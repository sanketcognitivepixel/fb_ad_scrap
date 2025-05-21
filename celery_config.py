from celery.schedules import crontab
import platform

# Redis Cloud settings
REDIS_HOST = 'redis-13971.c246.us-east-1-4.ec2.redns.redis-cloud.com'
REDIS_PORT = 13971
REDIS_USERNAME = 'default'
REDIS_PASSWORD = 'rJ6H8vLmMhJ9b304Nq85k3oBsEdl8Njj'

# Broker and backend URLs with authentication
broker_url = f'redis://{REDIS_USERNAME}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0'
result_backend = f'redis://{REDIS_USERNAME}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0'

# Task settings
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

# Windows-specific settings
if platform.system() == 'Windows':
    broker_connection_retry_on_startup = True
    worker_pool_restarts = True
    task_track_started = True
    worker_concurrency = 1  # Run single worker on Windows
    worker_pool = 'solo'  # Use solo pool instead of prefork on Windows
else:
    # Task execution settings for non-Windows systems
    task_track_started = True
    task_time_limit = 30 * 60  # 30 minutes
    task_soft_time_limit = 25 * 60  # 25 minutes
    worker_max_tasks_per_child = 50
    worker_prefetch_multiplier = 1 