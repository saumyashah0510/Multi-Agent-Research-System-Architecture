"""Redis-Backed Sliding-Window Rate Limiting Engine."""

import logging
import math
import time
import uuid

from fastapi import HTTPException, Request, Response, status

from app.core.security import decode_access_token
from app.services.redis_service import get_redis_client

logger = logging.getLogger(__name__)

# Redis executes this script atomically.
# Rejected requests are NOT added to the sliding window.
SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]

local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
local ttl = tonumber(ARGV[5])

local window_start = now - window

-- Remove requests outside the current sliding window.
redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

local count = redis.call('ZCARD', key)

-- Reject the request if the limit has already been reached.
if count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local oldest_time = tonumber(oldest[2])

    local reset_time = oldest_time + window
    local retry_after = math.max(0, reset_time - now)

    return {0, count, retry_after, reset_time}
end

-- Accept and record the request.
redis.call('ZADD', key, now, member)

count = count + 1

-- Find when the oldest accepted request expires.
local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
local reset_time = tonumber(oldest[2]) + window

-- Automatically clean up inactive rate-limit keys.
redis.call('EXPIRE', key, ttl)

return {1, count, 0, reset_time}
"""


class RateLimiter:
    """Sliding-window rate limiter dependency using Redis sorted sets."""

    def __init__(
        self,
        times: int,
        seconds: int,
        key_prefix: str = "rate_limit",
    ):
        if times <= 0 or seconds <= 0:
            raise ValueError("times and seconds must be positive.")

        self.times = times
        self.seconds = seconds
        self.key_prefix = key_prefix

    def _resolve_identifier(self, request: Request) -> str:
        """Resolve authenticated user ID or fall back to client IP."""

        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            payload = decode_access_token(token)

            if payload and payload.get("sub"):
                return f"user:{payload['sub']}"

        forwarded_for = request.headers.get("X-Forwarded-For")

        if forwarded_for:
            # CodeRabbit Security (CWE-807): Use the rightmost client IP appended by
            # the trusted reverse proxy (Nginx) to prevent caller header spoofing.
            client_ip = forwarded_for.split(",")[-1].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"

    async def __call__(self, request: Request, response: Response) -> bool:
        """Apply the Redis sliding-window rate limit."""

        identifier = self._resolve_identifier(request)

        # CodeRabbit Security (CWE-799): Enforce a single unified budget per caller and operation
        # without baking raw request.url.path to prevent quota duplication on alternate paths.
        key = f"{self.key_prefix}:{identifier}"

        redis = get_redis_client()

        now_ms = time.time_ns() // 1_000_000
        window_ms = self.seconds * 1000

        member = f"{now_ms}:{uuid.uuid4().hex}"
        ttl = math.ceil(self.seconds) + 1

        try:
            result = await redis.eval(
                SLIDING_WINDOW_SCRIPT,
                1,
                key,
                now_ms,
                window_ms,
                self.times,
                member,
                ttl,
            )
        except Exception as exc:
            # Resiliency: If Redis is unavailable or times out, fail open to avoid service outage
            logger.warning("Redis rate limiter unavailable (%s). Failing open.", exc)
            return True

        allowed = int(result[0])
        request_count = int(result[1])
        retry_after_ms = int(result[2])
        reset_time_ms = int(result[3])

        remaining = max(0, self.times - request_count)

        reset_timestamp = math.ceil(reset_time_ms / 1000)

        response.headers["X-RateLimit-Limit"] = str(self.times)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_timestamp)

        if not allowed:
            retry_after = max(1, math.ceil(retry_after_ms / 1000))

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded. Maximum " f"{self.times} requests per {self.seconds}s."
                ),
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.times),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_timestamp),
                },
            )

        return True
