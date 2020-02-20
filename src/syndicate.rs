use crate::config::{Feed, FeedKind, Feeds};
use atom_syndication::{Error as AtomError, Feed as AtomFeed};
use base64::encode as b64encode;
use bytes::buf::BufExt;
use chrono::{DateTime, Utc};
use darkredis::{Connection as RedisConnection, Error as RedisError};
use reqwest::{Client as HttpClient, Error as HttpError, StatusCode};
use rss::{Channel as RssChannel, Error as RssError};
use std::{error::Error, fmt, io::BufRead, sync::Arc, time::Duration};
use tgbot::{
    methods::SendMessage,
    types::{ParseMode, ResponseError, ResponseParameters},
    Api, ExecuteError,
};
use tokio::{sync::Mutex, time::delay_for};

const PREFIX: &str = "telefeed";
const MAX_DAYS: i64 = 1;
const KEY_LIFETIME: u32 = 86400 * 7;
const MAX_SEND_TRIES: u64 = 20;
const PARSE_MODE: ParseMode = ParseMode::Html;

#[derive(Default)]
pub struct SyndicateBuilder {
    api: Option<Api>,
    http_client: Option<HttpClient>,
    redis_connection: Option<RedisConnection>,
    include_feed_title: bool,
}

impl SyndicateBuilder {
    pub fn api(mut self, api: Api) -> Self {
        self.api = Some(api);
        self
    }

    pub fn http_client(mut self, http_client: HttpClient) -> Self {
        self.http_client = Some(http_client);
        self
    }

    pub fn redis_connection(mut self, redis_connection: RedisConnection) -> Self {
        self.redis_connection = Some(redis_connection);
        self
    }

    pub fn include_feed_title(mut self, include_feed_title: bool) -> Self {
        self.include_feed_title = include_feed_title;
        self
    }

    pub fn build(self) -> Syndicate {
        Syndicate {
            api: self.api.expect("API is missing"),
            http_client: Arc::new(self.http_client.expect("HTTP client is missing")),
            redis_connection: Arc::new(Mutex::new(self.redis_connection.expect("Redis connection is missing"))),
            include_feed_title: self.include_feed_title,
        }
    }
}

#[derive(Clone)]
pub struct Syndicate {
    api: Api,
    http_client: Arc<HttpClient>,
    redis_connection: Arc<Mutex<RedisConnection>>,
    include_feed_title: bool,
}

impl Syndicate {
    async fn get_entries(&self, feed: &Feed) -> Result<Entries, SyndicateError> {
        let rep = self.http_client.get(&feed.url).send().await?;
        let status = rep.status();
        if !status.is_success() {
            return Err(SyndicateError::BadStatus(status));
        }
        let reader = rep.bytes().await?.reader();
        match feed.kind {
            FeedKind::Rss => read_rss(reader),
            FeedKind::Atom => read_atom(reader),
        }
    }

    pub async fn run(self, feeds: Feeds) -> Result<(), SyndicateError> {
        let timeout = Duration::from_secs(60);
        let mut redis_connection = self.redis_connection.lock().await;
        loop {
            for (channel_name, channel_feeds) in &feeds {
                for feed in channel_feeds {
                    log::info!("Reading entries for '{}' ...", feed.url);
                    match self.get_entries(&feed).await {
                        Ok(entries) => {
                            let feed_title = PARSE_MODE.escape(entries.feed_title);
                            let total_entries = entries.items.len();
                            let mut sent_count = 0;
                            log::info!("Got {} entries for {}", total_entries, feed.url);
                            for entry in entries.items {
                                let key =
                                    format!("{}:{}", PREFIX, b64encode(&format!("{}{}", &channel_name, entry.url)));
                                if !redis_connection.exists(&key).await? {
                                    let mut text = entry.to_html();
                                    if self.include_feed_title {
                                        text = format!("{}: {}", feed_title, text);
                                    }
                                    redis_connection
                                        .set_and_expire_seconds(key, &text, KEY_LIFETIME)
                                        .await?;
                                    tokio::spawn(send_message(self.api.clone(), channel_name.clone(), text));
                                    sent_count += 1;
                                }
                            }
                            log::info!("{} of {} entries sent for {}", sent_count, total_entries, feed.url);
                        }
                        Err(err) => log::error!("Failed to get entries for feed {}: {}", feed.url, err),
                    }
                }
            }
            log::info!("All entries read, waiting for next iteration...");
            delay_for(timeout).await;
        }
    }
}

async fn send_message(api: Api, channel_name: String, text: String) -> Result<(), SyndicateError> {
    let mut current_try = 0;
    loop {
        match api
            .execute(SendMessage::new(channel_name.as_str(), &text).parse_mode(PARSE_MODE))
            .await
        {
            Ok(_) => {
                return Ok(());
            }
            Err(err) => {
                if current_try >= MAX_SEND_TRIES {
                    log::error!(
                        "Failed to send message '{}' to channel '{}': {}",
                        text,
                        channel_name,
                        err
                    );
                    return Err(SyndicateError::SendMessage(err));
                }
                log::info!(
                    "Failed to send message '{}' to channel '{}': {}, trying again...",
                    text,
                    channel_name,
                    err
                );
                current_try += 1;
                let timeout = match err {
                    ExecuteError::Response(ResponseError {
                        parameters:
                            Some(ResponseParameters {
                                retry_after: Some(retry_after),
                                ..
                            }),
                        ..
                    }) => Duration::from_secs(retry_after as u64),
                    _ => Duration::from_millis(100 * current_try),
                };
                delay_for(timeout).await
            }
        }
    }
}

#[derive(Debug)]
struct Entries {
    feed_title: String,
    items: Vec<Entry>,
}

impl Entries {
    fn new<T: Into<String>>(feed_title: T, items: Vec<Entry>) -> Self {
        Self {
            feed_title: feed_title.into(),
            items,
        }
    }
}

fn read_rss<R: BufRead>(reader: R) -> Result<Entries, SyndicateError> {
    let now = Utc::now().naive_utc();
    let now_str = Utc::now().to_rfc2822();
    let mut result = Vec::new();
    let channel = RssChannel::read_from(reader)?;
    let feed_title = channel.title().to_string();
    for item in channel.into_items() {
        let pub_date = match item.pub_date().map(DateTime::parse_from_rfc2822) {
            Some(Ok(pub_date)) => {
                // Skip items older than MAX_DAYS
                let num_days = (now - pub_date.naive_utc()).num_days();
                if num_days > MAX_DAYS {
                    log::debug!("RSS item {:?} is {} days old, skipping", item, num_days);
                    continue;
                }
                pub_date.to_rfc2822()
            }
            _ => now_str.clone(), // let's assume that item published now
        };
        if let (Some(title), Some(link)) = (item.title(), item.link()) {
            result.push(Entry::new(link, title, pub_date));
        } else {
            log::debug!("Title or link not found for RSS item: {:?}", item);
        }
    }
    Ok(Entries::new(feed_title, result))
}

fn read_atom<R: BufRead>(reader: R) -> Result<Entries, SyndicateError> {
    let now = Utc::now().naive_utc();
    let mut result = Vec::new();
    let feed = AtomFeed::read_from(reader)?;
    for item in feed.entries() {
        let published = item.published().unwrap_or_else(|| item.updated());
        // Skip items older than MAX_DAYS
        let num_days = (now - published.naive_utc()).num_days();
        if num_days > MAX_DAYS {
            log::debug!("Atom item {:?} is {} days old, skipping", item, num_days);
            continue;
        }
        let links = item.links();
        if links.is_empty() {
            log::debug!("Atom item {:?} has no links, skipping", item);
            continue;
        }
        let link = &links[0];
        let title = link.title().unwrap_or_else(|| item.title());
        result.push(Entry::new(link.href(), title, published.to_rfc2822()));
    }
    Ok(Entries::new(feed.title(), result))
}

#[derive(Debug)]
struct Entry {
    url: String,
    title: String,
    published: String,
}

impl Entry {
    fn new<U, T, P>(url: U, title: T, published: P) -> Self
    where
        U: Into<String>,
        T: Into<String>,
        P: Into<String>,
    {
        Self {
            url: url.into(),
            title: title.into(),
            published: published.into(),
        }
    }

    fn to_html(&self) -> String {
        let title = PARSE_MODE.escape(&self.title);
        format!(r#"<a href="{}">{}</a> ({})"#, self.url, title, self.published)
    }
}

#[derive(Debug)]
pub enum SyndicateError {
    Atom(AtomError),
    BadStatus(StatusCode),
    HttpRequest(HttpError),
    Redis(RedisError),
    Rss(RssError),
    SendMessage(ExecuteError),
}

impl From<AtomError> for SyndicateError {
    fn from(err: AtomError) -> Self {
        SyndicateError::Atom(err)
    }
}

impl From<HttpError> for SyndicateError {
    fn from(err: HttpError) -> Self {
        SyndicateError::HttpRequest(err)
    }
}

impl From<RedisError> for SyndicateError {
    fn from(err: RedisError) -> Self {
        SyndicateError::Redis(err)
    }
}

impl From<RssError> for SyndicateError {
    fn from(err: RssError) -> Self {
        SyndicateError::Rss(err)
    }
}

impl Error for SyndicateError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            SyndicateError::HttpRequest(err) => Some(err),
            SyndicateError::Rss(err) => Some(err),
            SyndicateError::Redis(err) => Some(err),
            SyndicateError::SendMessage(err) => Some(err),
            _ => None,
        }
    }
}

impl fmt::Display for SyndicateError {
    fn fmt(&self, out: &mut fmt::Formatter) -> fmt::Result {
        match self {
            SyndicateError::Atom(err) => write!(out, "failed to parse atom feed: {}", err),
            SyndicateError::BadStatus(status) => write!(out, "server repsond with {} status code", status),
            SyndicateError::HttpRequest(err) => write!(out, "http request error: {}", err),
            SyndicateError::Redis(err) => write!(out, "redis error: {}", err),
            SyndicateError::Rss(err) => write!(out, "failed to parse RSS: {}", err),
            SyndicateError::SendMessage(err) => write!(out, "failed to send message: {}", err),
        }
    }
}
