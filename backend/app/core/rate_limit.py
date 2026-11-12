"""Redis-Backed Sliding-Window Rate Limiting Engine.

Assignee Task (Issue BE-14):
- Implement sliding-window rate limiting using Redis Sorted Sets (zset).
- Identify requests by authenticated user ID (from Bearer JWT) or client IP.
- Return 429 Too Many Requests with Retry-After and X-RateLimit headers when quota is exceeded.
"""

from fastapi import Request, Response

from app.core.security import decode_access_token


class RateLimiter:
    """Sliding-window rate limiter dependency using Redis sorted sets (zset)."""

    def __init__(
        self,
        times: int,
        seconds: int,
        key_prefix: str = "rate_limit",
    ):
        """Initialize rate limiter constraint.

        Args:
            times: Maximum allowed requests within the time window.
            seconds: Window duration in seconds.
            key_prefix: Redis key namespace prefix.
        """
        self.times = times
        self.seconds = seconds
        self.key_prefix = key_prefix

    def _resolve_identifier(self, request: Request) -> str:
        """Resolve client identifier: authenticated user ID if Bearer token present, else client IP."""
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            payload = decode_access_token(token)
            if payload and payload.get("sub"):
                return f"user:{payload['sub']}"

        # Fallback to client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def __call__(self, request: Request, response: Response) -> bool:
        """Evaluate rate limit sliding window on inbound request.

        Raises:
            HTTPException: 429 Too Many Requests if request count exceeds limit.
        """
        # TODO (Assignee - BE-14):
        # 1. Resolve client identifier using self._resolve_identifier(request)
        # 2. Build redis key: f"{self.key_prefix}:{identifier}:{request.url.path}"
        # 3. Get redis client via get_redis_client()
        # 4. Use Redis sorted set (zset):
        #    now = time.time()
        #    window_start = now - self.seconds
        #    pipe = redis.pipeline()
        #    pipe.zremrangebyscore(key, 0, window_start)
        #    pipe.zadd(key, {f"{now}-{request.headers.get('x-request-id', now)}": now})
        #    pipe.zcard(key)
        #    pipe.expire(key, self.seconds)
        #    _, _, request_count, _ = await pipe.execute()
        # 5. Calculate remaining = max(0, self.times - request_count)
        # 6. Set response headers:
        #    response.headers["X-RateLimit-Limit"] = str(self.times)
        #    response.headers["X-RateLimit-Remaining"] = str(remaining)
        # 7. If request_count > self.times:
        #    retry_after = self.seconds
        #    raise HTTPException(status_code=429, detail="Too Many Requests. Rate limit exceeded.",
        #                        headers={"Retry-After": str(retry_after), ...})
        return True
