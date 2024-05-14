from __future__ import absolute_import

import sentry_sdk
from celery import Celery, signals
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto.settings')

app = Celery('auto')


@signals.worker_init.connect
def init_sentry(**_kwargs):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        enable_tracing=True
    )


app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.update(
    task_ignore_result=True,
    task_serializer='json',
    result_serializer='json',
    timezone='Europe/Kiev',
    worker_heartbeat_interval=25,
    task_prefetch_multiplier=1,
    redis_max_connections=50,
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        'retry_policy': {
            'timeout': 5.0
        },
        'visibility_timeout': 1800,
        'health_check_interval': 10,
        'max_retries': 3,
        'max_connections': 50,
        'retry_on_timeout': True,
        'connection_retry': True,
        'connection_timeout': 120,
        'connection_max_retries': 0,
        'socket_keepalive': True,
        'socket_timeout': 10,
        'socket_connect_timeout': 60
    },
    result_backend_transport_options={
        'retry_policy': {
            'timeout': 5.0
        },
    }
)

app.autodiscover_tasks(['auto'])
