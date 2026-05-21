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
   - **Build Command:** `./build.sh`
   - **Start Command:** `gunicorn testa_project.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
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
| `SECRET_KEY` | Generate a long random string (or use Render “Generate”) |

Render sets `RENDER_EXTERNAL_HOSTNAME` automatically (used for `ALLOWED_HOSTS` / CSRF).

Optional after first deploy:

| Key | Value |
|-----|--------|
| `CSRF_TRUSTED_ORIGINS` | `https://your-app.onrender.com` |
| `ALLOWED_HOSTS` | `your-app.onrender.com` (usually auto via Render host) |

## 4. First deploy

After deploy succeeds:

1. Open `https://<your-app>.onrender.com`
2. Register a user or create admin via **Shell** on Render:
   ```bash
   python manage.py createsuperuser
   ```

## 5. Limitations on free tier

| Item | Note |
|------|------|
| **Cold starts** | Free tier spins down; first visit may be slow |
| **RAM** | `sentence-transformers` + FAISS need memory; upgrade if workers crash |
| **Uploaded files** | Stored on ephemeral disk — **re-upload after redeploy** unless you add persistent disk or S3 |
| **FAISS index** | Rebuilt when users upload; index lost on redeploy without persistent storage |

## 6. Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails on `collectstatic` | Check build logs; ensure `whitenoise` in `requirements.txt` |
| `DisallowedHost` | Confirm `RENDER_EXTERNAL_HOSTNAME` is set (automatic on Render) |
| Database SSL error | `POSTGRES_SSLMODE=require` |
| 502 / worker timeout | Increase gunicorn `--timeout`; reduce embedding load or use paid plan |
| AI errors | Set `OPENROUTER_API_KEY` in Render env |

## 7. Custom domain (optional)

Render → your service → **Settings** → **Custom Domain** → add DNS records as shown.
