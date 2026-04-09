# AI Auto Poster

AI Auto Poster is a Django-based SaaS starter for AI-assisted social publishing.

It supports:

- user signup and login
- one or more brand workspaces
- per-workspace Facebook and YouTube connections
- AI-assisted post drafting
- scheduled posts
- manual publish now from the dashboard
- usage tracking and Free / Basic / Pro plans
- Razorpay subscription checkout and webhook sync
- Celery + Redis background publishing

## Stack

- Django 5
- Celery + Redis
- SQLite by default, PostgreSQL-ready
- Gemini for AI content
- MoviePy + Pillow for short-form video creation
- Facebook Graph API
- YouTube Data API
- Razorpay Subscriptions

## Quick start

```powershell
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/admin/`

## Docker

```powershell
docker compose up --build
```

This starts:

- Django web app
- Celery worker
- Celery beat
- Redis

The app is served on `http://127.0.0.1:8000/`.

## AWS EC2 deployment

Fastest AWS path:

1. Launch an Ubuntu EC2 instance
2. Open inbound ports:
   - `80`
   - `443` later if you add HTTPS
   - `22` for SSH
3. Install Docker + Docker Compose plugin
4. Clone this repo onto the server
5. Copy `.env.example` to `.env` and fill real values
6. Start the production stack:

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

This stack includes:

- Django web app
- Celery worker
- Celery beat
- PostgreSQL
- Redis

For first live testing, you can access the app by EC2 public IP on port `80`.

Important:

- Facebook OAuth still needs a real HTTPS URL, not just raw EC2 HTTP
- YouTube OAuth also works best with a stable public redirect URL
- for production social login, point a domain to EC2 and add HTTPS

## Environment variables

Use `.env.example` as the starting point.

Core Django:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `APP_TIME_ZONE`
- `SESSION_COOKIE_SECURE`
- `CSRF_COOKIE_SECURE`
- `SECURE_SSL_REDIRECT`
- `SECURE_HSTS_SECONDS`
- `SECURE_HSTS_INCLUDE_SUBDOMAINS`
- `SECURE_HSTS_PRELOAD`
- `EMAIL_BACKEND`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS`
- `DEFAULT_FROM_EMAIL`

Database and async:

- `DB_ENGINE`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `REDIS_URL`
- `CELERY_BROKER_URL`
