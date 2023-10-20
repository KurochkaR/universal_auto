web: bash ./entrypoint.sh
worker: celery -A auto worker --beat --scheduler django_celery_beat.schedulers:DatabaseScheduler --loglevel=info --pool=solo
