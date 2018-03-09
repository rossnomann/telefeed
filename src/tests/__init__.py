import sqlalchemy as sa

from telefeed import config, models


SA_URL_TEMPLATE = 'postgresql://postgres:1234@postgres/{db}'
SA_POSTGRES_URL = SA_URL_TEMPLATE.format(db='postgres')
SA_TEST_URL = SA_URL_TEMPLATE.format(db='test')


def init_db():
    engine = sa.create_engine(SA_POSTGRES_URL, isolation_level='AUTOCOMMIT')
    with engine.connect() as conn:
        conn.execute("DROP DATABASE IF EXISTS test")
        conn.execute("CREATE DATABASE test")
    engine = sa.create_engine(SA_TEST_URL, isolation_level='AUTOCOMMIT')
    models.metadata.create_all(engine)


config.setup_logging()
init_db()
