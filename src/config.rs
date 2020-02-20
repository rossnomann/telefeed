use serde::Deserialize;
use serde_yaml::Error as YamlError;
use std::{
    collections::HashMap,
    error::Error,
    fmt,
    io::Error as IoError,
    path::{Path, PathBuf},
};
use tgbot::{Config as ApiConfig, ParseProxyError};
use tokio::fs;

#[derive(Clone, Debug, Deserialize)]
pub struct Config {
    token: String,
    proxy: Option<String>,
    #[serde(default)]
    pub include_feed_title: bool,
    pub redis_url: String,
    pub feeds: Feeds,
}

impl Config {
    pub async fn from_file<P: AsRef<Path>>(path: P) -> Result<Self, ConfigError> {
        let path = path.as_ref();
        let data = fs::read(path)
            .await
            .map_err(|err| ConfigError::ReadFile(path.to_owned(), err))?;
        Ok(serde_yaml::from_slice(&data).map_err(ConfigError::ParseYaml)?)
    }

    pub fn get_api_config(&self) -> Result<ApiConfig, ConfigError> {
        let mut config = ApiConfig::new(self.token.clone());
        if let Some(ref proxy) = self.proxy {
            config = config.proxy(proxy.clone())?;
        }
        Ok(config)
    }
}

pub type Feeds = HashMap<String, Vec<Feed>>;

#[derive(Clone, Debug, Deserialize)]
pub struct Feed {
    pub url: String,
    pub kind: FeedKind,
}

#[derive(Copy, Clone, Debug, Deserialize, PartialEq, PartialOrd)]
pub enum FeedKind {
    #[serde(rename = "rss")]
    Rss,
    #[serde(rename = "atom")]
    Atom,
}

#[derive(Debug)]
pub enum ConfigError {
    ParseYaml(YamlError),
    ProxyAddress(ParseProxyError),
    ReadFile(PathBuf, IoError),
}

impl From<ParseProxyError> for ConfigError {
    fn from(err: ParseProxyError) -> Self {
        ConfigError::ProxyAddress(err)
    }
}

impl Error for ConfigError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            ConfigError::ParseYaml(err) => Some(err),
            ConfigError::ProxyAddress(err) => Some(err),
            ConfigError::ReadFile(_, err) => Some(err),
        }
    }
}

impl fmt::Display for ConfigError {
    fn fmt(&self, out: &mut fmt::Formatter) -> fmt::Result {
        match self {
            ConfigError::ParseYaml(err) => write!(out, "failed to parse YAML: {}", err),
            ConfigError::ProxyAddress(err) => write!(out, "bad proxy address: {}", err),
            ConfigError::ReadFile(path, err) => write!(out, "failed to read a file '{}': {}", path.display(), err),
        }
    }
}
