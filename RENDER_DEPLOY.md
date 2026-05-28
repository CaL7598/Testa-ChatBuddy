# Deploy Testa StudyBuddy on Render

## Prerequisites

- GitHub repo pushed (this project)
- [Supabase](https://supabase.com) database with **Session pooler** URI (port 5432)
- [OpenRouter](https://openrouter.ai) API key

## 1. Push to GitHub

Ensure `.env` is **not** committed (it is in `.gitignore`).

## 2. Create Web Service on Render

1. Go to [https://dashboard.render.com](https://dashboard.render.com) → **New +** → **Web Service**
2. Connect repository: `CaL7598/Testa-ChatBuddy` (or your fork)
3. Settings:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements-render.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput`
   - **Start Command:** `gunicorn testa_project.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 180`
   - **Plan:** Free (upgrade if ML models run out of memory)

Or use **Blueprint** deploy with `render.yaml` in the repo root.

## 3. Environment variables (Render dashboard)

| Key | Value |
|-----|--------|
| `DEBUG` | `False` |
| `DB_ENGINE` | `postgresql` |
| `DATABASE_URL` | Your Supabase Session URI (port 5432) |
| `POSTGRES_SSLMODE` | `require` |
| `OPENROUTER_API_KEY` | Your OpenRouter key |
| `SENDGRID_API_KEY` | SendGrid API key (Mail Send permission) |
| `DEFAULT_FROM_EMAIL` | `adubeasarah44@gmail.com` (verified SendGrid sender) |
| `SUPPORT_EMAIL` | `adubeasarah44@gmail.com` |
| `SITE_URL` | `https://testa-chatbuddy.onrender.com` |
| `GOOGLE_SITE_VERIFICATION` | (Optional) From [Google Search Console](https://search.google.com/search-console) HTML tag — see `GOOGLE_INDEXING.md` |
| `SECRET_KEY` | Generate a long random string (or use Render “Generate”) |

Render sets `RENDER_EXTERNAL_HOSTNAME` automatically (used for `ALLOWED_HOSTS` / CSRF).

Optional after first deploy:

| Key | Value |
|-----|--------|
| `CSRF_TRUSTED_ORIGINS` | `https://your-app.onrender.com` |
| `ALLOWED_HOSTS` | `your-app.onrender.com` (usually auto via Render host) |

## 4. Google Search indexing

After deploy, follow **[GOOGLE_INDEXING.md](GOOGLE_INDEXING.md)** to verify the site in Search Console and submit `sitemap.xml`.

## 5. First deploy

After deploy succeeds:

1. Open `https://<your-app>.onrender.com`
2. Register a user or create admin via **Shell** on Render:
   ```bash
   python manage.py createsuperuser
   ```

## 6. Limitations on free tier

| Item | Note |
|------|------|
| **Cold starts** | Free tier spins down; first visit may be slow |
| **RAM** | Production uses `requirements-render.txt` (no PyTorch/FAISS). Q&A uses OpenRouter only. Upgrade plan if you need on-server RAG. |
| **Uploaded files** | Stored on ephemeral disk — **re-upload after redeploy** unless you add persistent disk or S3 |
| **FAISS index** | Rebuilt when users upload; index lost on redeploy without persistent storage |

## 7. Troubleshooting

| Issue | Fix |
|-------|-----|
| **Blank page / nothing loads** | Open Render **Logs**; confirm `DATABASE_URL` is set (Supabase Session URI, port **5432**). Test `https://your-app.onrender.com/health/` — should return `{"status":"ok"}`. |
| **Site spins forever** | Free tier cold start (wait 60–90s). Or DB connection hanging — fix `DATABASE_URL`. |
| Build fails on `collectstatic` | Check build logs; ensure `whitenoise` in `requirements.txt` |
| `DisallowedHost` | Add `testa-chatbuddy.onrender.com` to `ALLOWED_HOSTS` or rely on `RENDER_EXTERNAL_HOSTNAME` |
| Database SSL error | `POSTGRES_SSLMODE=require` |
| 502 / worker OOM | Use `requirements-render.txt`, `DISABLE_ML=1`, `--workers 1`. In Render **Settings**, set Build Command to match `render.yaml`. |
| AI errors | Set `OPENROUTER_API_KEY` in Render env |

**Health check:** `GET /health/` returns JSON without touching the database.

## 8. Custom domain (optional)

Render → your service → **Settings** → **Custom Domain** → add DNS records as shown.
