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

#[derive(Clone)]
pub struct Syndication {
    api: Api,
    http_client: Arc<HttpClient>,
    redis_connection: Arc<Mutex<RedisConnection>>,
}

impl Syndication {
    pub fn new(api: Api, http_client: HttpClient, redis_connection: RedisConnection) -> Self {
        Self {
            api,
            http_client: Arc::new(http_client),
            redis_connection: Arc::new(Mutex::new(redis_connection)),
        }
    }

    async fn get_entries(&self, feed: &Feed) -> Result<Vec<String>, SyndicationError> {
        let rep = self.http_client.get(&feed.url).send().await?;
        let status = rep.status();
        if !status.is_success() {
            return Err(SyndicationError::BadStatus(status));
        }
        let reader = rep.bytes().await?.reader();
        match feed.kind {
            FeedKind::Rss => read_rss(reader),
            FeedKind::Atom => read_atom(reader),
        }
    }

    pub async fn run(self, feeds: Feeds) -> Result<(), SyndicationError> {
        let timeout = Duration::from_secs(60);
        let mut redis_connection = self.redis_connection.lock().await;
        loop {
            for (channel_name, channel_feeds) in &feeds {
                for feed in channel_feeds {
                    log::info!("Reading entries for '{}' ...", feed.url);
                    match self.get_entries(&feed).await {
                        Ok(entries) => {
                            let total_entries = entries.len();
                            let mut sent_count = 0;
                            log::info!("Got {} entries for {}", total_entries, feed.url);
                            for entry in entries {
                                let key = format!("{}:{}", PREFIX, b64encode(&format!("{}{}", &channel_name, entry)));
                                if !redis_connection.exists(&key).await? {
                                    redis_connection
                                        .set_and_expire_seconds(key, entry.clone(), KEY_LIFETIME)
                                        .await?;
                                    tokio::spawn(send_message(self.api.clone(), channel_name.clone(), entry));
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

async fn send_message(api: Api, channel_name: String, text: String) -> Result<(), SyndicationError> {
    let mut current_try = 0;
    loop {
        match api
            .execute(SendMessage::new(channel_name.as_str(), &text).parse_mode(ParseMode::Html))
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
                    return Err(SyndicationError::SendMessage(err));
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

fn read_rss<R: BufRead>(reader: R) -> Result<Vec<String>, SyndicationError> {
    let now = Utc::now().naive_utc();
    let now_str = Utc::now().to_rfc2822();
    let mut result = Vec::new();
    for item in RssChannel::read_from(reader)?.into_items() {
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
            result.push(format!(r#"<a href="{}">{}</a> ({})"#, link, title, pub_date));
        } else {
            log::debug!("Title or link not found for RSS item: {:?}", item);
        }
    }
    Ok(result)
}

fn read_atom<R: BufRead>(reader: R) -> Result<Vec<String>, SyndicationError> {
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
        result.push(format!(
            r#"<a href="{}">{}</a> ({})"#,
            link.href(),
            title,
            published.to_rfc2822()
        ));
    }
    Ok(result)
}

#[derive(Debug)]
pub enum SyndicationError {
    Atom(AtomError),
    BadStatus(StatusCode),
    HttpRequest(HttpError),
    Redis(RedisError),
    Rss(RssError),
    SendMessage(ExecuteError),
}

impl From<AtomError> for SyndicationError {
    fn from(err: AtomError) -> Self {
        SyndicationError::Atom(err)
    }
}

impl From<HttpError> for SyndicationError {
    fn from(err: HttpError) -> Self {
        SyndicationError::HttpRequest(err)
    }
}

impl From<RedisError> for SyndicationError {
    fn from(err: RedisError) -> Self {
        SyndicationError::Redis(err)
    }
}

impl From<RssError> for SyndicationError {
    fn from(err: RssError) -> Self {
        SyndicationError::Rss(err)
    }
}

impl Error for SyndicationError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            SyndicationError::HttpRequest(err) => Some(err),
            SyndicationError::Rss(err) => Some(err),
            SyndicationError::Redis(err) => Some(err),
            SyndicationError::SendMessage(err) => Some(err),
            _ => None,
        }
    }
}

impl fmt::Display for SyndicationError {
    fn fmt(&self, out: &mut fmt::Formatter) -> fmt::Result {
        match self {
            SyndicationError::Atom(err) => write!(out, "failed to parse atom feed: {}", err),
            SyndicationError::BadStatus(status) => write!(out, "server repsond with {} status code", status),
            SyndicationError::HttpRequest(err) => write!(out, "http request error: {}", err),
            SyndicationError::Redis(err) => write!(out, "redis error: {}", err),
            SyndicationError::Rss(err) => write!(out, "failed to parse RSS: {}", err),
            SyndicationError::SendMessage(err) => write!(out, "failed to send message: {}", err),
        }
    }
}
