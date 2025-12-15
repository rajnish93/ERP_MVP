from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize Limiter
# key_func=get_remote_address uses the client's IP address
limiter = Limiter(key_func=get_remote_address)

__all__ = ["limiter", "RateLimitExceeded", "_rate_limit_exceeded_handler"]
