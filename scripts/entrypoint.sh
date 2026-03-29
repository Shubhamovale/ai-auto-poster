#!/bin/sh
set -e

if [ "${DB_ENGINE}" = "django.db.backends.postgresql" ]; then
  echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT:-5432}..."
  until python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('${DB_HOST}', int('${DB_PORT:-5432}'))); s.close()" 2>/dev/null; do
    sleep 2
  done
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
