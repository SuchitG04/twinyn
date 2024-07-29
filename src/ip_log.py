from typing import Annotated
from fastapi import FastAPI
import redis.asyncio as redis
from pydantic import AfterValidator

import db_crud
from schemas import IPModel

app = FastAPI()

redis = redis.Redis(host="localhost", port=6379, db=0)

async def cache_ip_details(ip: str):
    """Stores IP details in redis cache"""
    res = await db_crud.get_ip_details(ip)
    if res is None:
        raise ValueError("IP not found in database")

    ip_details = {}
    keys = [
        "network",
        "geoname_id",
        "registered_country_geoname_id",
        "represented_country_geoname_id",
        "is_anonymous_proxy",
        "is_satellite_provider",
        "postal_code",
        "latitude",
        "longitude",
        "accuracy_radius",
        "is_anycast"
    ]
    for key, value in zip(keys, res):
        ip_details.update({key: value})
    await redis.hset(
        name=ip,
        mapping=ip_details
    )


async def geo_ip(ip: str) -> dict:
    """Queries redis cache to get IP. Writes through to the database if cache miss occurs"""
    ip_info = await redis.hgetall(name=ip)
    if not ip_info:
        await cache_ip_details(ip)
    return ip_info


@app.post("/insert")
async def insert_ip(request_ip: Annotated[IPModel, AfterValidator(lambda x: x.ip)]):
    """Logs IP and inserts IP details into redis cache"""
    await db_crud.log_ip(str(request_ip))
    ip_details = await geo_ip(str(request_ip))
    return ip_details
