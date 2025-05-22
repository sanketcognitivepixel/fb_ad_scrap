from celery import Celery
import os

# Get Redis URL from environment variable
REDIS_URL = os.getenv('REDIS_URL', 'redis://default:jXXK6aQaaYmfEMSfXWwQx8hXmJOQ7tS1@redis-10575.c14.us-east-1-3.ec2.redns.redis-cloud.com:10575')

# Create Celery app
celery = Celery(
    'tasks',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['app']  # This will import tasks from app.py
)

# Celery Configuration
celery.conf.update(
    broker_connection_retry_on_startup=True,
    worker_pool_restarts=True,
    broker_connection_max_retries=None,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
)

if __name__ == '__main__':
    celery.worker_main()
