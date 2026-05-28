# Get Testa StudyBuddy on Google Search

Google does not index a site automatically. You need **public pages**, a **sitemap**, and **Google Search Console** to request indexing.

## What the app already provides

After you deploy with `SITE_URL` set:

| URL | Purpose |
|-----|---------|
| `https://your-app.onrender.com/robots.txt` | Tells Google what to crawl |
| `https://your-app.onrender.com/sitemap.xml` | Lists public pages (home, about, login, register) |
| Meta tags on pages | Title, description, canonical URL, Open Graph |
| `GOOGLE_SITE_VERIFICATION` (optional) | Proves you own the site to Google |

Private areas (Q&A, analytics, profile, etc.) are **disallowed** in `robots.txt` so Google focuses on your landing page.

---

## Step 1 — Render environment

Add or confirm in **Render → Environment**:

```env
SITE_URL=https://testa-chatbuddy.onrender.com
SITE_NAME=Testa StudyBuddy
```

Use your real Render URL (no trailing slash). Redeploy.

Verify in the browser:

- `https://testa-chatbuddy.onrender.com/robots.txt` — should list `Sitemap: https://.../sitemap.xml`
- `https://testa-chatbuddy.onrender.com/sitemap.xml` — should list `/`, `/about/`, `/register/`, `/login/`

---

## Step 2 — Google Search Console

1. Open [Google Search Console](https://search.google.com/search-console).
2. Click **Add property** → choose **URL prefix**.
3. Enter: `https://testa-chatbuddy.onrender.com` (your live URL).
4. **Verify ownership**

   **Option A — HTML file (recommended if you downloaded `google*.html`)**

   This repo serves your verification file at the site root:

   `https://testa-chatbuddy.onrender.com/googlef9819ca33b10c69b.html`

   1. Deploy the latest code to Render.
   2. Open that URL in your browser — you should see exactly one line:  
      `google-site-verification: googlef9819ca33b10c69b.html`
   3. In Search Console, choose the **HTML file** method and click **Verify**.

   You do **not** need to upload the file to Render manually; the app serves it.

   **Option B — HTML meta tag**

   - Copy the `content="..."` value from Google’s meta tag.
   - On Render: `GOOGLE_SITE_VERIFICATION=your_code`
   - Redeploy and click **Verify**.

---

## Step 3 — Submit sitemap

In Search Console for your property:

1. Go to **Sitemaps** (left menu).
2. Enter: `sitemap.xml`
3. Click **Submit**.

Status should become “Success” after Google fetches it (can take hours).

---

## Step 4 — Request indexing (homepage)

1. In Search Console, use **URL inspection** (top search bar).
2. Paste: `https://testa-chatbuddy.onrender.com/`
3. Click **Request indexing**.

Repeat for `/about/` if you want that page indexed too.

---

## Step 5 — Wait and improve

- **First appearance in Google** often takes **a few days to several weeks** for new sites.
- Free Render apps **sleep when idle** — Google can still crawl them, but responses may be slow on cold start.
- Improve rankings over time:
  - Clear, unique **title** and **description** on the landing page (already set in templates).
  - Link to your app from social profiles, GitHub README, or a university page.
  - Keep the site **public** (landing + about + register) — login-only homepages are hard to index.

---

## Optional env vars

| Variable | Example |
|----------|---------|
| `SEO_DESCRIPTION` | Custom default meta description |
| `GOOGLE_SITE_VERIFICATION` | Code from Search Console HTML tag method |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `robots.txt` has no Sitemap line | Set `SITE_URL` on Render and redeploy |
| Verification fails | Confirm `GOOGLE_SITE_VERIFICATION` matches Google’s tag exactly; redeploy |
| Sitemap “Couldn’t fetch” | Open `/sitemap.xml` in browser; fix 502/cold start; try again later |
| Site never appears | Normal for new domains; keep property verified and sitemap submitted |
| Wrong URL in search results | `SITE_URL` must match the URL you added in Search Console |

---

## Checklist

- [ ] `SITE_URL` set on Render
- [ ] `/robots.txt` and `/sitemap.xml` work in browser
- [ ] Search Console property added and verified
- [ ] Sitemap submitted
- [ ] Homepage “Request indexing” submitted
- [ ] Wait 1–2 weeks and search: `Testa StudyBuddy` or `site:testa-chatbuddy.onrender.com`
