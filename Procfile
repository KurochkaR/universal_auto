web: bash ./dev.sh
beat: celery -A auto beat -l INFO
worker_1: celery -A auto worker --loglevel=info --pool=solo -n 'partner_1'
