use serde::Deserialize;
use std::{
    collections::HashMap,
    error::Error,
    fmt,
    io::Error as IoError,
    path::{Path, PathBuf},
    time::Duration,
};
use tgbot::types::{ChatId, Integer};
use tokio::fs;
use toml::de::Error as TomlError;

const DEFAULT_INCLUDE_FEED_TITLE: bool = false;
const DEFAULT_REQUEST_TIMEOUT: u64 = 1200;

#[derive(Deserialize)]
struct RawConfig {
    token: String,
    redis_url: String,
    feeds: HashMap<String, Vec<RawFeedConfig>>,
    include_feed_title: Option<bool>,
    request_timeout: Option<u64>,
}

#[derive(Deserialize)]
struct RawFeedConfig {
    url: String,
    kind: FeedKind,
    include_feed_title: Option<bool>,
    request_timeout: Option<u64>,
}

#[derive(Clone, Debug)]
pub struct Config {
    token: String,
    redis_url: String,
    feeds: Vec<FeedConfig>,
}

impl Config {
    pub async fn from_file<P: AsRef<Path>>(path: P) -> Result<Self, ConfigError> {
        let path = path.as_ref();
        let data = fs::read_to_string(path)
            .await
            .map_err(|err| ConfigError::ReadFile(path.to_owned(), err))?;
        let raw: RawConfig = toml::from_str(&data).map_err(ConfigError::ParseToml)?;
        let default_include_feed_title = raw.include_feed_title.unwrap_or(DEFAULT_INCLUDE_FEED_TITLE);
        let default_request_timeout = raw.request_timeout.unwrap_or(DEFAULT_REQUEST_TIMEOUT);
        let mut feeds = Vec::new();
        for (key, raw_feeds) in raw.feeds {
            let chat_id = match key.parse::<Integer>() {
                Ok(chat_id) => ChatId::from(chat_id),
                Err(_) => ChatId::from(key),
            };
            for raw_feed in raw_feeds {
                let include_feed_title = raw_feed.include_feed_title.unwrap_or(default_include_feed_title);
                let request_timeout = raw_feed.request_timeout.unwrap_or(default_request_timeout);
                feeds.push(FeedConfig {
                    chat_id: chat_id.clone(),
                    url: raw_feed.url,
                    kind: raw_feed.kind,
                    include_feed_title,
                    request_timeout: Duration::from_secs(request_timeout),
                });
            }
        }
        Ok(Self {
            token: raw.token,
            redis_url: raw.redis_url,
            feeds,
        })
    }

    pub fn get_token(&self) -> &str {
        &self.token
    }

    pub fn redis_url(&self) -> &str {
        &self.redis_url
    }

    pub fn into_feeds(self) -> Vec<FeedConfig> {
        self.feeds
    }
}

#[derive(Clone, Debug)]
pub struct FeedConfig {
    pub chat_id: ChatId,
    pub url: String,
    pub kind: FeedKind,
    pub include_feed_title: bool,
    pub request_timeout: Duration,
}

#[derive(Copy, Clone, Debug, Deserialize)]
pub enum FeedKind {
    #[serde(rename = "rss")]
    Rss,
    #[serde(rename = "atom")]
    Atom,
}

#[derive(Debug)]
pub enum ConfigError {
    ParseToml(TomlError),
    ReadFile(PathBuf, IoError),
}

impl Error for ConfigError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            ConfigError::ParseToml(err) => Some(err),
            ConfigError::ReadFile(_, err) => Some(err),
        }
    }
}

impl fmt::Display for ConfigError {
    fn fmt(&self, out: &mut fmt::Formatter) -> fmt::Result {
        match self {
            ConfigError::ParseToml(err) => write!(out, "failed to parse TOML: {err}"),
            ConfigError::ReadFile(path, err) => {
                write!(out, "failed to read a file '{err}': {path}", path = path.display())
            }
        }
    }
}
