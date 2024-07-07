use crate::{
    cache::Cache,
    config::{Config, ConfigError},
    reader::Reader,
};
use dotenvy::dotenv;
use redis::{Client as RedisClient, RedisError};
use reqwest::Client as HttpClient;
use std::{env, fmt};
use tgbot::api::{Client, ClientError};
use tokio::sync::mpsc::channel;

const CHANNEL_BUFFER_SIZE: usize = 100;

pub async fn run() -> Result<(), Error> {
    dotenv().ok();
    env_logger::init();
    let config = match env::args().nth(1) {
        Some(path) => Config::from_file(path).await?,
        None => return Err(Error::ConfigPathMissing),
    };
    let client = Client::new(config.get_token())?;
    let http_client = HttpClient::new();
    let redis_client = RedisClient::open(config.redis_url())?;
    let redis_connection = redis_client.get_multiplexed_async_connection().await?;
    let cache = Cache::new(redis_connection);
    let (tx, mut rx) = channel(CHANNEL_BUFFER_SIZE);
    for feed_config in config.into_feeds() {
        let reader = Reader::new(feed_config, http_client.clone(), tx.clone());
        tokio::spawn(reader.run());
    }
    while let Some(payload) = rx.recv().await {
        tokio::spawn(payload.publish(client.clone(), cache.clone()));
    }
    Ok(())
}

pub enum Error {
    Client(ClientError),
    Config(ConfigError),
    ConfigPathMissing,
    Redis(RedisError),
}

impl From<ClientError> for Error {
    fn from(err: ClientError) -> Self {
        Error::Client(err)
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
            Error::Client(err) => write!(out, "Can not create a Telegram Bot API client: {err}"),
            Error::Config(err) => write!(out, "Configuration error: {err}"),
            Error::ConfigPathMissing => write!(out, "You need to provide a path to config"),
            Error::Redis(err) => write!(out, "Redis error: {err}"),
        }
    }
}
