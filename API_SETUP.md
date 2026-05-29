# API Setup Guide for Testa StudyBuddy

## Required: OpenRouter API (DeepSeek model)

The project uses **DeepSeek** for all text generation, accessed through **OpenRouter**:

- AI-powered question answering (with RAG context)
- Quiz generation
- Flashcard generation
- Study guide and summary generation

**Embeddings** (document search) use **sentence-transformers** locally — no API key required for that step.

For full technical documentation (architecture, request/response structure, integration points), see **[DEEPSEEK_API_DOCUMENTATION.md](DEEPSEEK_API_DOCUMENTATION.md)**.

---

### How to get your API key

1. Go to [https://openrouter.ai](https://openrouter.ai) and create an account.
2. Open **Keys** in the dashboard and create an API key.
3. Add credits if required by OpenRouter for your chosen model.

### Configure the project

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=sk-or-v1-your_key_here
```

The app loads this automatically via `python-dotenv` when `bytez_client.py` is imported.

**Windows (PowerShell, session only):**

```powershell
$env:OPENROUTER_API_KEY="sk-or-v1-your_key_here"
```

**Linux / macOS:**

```bash
export OPENROUTER_API_KEY="sk-or-v1-your_key_here"
```

### Model used

| Setting | Value |
|---------|--------|
| Provider | OpenRouter |
| Model ID | `deepseek/deepseek-chat` (DeepSeek V3) |
| Endpoint | `https://openrouter.ai/api/v1/chat/completions` |
| Configured in | `testa_app/bytez_client.py` → `DEFAULT_MODEL` |

---

## Where the API is used in code

| File | Role |
|------|------|
| `testa_app/bytez_client.py` | HTTP client, retries, `answer_question`, `generate_text` |
| `testa_app/utils.py` | RAG chain, quiz/flashcard/summary generators |
| `testa_app/views.py` | Q&A view when RAG does not return an answer |
| `testa_app/study_assistant_views.py` | Quiz, flashcard, summary, study guide pages |

Shared accessor:

```python
from testa_app.bytez_client import get_bytez_client

client = get_bytez_client()
answer = client.answer_question("What is photosynthesis?", context=document_chunks)
```

---

## Testing your API key

1. Ensure `.env` contains `OPENROUTER_API_KEY`.
2. Run: `python manage.py runserver`
3. Log in and ask a question on the Q&A page.
4. If you see configuration errors, verify the key and OpenRouter account status.

---

## Security

- Do **not** commit `.env` to Git (it should stay in `.gitignore`).
- Do not expose API keys in screenshots or reports.
- Use separate keys for development and production if you deploy publicly.

---

## Troubleshooting

| Problem | What to check |
|---------|----------------|
| `OPENROUTER_API_KEY not found` | `.env` in project root, correct variable name |
| 401 / `User not found` | Key was **deleted or revoked** on OpenRouter — create a **new** key at [openrouter.ai/keys](https://openrouter.ai/keys) and update Render + `.env` |
| 401 / 403 / "Authentication error" | Invalid or missing `OPENROUTER_API_KEY`; add credits at [openrouter.ai/credits](https://openrouter.ai/credits) |
| Test on Render | Shell: `python manage.py check_openrouter` |
| Works locally, fails on Render | Key is only in local `.env` — copy the same `OPENROUTER_API_KEY` to Render and redeploy |
| Timeout | Network; try again; large `max_tokens` requests take longer |
| `sentence-transformers not installed` | `pip install sentence-transformers` (embeddings only) |

---

## Legacy note (Bytez)

Earlier versions used the Bytez API (`BYTEZ_API_KEY`). The current codebase uses **OpenRouter + DeepSeek** only. Old Bytez client code is commented out at the bottom of `bytez_client.py` for reference.

---

## Further reading

- [DEEPSEEK_API_DOCUMENTATION.md](DEEPSEEK_API_DOCUMENTATION.md) — structure, flows, and methodology text
- [METHODOLOGY_NOTES.md](METHODOLOGY_NOTES.md) — RAG pipeline and system design
- OpenRouter docs: [https://openrouter.ai/docs](https://openrouter.ai/docs)
