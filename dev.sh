sudo nginx -g 'daemon on;'
gunicorn auto.wsgi:application --bind "0.0.0.0:8000" --log-level debug --reload --timeout 600 --worker-class=gevent --worker-connections=100 --workers=1