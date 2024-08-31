import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
conn = psycopg2.connect(os.getenv("CONNECTION_URL"))

# CREATE table server_log (
#     client cidr,
#     datetime timestamptz,
#     method text,
#     path text,
#     status_code integer,
#     size integer,
#     referer text,
#     user_agent text
# );
# CREATE index ON geoip2_network USING gist (network inet_ops);
# CREATE index ON server_log USING gist (network inet_ops);
# SELECT create_hypertable ('server_log', by_range('datetime'));