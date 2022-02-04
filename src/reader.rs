use crate::{
    config::{FeedConfig, FeedKind},
    feed::{Feed, FeedError},
    payload::Payload,
};
use atom_syndication::{Error as AtomError, Feed as AtomFeed};
use bytes::Buf;
use reqwest::{Client as HttpClient, Error as HttpError, StatusCode};
use rss::{Channel as RssFeed, Error as RssError};
use std::{convert::TryFrom, error::Error, fmt};
use tokio::{sync::mpsc::Sender, time::sleep};

pub struct Reader {
    config: FeedConfig,
    http_client: HttpClient,
    sender: Sender<Payload>,
}

impl Reader {
    pub fn new(config: FeedConfig, http_client: HttpClient, sender: Sender<Payload>) -> Self {
        Self {
            config,
            http_client,
            sender,
        }
    }

    async fn request(&self) -> Result<Feed, RequestError> {
        let rep = self.http_client.get(&self.config.url).send().await?;
        let status = rep.status();
        if !status.is_success() {
            return Err(RequestError::BadStatus(status));
        }
        let reader = rep.bytes().await?.reader();
        Ok(match self.config.kind {
            FeedKind::Rss => Feed::try_from(RssFeed::read_from(reader)?)?,
            FeedKind::Atom => Feed::try_from(AtomFeed::read_from(reader)?)?,
        })
    }

    pub async fn run(self) {
        loop {
            match self.request().await {
                Ok(feed) => {
                    if self
                        .sender
                        .send(Payload {
                            chat_id: self.config.chat_id.clone(),
                            feed,
                            config: self.config.clone(),
                        })
                        .await
                        .is_err()
                    {
                        log::error!("Could not publish payload; A receiving end has dropped");
                    }
                }
                Err(err) => log::error!("An error has occurred: {}", err),
            }
            sleep(self.config.request_timeout).await;
        }
    }
}

#[derive(Debug)]
enum RequestError {
    Atom(AtomError),
    BadStatus(StatusCode),
    Feed(FeedError),
    Http(HttpError),
    Rss(RssError),
}

impl From<AtomError> for RequestError {
    fn from(err: AtomError) -> Self {
        RequestError::Atom(err)
    }
}

impl From<FeedError> for RequestError {
    fn from(err: FeedError) -> Self {
        RequestError::Feed(err)
    }
}

impl From<HttpError> for RequestError {
    fn from(err: HttpError) -> Self {
        RequestError::Http(err)
    }
}

impl From<RssError> for RequestError {
    fn from(err: RssError) -> Self {
        RequestError::Rss(err)
    }
}

impl Error for RequestError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            RequestError::Atom(err) => Some(err),
            RequestError::BadStatus(_) => None,
            RequestError::Feed(err) => Some(err),
            RequestError::Http(err) => Some(err),
            RequestError::Rss(err) => Some(err),
        }
    }
}

impl fmt::Display for RequestError {
    fn fmt(&self, out: &mut fmt::Formatter) -> fmt::Result {
        match self {
            RequestError::Atom(err) => write!(out, "can not parse an atom feed: {}", err),
            RequestError::BadStatus(status) => write!(out, "a server respond with {} status", status),
            RequestError::Feed(err) => write!(out, "can not read a feed: {}", err),
            RequestError::Http(err) => write!(out, "an error occurred when sending an HTTP request: {}", err),
            RequestError::Rss(err) => write!(out, "can not parse an RSS feed: {}", err),
        }
    }
}
