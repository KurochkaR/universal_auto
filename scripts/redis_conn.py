import os
import redis
import logging

# Create a global Redis instance
redis_instance = redis.Redis.from_url(os.environ["REDIS_URL"])


def get_logger():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
    return logging.getLogger(__name__)
