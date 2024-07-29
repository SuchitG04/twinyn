from database import conn

async def get_ip_details(ip: str):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT * FROM geoip2_network
            WHERE network = %s
            """,
            (ip, ),
        )
        res = cursor.fetchone()
    return res


async def log_ip(ip: str):
    with conn.cursor() as cursor:
        try:
            cursor.execute(
                """
                INSERT INTO ip_log
                (network, req_timestamp)
                VALUES (%s, CURRENT_TIMESTAMP)
                """,
                (ip, )
            )
        except:
            conn.rollback()
        else:
            conn.commit()
