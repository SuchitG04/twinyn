from typing import Annotated
from fastapi import APIRouter, HTTPException
import redis.asyncio as redis
from pydantic import AfterValidator

import db_crud
from schemas import IPModel

router = APIRouter()

redis = redis.Redis(host="localhost", port=6379, db=0)

async def cache_ip_details(ip: str):
    """Stores IP details in redis cache"""
    res = await db_crud.get_ip_details(ip)
    if res is None:
        raise HTTPException(
            status_code=404,
            detail=f"IP address {ip} was not found in MaxMind database",
        )
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
        if value is None:
            value = ""
        elif isinstance(value, bool) or not isinstance(value, (bytes, int, str, float)):
            value = str(value)
        ip_details.update({key: value})
    await redis.hset(
        name=ip,
        mapping=ip_details
    )


async def geo_ip(ip: str) -> dict:
    """Queries redis cache to get IP. Caches IP if not cached already"""
    ip_details = await redis.hgetall(name=ip)
    if not ip_details:
        await cache_ip_details(ip)

    return ip_details
