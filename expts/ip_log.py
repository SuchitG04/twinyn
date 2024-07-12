import os
import geoip2.database
from fastapi import FastAPI
import redis.asyncio as redis
from dotenv import load_dotenv

from database import conn
from schemas import IPModel

app = FastAPI()
load_dotenv()

GEOIP_DB = os.getenv("GEOIP_DB")
reader = geoip2.database.Reader(GEOIP_DB)
redis = redis.Redis(host="localhost", port=6379, db=0)


async def geo_ip(ip_request: IPModel) -> dict:
    """Queries redis cache to get ip. Writes through to the database if cache miss occurs"""
    cached_ip_info = await redis.hgetall(name=str(ip_request.ip))

    # cache miss
    if not cached_ip_info:
        ip_info = reader.city(ip_request.ip).__dict__["raw"]
        out_info = {
            "continent": ip_info["continent"]["names"]["en"],
            "country": ip_info["country"]["names"]["en"],
            "registered_country": ip_info["registered_country"]["names"]["en"],
            "time_zone": ip_info["location"]["time_zone"],
            "latitude": ip_info["location"]["latitude"],
            "longitude": ip_info["location"]["longitude"],
        }
        await redis.hset(name=str(ip_request.ip), mapping=out_info)
        return out_info

    # cache hit
    decoded_ip_info = {k.decode(): v.decode() for k, v in cached_ip_info.items()}
    decoded_ip_info = {
        k: (float(v) if v.replace(".", "").isdigit() else v)
        for k, v in decoded_ip_info.items()
    }
    return decoded_ip_info


@app.post(
    "/insert",
)
async def insert_ip(ip: IPModel):
    ip_info = await geo_ip(ip)
    with conn.cursor() as cursor:
        try:
            cursor.execute(
                """
                INSERT INTO ip_info
                (continent, country, registered_country, time_zone, latitude, longitude)
                VALUES (%(continent)s, %(country)s, %(registered_country)s, %(time_zone)s, %(latitude)s, %(longitude)s)
                RETURNING id
                """,
                ip_info,
            )
            ip_info_id = cursor.fetchone()[0]
            cursor.execute(
                """
                INSERT INTO ip_logs (ip, request_timestamp, ip_info_id)
                VALUES (%s, CURRENT_TIMESTAMP, %s)
                """,
                (str(ip.ip), ip_info_id),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    return ip_info
