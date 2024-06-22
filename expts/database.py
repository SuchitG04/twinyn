import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
CONNECTION_URL = os.getenv("CONNECTION_URL")
conn = psycopg2.connect(CONNECTION_URL)

# create_table = """CREATE TABLE ip_log (
#                       id SERIAL,
#                       ip VARCHAR,
#                       time TIMESTAMPTZ NOT NULL
#                   );
#                   """
# hypertable = """SELECT create_hypertable ('ip_log', by_range('time'))"""
