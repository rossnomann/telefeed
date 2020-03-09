use crate::{
    cache::Cache,
    config::{Config, ConfigError},
    reader::Reader,
};
use darkredis::{Connection as RedisConnection, Error as RedisError};
use dotenv::dotenv;
use reqwest::Client as HttpClient;
use std::{env, fmt};
use tgbot::{Api, ApiError};
use tokio::sync::mpsc::channel;

const CHANNEL_BUFFER_SIZE: usize = 100;

pub async fn run() -> Result<(), Error> {
    dotenv().ok();
    env_logger::init();
    let config = match env::args().nth(1) {
        Some(path) => Config::from_file(path).await?,
        None => return Err(Error::ConfigPathMissing),
    };
    let api_config = config.get_api_config()?;
    let api = Api::new(api_config)?;
    let http_client = HttpClient::new();
    let redis_connection = RedisConnection::connect(config.redis_url()).await?;
    let cache = Cache::new(redis_connection);
    let (tx, mut rx) = channel(CHANNEL_BUFFER_SIZE);
    for feed_config in config.into_feeds() {
        let reader = Reader::new(feed_config, http_client.clone(), tx.clone());
        tokio::spawn(reader.run());
    }
    while let Some(payload) = rx.recv().await {
        tokio::spawn(payload.publish(api.clone(), cache.clone()));
    }
    Ok(())
}

pub enum Error {
    Api(ApiError),
    Config(ConfigError),
    ConfigPathMissing,
    Redis(RedisError),
}

impl From<ApiError> for Error {
    fn from(err: ApiError) -> Self {
        Error::Api(err)
    }
}

impl From<ConfigError> for Error {
    fn from(err: ConfigError) -> Self {
        Error::Config(err)
    }
}

impl From<RedisError> for Error {
    fn from(err: RedisError) -> Self {
        Error::Redis(err)
    }
}

impl fmt::Display for Error {
    fn fmt(&self, out: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Error::Api(err) => write!(out, "Can not create a Telegram Bot API: {}", err),
            Error::Config(err) => write!(out, "Configuration error: {}", err),
            Error::ConfigPathMissing => write!(out, "You need to provide a path to config"),
            Error::Redis(err) => write!(out, "Redis error: {}", err),
        }
    }
}
