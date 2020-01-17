use darkredis::{Connection as RedisConnection, Error as RedisError};
use dotenv::dotenv;
use reqwest::Client as HttpClient;
use std::{env, fmt};
use tgbot::{Api, ApiError};

mod config;
mod syndication;

use self::{
    config::{Config, ConfigError},
    syndication::{Syndication, SyndicationError},
};

async fn run() -> Result<(), Error> {
    dotenv().ok();
    env_logger::init();

    let config = match env::args().nth(1) {
        Some(path) => Config::from_file(path).await?,
        None => return Err(Error::ConfigPathMissing),
    };
    let api_config = config.get_api_config()?;
    let api = Api::new(api_config)?;
    let http_client = HttpClient::new();
    let redis_connection = RedisConnection::connect(config.redis_url.as_str()).await?;
    let syndication = Syndication::new(api, http_client, redis_connection);
    syndication.run(config.feeds).await?;
    Ok(())
}

#[tokio::main]
async fn main() {
    if let Err(err) = run().await {
        log::error!("{}", err);
    }
}

enum Error {
    Api(ApiError),
    Config(ConfigError),
    ConfigPathMissing,
    Redis(RedisError),
    Syndication(SyndicationError),
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

impl From<SyndicationError> for Error {
    fn from(err: SyndicationError) -> Self {
        Error::Syndication(err)
    }
}

impl fmt::Display for Error {
    fn fmt(&self, out: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Error::Api(err) => write!(out, "Can not create a Telegram Bot API: {}", err),
            Error::Config(err) => write!(out, "Configuration error: {}", err),
            Error::ConfigPathMissing => write!(out, "You need to provide a path to config"),
            Error::Redis(err) => write!(out, "Redis error: {}", err),
            Error::Syndication(err) => write!(out, "{}", err),
        }
    }
}
