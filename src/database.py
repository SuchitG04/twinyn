import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
conn = psycopg2.connect(os.getenv("CONNECTION_URL"))

# CREATE TABLE ip_log (
#     id SERIAL,
#     ip VARCHAR,
#     time TIMESTAMPTZ NOT NULL
# );
# creating hypertable: SELECT create_hypertable ('ip_log', by_range('time'))
