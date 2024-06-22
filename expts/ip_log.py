from fastapi import FastAPI
import geoip2.database
import redis.asyncio as redis

import utils
from database import conn
from schemas import IPModel

import os
from dotenv import load_dotenv

app = FastAPI()
load_dotenv()

GEOIP_DB = os.getenv("GEOIP_DB")
reader = geoip2.database.Reader(GEOIP_DB)
redis = redis.Redis(host='localhost', port=6379, db=0)


async def geo_ip(ip_request: IPModel) -> dict:
    """
    query cache to get information about an IP
    write-through if cache-miss
    :param ip_request:
    :return:
    """
    cache_res = await redis.hgetall(name=ip_request.ip)
    # write-through
    if cache_res is None:
        # cache miss
        db_res = reader.city(ip_request.ip).__dict__["raw"]
        db_res = utils.flatten(db_res)
        await redis.hset(
            name=ip_request.ip,
            mapping=db_res
        )
    else:
        # cache hit
        return cache_res

    return db_res


@app.post(
    "/insert",
)
async def insert_ip(ip: IPModel):
    out = await geo_ip(ip)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ip_log (ip, time) VALUES (%s, CURRENT_TIMESTAMP);", (str(ip.ip), ))
    conn.commit()
    return out
