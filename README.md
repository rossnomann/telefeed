# TELEFEED

An RSS/Atom bot for telegram channels

# Installation

Make sure that you have installed [Redis](https://redis.io/).

Download binary:

```sh
$ curl -L https://github.com/rossnomann/telefeed/releases/download/0.2.0/telefeed-0.2.0_x86_64-linux-gnu --output telefeed
$ chmod +x telefeed
```

Create `config.yaml`:

```yaml
token: bottoken
redis_url: 127.0.0.1:6379
# proxy: 'socks5://user:password@host:port'
# http proxies also supported
feeds:
  '@channel':  # channel username with @
    - url: http://www.darkside.ru/rss/  # url to feed
      kind: rss  # kind of feed: rss/atom
  -1234567890:  # channel ID also supported
    - url: https://www.youtube.com/feeds/videos.xml?channel_id=UCX5180-7TnjjHlHaVDdqnmA
      kind: atom
    - url: https://www.youtube.com/feeds/videos.xml?channel_id=UC2S1gZS9e8jb3Mx1Ce6YH5g
      kind: atom
```

Run:
```sh
./telefeed config.yaml
```

# Changelog

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
