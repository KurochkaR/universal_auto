web: bash ./dev.sh
worker_1: celery -A auto worker --loglevel=debug -Q='beat_tasks_1' -n 'kut_1'
worker: celery -A auto worker --loglevel=info
beat: celery -A auto beat -l DEBUG
