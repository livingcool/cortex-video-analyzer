from celery import Celery

# Assumes Redis is running on localhost, default port 6379
# The broker is the transport, the backend is for storing results.
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'

# Initialize the Celery application
celery = Celery(
    'project_cortex',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=['tasks']  # Explicitly tell Celery where to find our tasks file
)

# Optional configuration
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],  # Avoid pickle for security
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

if __name__ == '__main__':
    celery.start()