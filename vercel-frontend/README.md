# Vercel Frontend

This folder is a static frontend package for Vercel.

## What it does

- Hosts the marketing landing page on Vercel
- Hosts clean `/login` and `/signup` handoff pages
- Sends auth actions to the Django backend domain configured in `config.js`

## Backend domain

Update `config.js`:

```js
window.APP_CONFIG = {
  BACKEND_BASE_URL: "https://app.aiautoposter.com"
};
```

Use your real Django backend domain there.

## Vercel setup

- Import this `vercel-frontend` folder as the project root
- Or keep deploying this folder only as a static site

## Important

The real login and signup form submission still happens on the backend app.
