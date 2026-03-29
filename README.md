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

Database and async:

- `DB_ENGINE`
- `DB_NAME`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `ASYNC_TASKS_ENABLED`

AI and media:

- `GEMINI_API_KEY`
- `UNSPLASH_ACCESS_KEY`
- `PEXELS_API_KEY`

Fallback platform credentials:

- `FB_PAGE_ID`
- `FB_PAGE_ACCESS_TOKEN`
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

OAuth config:

- `FACEBOOK_OAUTH_APP_ID`
- `FACEBOOK_OAUTH_APP_SECRET`
- `FACEBOOK_OAUTH_REDIRECT_URI`
- `YOUTUBE_OAUTH_CLIENT_ID`
- `YOUTUBE_OAUTH_CLIENT_SECRET`
- `YOUTUBE_OAUTH_REDIRECT_URI`

Archive and billing:

- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_WEBHOOK_SECRET`
- `RAZORPAY_PLAN_IDS`

## How the app works

1. Create an account.
2. Create a workspace.
3. Connect Facebook and YouTube from the dashboard.
4. Create or refine an AI-assisted post.
5. Schedule it or publish immediately.
6. Upgrade to a paid plan from the pricing table.

## Connected account fields

### Facebook

- `Platform`: `facebook`
- `Account name`: any readable label
- `Account identifier`: Facebook Page ID
- `Access token`: Page access token
- `Is connected`: enabled

Dashboard OAuth route:

- `/app/accounts/connect/facebook/`

Required env for OAuth:

- `FACEBOOK_OAUTH_APP_ID`
- `FACEBOOK_OAUTH_APP_SECRET`
- `FACEBOOK_OAUTH_REDIRECT_URI`

### YouTube

- `Platform`: `youtube`
- `Account name`: channel label
- `Client ID`: Google OAuth client ID
- `Client secret`: Google OAuth client secret
- `Refresh token`: YouTube refresh token
- `Token URI`: usually the default Google token URI
- `Is connected`: enabled

Dashboard OAuth route:

- `/app/accounts/connect/youtube/`

Required env for OAuth:

- `YOUTUBE_OAUTH_CLIENT_ID`
- `YOUTUBE_OAUTH_CLIENT_SECRET`
- `YOUTUBE_OAUTH_REDIRECT_URI`

## Publishing behavior

- The app tries workspace-connected accounts first.
- If a workspace account is missing, it falls back to environment credentials.
- Instagram is not implemented yet.
- When `ASYNC_TASKS_ENABLED=1`, manual publish requests are queued to Celery.

## Background jobs

Celery beat publishes due scheduled posts every minute through:

- `posting.tasks.publish_due_posts_task`

Manual publish from the dashboard can also be queued through:

- `posting.tasks.publish_single_post_task`

You can still trigger due posts manually:

```powershell
python manage.py process_scheduled_posts
```

Recommended production async env:

```env
ASYNC_TASKS_ENABLED=1
REDIS_URL=redis://your-redis-host:6379/0
CELERY_BROKER_URL=redis://your-redis-host:6379/0
CELERY_RESULT_BACKEND=redis://your-redis-host:6379/0
```

## Razorpay subscriptions

Paid plans use Razorpay Subscriptions.

Set:

- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_WEBHOOK_SECRET`
- `RAZORPAY_PLAN_IDS`

Example:

```env
RAZORPAY_PLAN_IDS={"basic":"plan_xxxxx","pro":"plan_yyyyy"}
```

Webhook endpoint:

- `/app/billing/razorpay/webhook/`

Recommended webhook events:

- `subscription.authenticated`
- `subscription.activated`
- `subscription.charged`
- `subscription.cancelled`
- `subscription.completed`
- `subscription.pending`
- `subscription.halted`

The app verifies:

- checkout signatures on the Razorpay return flow
- webhook signatures using `RAZORPAY_WEBHOOK_SECRET`

## Tests

```powershell
python manage.py check
python manage.py test dashboard social_accounts
```

## Deployment notes

For Render, Railway, or AWS-style deployments:

- run the `web` process with Gunicorn
- run a separate Celery worker process
- run a separate Celery beat process
- use PostgreSQL in production
- set secure cookie and SSL env vars
- point webhooks and OAuth redirect URIs at the public HTTPS domain

Included deployment artifacts:

- [Procfile](/C:/p%20practice/ai-auto-poster/Procfile)
- [Dockerfile](/C:/p%20practice/ai-auto-poster/Dockerfile)
- [docker-compose.yml](/C:/p%20practice/ai-auto-poster/docker-compose.yml)

## Current limitations

- Facebook publishing is currently a photo post generated from the video thumbnail
- Instagram publishing is not implemented yet
- Video generation and publishing still depend on valid third-party credentials and quotas

## Legacy scripts

The original script-based pipeline is still present:

- `poster.py`
- `generate_content.py`
- `create_video.py`
- `post_facebook.py`
- `post_youtube.py`

The Django app uses those modules through a service layer so the migration path stays incremental.
