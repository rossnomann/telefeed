use crate::feed::Entry;
use base64::{engine::general_purpose::STANDARD_NO_PAD as BASE64_ENGINE, Engine};
use redis::{aio::Connection as RedisConnection, AsyncCommands, RedisError};
use std::{error::Error, fmt, sync::Arc};
use tgbot::types::ChatId;
use tokio::sync::Mutex;

const PREFIX: &str = "telefeed";
const LIFETIME: usize = 86400 * 7;

#[derive(Clone)]
pub struct Cache {
    connection: Arc<Mutex<RedisConnection>>,
}

impl Cache {
    pub fn new(connection: RedisConnection) -> Self {
        Cache {
            connection: Arc::new(Mutex::new(connection)),
        }
    }

    pub async fn exists(&self, key: &CacheKey) -> Result<bool, CacheError> {
        let mut conn = self.connection.lock().await;
        conn.exists(&key.0).await.map_err(CacheError::Exists)
    }

    pub async fn set(&self, key: &CacheKey) -> Result<(), CacheError> {
        let mut conn = self.connection.lock().await;
        conn.set_ex(&key.0, &key.0, LIFETIME).await.map_err(CacheError::Set)?;
        Ok(())
    }
}

pub struct CacheKey(String);

impl CacheKey {
    pub fn new(chat_id: &ChatId, entry: &Entry) -> Self {
        Self(format!(
            "{}:{}",
            PREFIX,
            BASE64_ENGINE.encode(format!("{chat_id}{url}", url = entry.url()))
        ))
    }
}

#[derive(Debug)]
pub enum CacheError {
    Exists(RedisError),
    Set(RedisError),
}

impl fmt::Display for CacheError {
    fn fmt(&self, out: &mut fmt::Formatter) -> fmt::Result {
        match self {
            CacheError::Exists(err) => write!(out, "can not check whether cache key exists: {err}"),
            CacheError::Set(err) => write!(out, "can not set cache key: {err}"),
        }
    }
}

impl Error for CacheError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        Some(match self {
            CacheError::Exists(err) => err,
            CacheError::Set(err) => err,
        })
    }
}
