"""
Rate limiting module to enforce Google Sheets API limits.
"""

import time
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Enforces rate limiting based on Google Sheets API quotas.
    
    Tracks read/write requests per minute and total requests per 100 seconds.
    """
    
    def __init__(
        self,
        read_requests_per_minute: int = 300,
        write_requests_per_minute: int = 60,
        total_requests_per_100_seconds: int = 500
    ):
        """
        Initialize the rate limiter.
        
        Args:
            read_requests_per_minute: Maximum read requests per minute
            write_requests_per_minute: Maximum write requests per minute
            total_requests_per_100_seconds: Maximum total requests per 100 seconds
        """
        self.read_requests_per_minute = read_requests_per_minute
        self.write_requests_per_minute = write_requests_per_minute
        self.total_requests_per_100_seconds = total_requests_per_100_seconds
        
        self.last_request_time = 0
        self.request_count_100s = 0
        self.read_request_count = 0
        self.write_request_count = 0
        self.minute_start_time = time.time()
    
    def check(self, request_type: str = "read") -> None:
        """
        Check and enforce rate limits before making a request.
        
        Args:
            request_type: Type of request - "read" or "write"
        """
        current_time = time.time()
        
        # Reset minute counters if a minute has passed
        if current_time - self.minute_start_time >= 60:
            self.read_request_count = 0
            self.write_request_count = 0
            self.minute_start_time = current_time
        
        # Check 100-second window for total requests
        if current_time - self.last_request_time > 100:
            self.request_count_100s = 0
        elif self.request_count_100s >= self.total_requests_per_100_seconds:
            sleep_time = 100 - (current_time - self.last_request_time)
            logger.warning(f"Total requests limit approaching. Sleeping for {sleep_time:.1f} seconds")
            time.sleep(max(sleep_time, 1))
            self.request_count_100s = 0
        
        # Check per-minute limits for read/write
        if request_type == "read" and self.read_request_count >= self.read_requests_per_minute:
            logger.warning("Read limit reached. Sleeping for 60 seconds")
            time.sleep(60)
            self.read_request_count = 0
            self.minute_start_time = time.time()
        elif request_type == "write" and self.write_request_count >= self.write_requests_per_minute:
            logger.warning("Write limit reached. Sleeping for 60 seconds")
            time.sleep(60)
            self.write_request_count = 0
            self.minute_start_time = time.time()
        
        # Update counters
        self.request_count_100s += 1
        if request_type == "read":
            self.read_request_count += 1
        else:
            self.write_request_count += 1
        self.last_request_time = current_time
