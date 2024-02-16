web: bash ./dev.sh
worker_1: celery -A auto worker --loglevel=info -Q beat_tasks_1 -n 'partner_1'
worker_2: celery -A auto worker --loglevel=info -Q beat_tasks_2 -n 'partner_2'
worker_6: celery -A auto worker --loglevel=info -Q beat_tasks_2 -n 'partner_6'
beat: celery -A auto beat -l INFO
