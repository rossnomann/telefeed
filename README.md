# TELEFEED

An RSS/Atom bot for telegram channels

[![Travis](https://img.shields.io/travis/rossnomann/telefeed.svg?style=flat-square)](https://travis-ci.org/rossnomann/telefeed)
[![Docker Stars](https://img.shields.io/docker/stars/rossnomann/telefeed.svg?style=flat-square)](https://hub.docker.com/r/rossnomann/telefeed/)
[![Docker Pulls](https://img.shields.io/docker/pulls/rossnomann/telefeed.svg?style=flat-square)](https://hub.docker.com/r/rossnomann/telefeed/)

# Usage

- `/addchannel <name>` - adds a new channel.
- `/addfeed <channel> <url>` adds an rss/atom feed to channel.
- `/delchannel <name>` - deletes a channel along with with feeds.
- `/delfeed <channel> <url>` - deletes a feed from channel.
- `/listchannels` - shows a list of available channels.
- `/listfeeds` - shows a list of available feeds per channel.

# Installation

Make sure that you have installed:

- Docker
- docker-compose
- PostgreSQL

Create a database:

```sh
$ psql
psql (9.5.12)
Type "help" for help.

postgres=> create database telefeed;
postgres=> \q
```

Create `docker-compose.yml`:

```yaml
version: '3.4'
services:
  app:
    image: rossnomann/telefeed:0.1.0
    environment:
      # URL to PostgreSQL database
      TELEFEED_SA_URL: postgresql://user:password@127.0.0.1/telefeed
      # Username or ID of admin user in telegram
      TELEFEED_ADMIN_USER_ID: telegramusername
      # Ask @BotFather for token and paste it here
      TELEFEED_TOKEN: bot-token
      # Timezone for feeds' entries
      TELEFEED_TIMEZONE: Europe/Moscow
      # Use 'true' to enable debug mode
      TELEFEED_DEBUG: 'false'
      # Feed parsing timeout
      TELEFEED_PARSE_TIMEOUT: 1200
    network_mode: host
    container_name: telefeed
    restart: always
```

Pull image:

```sh
$ docker-compose pull
```

Run migrations:

```sh
$ docker-compose run --rm app alembic upgrade head
```

Start app:

```sh
$ docker-compose up -d
```

Check that everything is ok:

```sh
$ docker-compose ps
$ docker-compose logs
```

Now you can add channels and feeds.
Don't forget to add your bot to channel's admins list.

Entries will appear as soon as possible. Good luck!

# Upgrade

Stop app:
```sh
$ docker-compose stop
```

Create a backup (`docker-compose.yml` and database).

Change image version in `docker-compose.yml`:

```yaml
# version: '3.4'
# services:
#   app:
      image: rossnomann/telefeed:%new-version-here%
```

Make other changes in `docker-compose.yml` if required (see changelog).

Pull a new image:
```sh
$ docker-compose pull
```

Run migrations:
```sh
docker-compose run --rm app alembic upgrade head
```

Start app:
```sh
$ docker-compose up -d
```

Check that everything is ok:

```sh
$ docker-compose ps
$ docker-compose logs
```

# Development

Make sure that you have installed:

- Docker
- docker-compose
- Python 3

Fork and clone this repository.

Create `.env` file:

```
TELEFEED_ADMIN_USER_ID=telegram-username-or-id
TELEFEED_TOKEN=Bot-Token-For-Tests
TELEFEED_TIMEZONE=Europe/Moscow
```

Run app and db using:

```sh
$ docker-compose up
```

Database access:
```sh
$ psql -h localhost -p 6001 -U postgres postgres
```

Tests:
```sh
$ ./manage.py test
```

(Re)build image:
```sh
$ ./manage.py build
```

# Changelog

## 0.1.0 (09.03.2018)

- First release

# LICENSE

The MIT License (MIT)
