web: bash ./dev.sh
beat: celery -A auto beat -l INFO
worker_1: celery -A auto worker --loglevel=warning -Q beat_tasks_1 -n 'partner_1'
