from fastapi import FastAPI
from pydantic import BaseModel
from pydantic.networks import IPvAnyAddress
import utils

import geoip2.database
import redis.asyncio as redis

from datetime import datetime, timezone
import pytz

app = FastAPI()

# TODO: use env variables for db connection info
reader = geoip2.database.Reader("./GeoLite2-City_20240618/GeoLite2-City.mmdb")
redis = redis.Redis(host='localhost', port=6379, db=0)

class IPModel(BaseModel):
    ip: IPvAnyAddress

# query cache to get information about an IP. write-through
async def geo_ip(ip_request: IPModel):
    ip_str = str(ip_request.ip)
    cache_res = await redis.hgetall(name=ip_str)
    # write-through
    if not cache_res:
        # cache miss
        db_res = reader.city(ip_str).__dict__["raw"]
        db_res = utils.flatten(db_res)
        await redis.hset(
            name=ip_str,
            mapping=db_res
        )
        # TODO: write the ip and db_res to the timeseriesdb
    else:
        # cache hit
        return cache_res

    return db_res

# def get_curr_time():
#     utc_time = datetime.now(timezone.utc)
#     local_time = datetime.now(pytz.timezone("Asia/Kolkata"))
#     timestamptz = utc_time.strftime("%Y-%m-%d %H:%M:%S%z")
#     timestamptz = timestamptz[:-5] + str(local_time)[-6:]
#     return timestamptz

@app.post(
    "/insert",
)
async def insert_ip(ip: IPModel):
    out = await geo_ip(ip)
    return out
