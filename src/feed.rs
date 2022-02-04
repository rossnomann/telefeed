use atom_syndication::{Entry as AtomEntry, Feed as AtomFeed};
use chrono::{DateTime, FixedOffset, Utc};
use rss::{Channel as RssFeed, Item as RssEntry};
use std::{convert::TryFrom, error::Error, fmt};
use tgbot::types::ParseMode;

#[derive(Debug)]
pub struct Feed {
    title: String,
    items: Vec<Entry>,
}

impl Feed {
    pub fn title(&self) -> &str {
        &self.title
    }

    pub fn entries(&self) -> &[Entry] {
        &self.items
    }
}

impl TryFrom<RssFeed> for Feed {
    type Error = FeedError;

    fn try_from(feed: RssFeed) -> Result<Self, Self::Error> {
        let title = feed.title().to_string();
        let mut items = Vec::new();
        for entry in feed.into_items() {
            items.push(Entry::try_from(entry)?);
        }
        Ok(Feed { title, items })
    }
}

impl TryFrom<AtomFeed> for Feed {
    type Error = FeedError;

    fn try_from(feed: AtomFeed) -> Result<Self, Self::Error> {
        let mut items = Vec::new();
        for entry in feed.entries() {
            items.push(Entry::try_from(entry.clone())?);
        }
        let title = String::from(feed.title().as_str());
        Ok(Feed { title, items })
    }
}

#[derive(Debug)]
pub enum FeedError {
    Entry(EntryError),
}

impl From<EntryError> for FeedError {
    fn from(err: EntryError) -> Self {
        FeedError::Entry(err)
    }
}

impl Error for FeedError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            FeedError::Entry(err) => Some(err),
        }
    }
}

impl fmt::Display for FeedError {
    fn fmt(&self, out: &mut fmt::Formatter) -> fmt::Result {
        match self {
            FeedError::Entry(err) => write!(out, "can not read entry: {}", err),
        }
    }
}

#[derive(Debug)]
pub struct Entry {
    url: String,
    title: String,
    published: DateTime<FixedOffset>,
}

impl Entry {
    pub fn new<U, T>(url: U, title: T, published: DateTime<FixedOffset>) -> Self
    where
        U: Into<String>,
        T: Into<String>,
    {
        Self {
            url: url.into(),
            title: title.into(),
            published,
        }
    }

    pub fn url(&self) -> &str {
        &self.url
    }

    pub fn age(&self) -> Days {
        let now = Utc::now().naive_utc();
        (now - self.published.naive_utc()).num_days()
    }

    pub fn as_html(&self) -> String {
        format!(
            r#"<a href="{}">{}</a> ({})"#,
            self.url,
            ParseMode::Html.escape(&self.title),
            self.published.to_rfc2822()
        )
    }
}

pub type Days = i64;

impl TryFrom<AtomEntry> for Entry {
    type Error = EntryError;

    fn try_from(entry: AtomEntry) -> Result<Self, Self::Error> {
        let links = entry.links();
        let link = &links[0];
        let title = link.title().unwrap_or_else(|| entry.title());
        if links.is_empty() {
            return Err(EntryError::NoUrl);
        }
        let published = entry.published().unwrap_or_else(|| entry.updated());
        Ok(Entry::new(link.href(), title, *published))
    }
}

impl TryFrom<RssEntry> for Entry {
    type Error = EntryError;

    fn try_from(entry: RssEntry) -> Result<Self, Self::Error> {
        let title = entry.title().ok_or(EntryError::NoTitle)?;
        let url = entry.link().ok_or(EntryError::NoUrl)?;
        let published = match entry.pub_date().map(DateTime::parse_from_rfc2822) {
            Some(Ok(published)) => published,
            _ => {
                // let's assume that item published now
                DateTime::from_utc(Utc::now().naive_utc(), FixedOffset::east(0))
            }
        };
        Ok(Entry::new(url, title, published))
    }
}

#[derive(Clone, Copy, Debug)]
pub enum EntryError {
    NoTitle,
    NoUrl,
}

impl Error for EntryError {}

impl fmt::Display for EntryError {
    fn fmt(&self, out: &mut fmt::Formatter) -> fmt::Result {
        match self {
            EntryError::NoTitle => write!(out, "title is missing"),
            EntryError::NoUrl => write!(out, "url is missing"),
        }
    }
}
