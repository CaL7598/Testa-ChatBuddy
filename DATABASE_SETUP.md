# Database setup — PostgreSQL, Supabase, or SQLite

Testa StudyBuddy uses **Django’s ORM**. Use **PostgreSQL** for production and large datasets—including **Supabase**, which provides managed PostgreSQL. Use **SQLite** for quick local development without a database server.

---

## Option A: Supabase PostgreSQL (hosted — recommended for deployment)

**Supabase is standard PostgreSQL.** Django connects the same way; you do not need the Supabase JavaScript client for this app. Django still uses its own **auth** (`django.contrib.auth`) and stores data through the ORM.

### 1. Create a Supabase project

1. Sign up at [https://supabase.com](https://supabase.com)
2. **New project** → choose region and set a **database password** (save it)

### 2. Copy the connection string

In the dashboard: **Project Settings → Database → Connection string → URI**

- For **`migrate`** and **`createsuperuser`**, use **Session mode** (direct), usually port **5432**
- For production traffic you can later use the **Transaction pooler** (port **6543**); run migrations on session/direct first

Example shape (yours will differ):

```text
postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
```

### 3. Configure `.env`

```env
DB_ENGINE=postgresql
DATABASE_URL=postgresql://postgres.xxxxx:YOUR_PASSWORD@aws-0-xxxxx.pooler.supabase.com:5432/postgres
POSTGRES_SSLMODE=require

OPENROUTER_API_KEY=your_key_here
```

`DATABASE_URL` takes priority over `POSTGRES_*` when both are set.

### 4. Install driver and migrate

```powershell
pip install psycopg2-binary
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### What you use vs what you skip (for this Django app)

| Supabase feature | Used in Testa StudyBuddy? |
|------------------|---------------------------|
| **PostgreSQL database** | Yes — all Django models |
| Supabase Auth | No — Django login/register |
| Supabase Storage | No — files on local `media/` |
| Supabase Realtime / Edge Functions | No |
| Row Level Security (RLS) | Optional — Django connects with the DB user from the URI (bypasses RLS unless you design policies for direct SQL clients) |

### Thesis / documentation line

> Production data is stored in **PostgreSQL** hosted on **Supabase**, providing scalability, backups, and a managed database while the application layer remains **Django** with ORM migrations.

---

## Option B: Local PostgreSQL

### 1. Install PostgreSQL

- **Windows:** [PostgreSQL installer](https://www.postgresql.org/download/windows/)
- **Docker:**

```powershell
docker run --name testa-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=testa_studybuddy -p 5432:5432 -d postgres:16
```

### 2. Install the Python driver

```powershell
pip install psycopg2-binary
```

Or install all dependencies:

```powershell
pip install -r requirements.txt
```

### 3. Configure `.env`

Copy `.env.example` to `.env`:

```env
DB_ENGINE=postgresql
POSTGRES_DB=testa_studybuddy
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

OPENROUTER_API_KEY=your_key_here
```

### 4. Create the database (if not using Docker)

In `psql` or pgAdmin:

```sql
CREATE DATABASE testa_studybuddy;
```

### 5. Run migrations

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 6. (Optional) Move data from SQLite

```powershell
# Export while on SQLite (DB_ENGINE=sqlite or unset)
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 2 > data_backup.json

# Set DB_ENGINE=postgresql in .env, migrate, then:
python manage.py loaddata data_backup.json
```

---

## Option C: SQLite (local development)

In `.env`:

```env
DB_ENGINE=sqlite
```

Or omit `DB_ENGINE` (SQLite is the default).

```powershell
python manage.py migrate
python manage.py runserver
```

Creates `db.sqlite3` in the project root.

---

## What is stored where

| Data | Location |
|------|----------|
| Users, Q&A, quizzes, analytics, bookmarks | **PostgreSQL** or SQLite |
| Uploaded PDFs / DOCX / PPTX | Disk (`media/`) |
| Document vectors (RAG) | `faiss_index/` folder |
| API keys | `.env` |

---

## Configuration (`testa_project/settings.py`)

| `DB_ENGINE` | Backend |
|-------------|---------|
| `postgresql` + `DATABASE_URL` | Supabase / any hosted Postgres URI |
| `postgresql` + `POSTGRES_*` | Local or custom Postgres |
| `sqlite` | `django.db.backends.sqlite3` (default) |

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `No module named 'psycopg2'` | `pip install psycopg2-binary` |
| `connection refused` | Start PostgreSQL; check `POSTGRES_HOST` / `PORT` (5432) |
| `database "testa_studybuddy" does not exist` | `CREATE DATABASE testa_studybuddy;` |
| `password authentication failed` | Fix `POSTGRES_USER` / `POSTGRES_PASSWORD` |
| Supabase `SSL required` | Set `POSTGRES_SSLMODE=require` |
| Supabase connection timeout | Use Session/direct URI (5432), not pooler, for `migrate` |
| `relation does not exist` | Run `python manage.py migrate` on the Supabase database |

---

## Documentation wording

> Relational data is managed through Django ORM. **PostgreSQL** is used as the production database to support high record volume and concurrent users; **SQLite** is available for lightweight local development.
