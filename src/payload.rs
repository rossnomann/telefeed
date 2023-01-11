use crate::{
    cache::{Cache, CacheKey},
    config::FeedConfig,
    feed::Feed,
};
use tgbot::{
    methods::SendMessage,
    types::{ChatId, ParseMode},
    Api,
};

const PARSE_MODE: ParseMode = ParseMode::Html;
const MAX_ENTRY_AGE: i64 = 1;

#[derive(Debug)]
pub struct Payload {
    pub chat_id: ChatId,
    pub config: FeedConfig,
    pub feed: Feed,
}

impl Payload {
    pub async fn publish(self, api: Api, cache: Cache) {
        let feed_title = self.feed.title();
        let entries = self.feed.entries();
        log::info!("Got {} entries for {} feed", entries.len(), feed_title);
        let feed_title = PARSE_MODE.escape(feed_title);
        let entries = entries.iter().filter(|entry| {
            let entry_age = entry.age();
            let skip = entry_age > MAX_ENTRY_AGE;
            if skip {
                log::info!("{:?} {} day(s) old, skipping", entry, entry_age);
            }
            !skip
        });
        for entry in entries {
            let cache_key = CacheKey::new(&self.chat_id, entry);
            match cache.exists(&cache_key).await {
                Ok(true) => {
                    log::info!("{:?} already sent, skipping", entry);
                    continue;
                }
                Ok(false) => {
                    log::info!("{:?} not sent, continue", entry);
                }
                Err(err) => {
                    log::error!("Failed to check whether entry was sent: {}; send entry anyway", err);
                }
            };
            let mut text = entry.as_html();
            if self.config.include_feed_title {
                text = format!("{feed_title}: {text}");
            }
            let method = SendMessage::new(self.chat_id.clone(), text).parse_mode(PARSE_MODE);
            match api.execute(method).await {
                Ok(_) => {
                    if let Err(err) = cache.set(&cache_key).await {
                        log::error!("Failed to mark entry as sent: {}", err)
                    }
                }
                Err(err) => log::error!("Failed to send message: {}", err),
            }
        }
    }
}
