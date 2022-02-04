# TELEFEED

An RSS/Atom bot for telegram channels

# Installation

Make sure that you have installed [Redis](https://redis.io/).

Download binary:

```sh
$ curl -L https://github.com/rossnomann/telefeed/releases/download/0.4.0/telefeed-0.4.0_x86_64-linux-gnu --output telefeed
$ chmod +x telefeed
```

Create `config.yaml`:

```yaml
token: bottoken
redis_url: redis://127.0.0.1:6379
# include_feed_title: true  # include feed title to entry link; defaults to false
# request_timeout: 3600  # timeout between requests in seconds; defaults to 1200 (20 minutes)
feeds:
  '@channel':  # channel username with @
    - url: http://www.darkside.ru/rss/  # url to feed
      kind: rss  # kind of feed: rss/atom
      # request_timeout: 20  # override root value
  -1234567890:  # channel ID also supported
    - url: https://www.youtube.com/feeds/videos.xml?channel_id=UCX5180-7TnjjHlHaVDdqnmA
      kind: atom
      # include_feed_title: false  # override root value
    - url: https://www.youtube.com/feeds/videos.xml?channel_id=UC2S1gZS9e8jb3Mx1Ce6YH5g
      kind: atom
```

Run:
```sh
./telefeed config.yaml
```

# Changelog

## 0.4.0 (04.02.2022)

- Updated tgbot to 0.17 and tokio to 1.16.
- Migrated from darkredis to redis-rs.
- Removed proxy configuration parameter.
- Added information about url to request error message.

## 0.3.0 (15.03.2020)

- Separate fetching of feed entries.
- Added `request_timeout` option to root and feed config section.
- Added `include_feed_title` option to feed config section.

## 0.2.3 (20.02.2020)

- Added `include_feed_title` option to config.
  Set it to `true` when you need to know feed title for each entry.

## 0.2.2 (31.01.2020)

- Escape special characters in URL title.

## 0.2.1 (19.01.2020)

- Fixed entries duplication.

## 0.2.0 (17.01.2020)

- RIIR.

## 0.1.5 (04.07.2018)

- Catch exceptions in getUpdates loop

## 0.1.4 (19.06.2018)

- Migrate to aiotg.
- Add http/socks5 proxy support.

## 0.1.3 (18.05.2018)

- Exclude entry title from unique constraint.

## 0.1.2 (15.03.2018)

- Escape html entities in entry title.
- Display dates with a timezone.

## 0.1.1 (11.03.2018)

- Catch feedparser exceptions.

## 0.1.0 (09.03.2018)

- First release.

# LICENSE

The MIT License (MIT)
