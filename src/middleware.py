from starlette.middleware.base import BaseHTTPMiddleware

class ServerAccessLoggerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, conn):
        super().__init__(app)
        self.conn = conn

    @staticmethod
    def _build_log_args(request, response):
        out = [
            request.scope["client"][0],
            f"{request.method} {request.scope['path']} " + \
            f"{request.scope['type'].upper()}/{request.scope['http_version']}",
            response.status_code,
            response.headers["content-length"],
            dict(request.scope["headers"]).get(b"referer", b"").decode(),
            request.headers["user-agent"]
        ]
        def handle_null(value):
            return "-" if value == "" else value

        out = [handle_null(val) for val in out]
        return tuple(out)

    async def _log(self, log_args):
        """Logs request and response in the PostgreSQL database following the Common Log Format extended
        extended with user-agent and referer."""
        with self.conn.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    INSERT INTO server_log
                    VALUES (%s, NOW(), %s, %s, %s, %s, %s)
                    """,
                    log_args
                )
            except Exception as e:
                print("Exceptiion: ", e)
                self.conn.rollback()
            else:
                self.conn.commit()

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        log_args = self._build_log_args(request, response)
        await self._log(log_args)
        return response