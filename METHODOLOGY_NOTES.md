# Methodology Notes — UENR Testa StudyBuddy

Key technical details for writing the methodology section of the project documentation.

---

## 1. System Architecture

- **Framework**: Django 5.0.3 using the MVT (Model-View-Template) architectural pattern
- **Database**: Django ORM — **PostgreSQL** for production/large datasets (`DB_ENGINE=postgresql`, optional **Supabase** via `DATABASE_URL`); **SQLite** by default for local dev; see [DATABASE_SETUP.md](DATABASE_SETUP.md); indexes on `user`, `created_at`, `course`, `topic`, and `upvotes` fields
- **Server**: WSGI-based application server (`testa_project/wsgi.py`)
- **Session management**: Django session middleware handles user authentication state
- **URL routing**: Centralised in `testa_project/urls.py`

---

## 2. AI & NLP Pipeline — Retrieval-Augmented Generation (RAG)

The core question-answering feature is built on a RAG pipeline:

| Step | Description | Technology |
|------|-------------|------------|
| 1. Document ingestion | Extract raw text from uploaded files | PyPDF2, python-docx, python-pptx |
| 2. Text chunking | Split text into overlapping segments | LangChain `RecursiveCharacterTextSplitter` (chunk size: 50,000 chars, overlap: 1,000 chars) |
| 3. Embedding | Convert chunks to numerical vectors | Sentence Transformers `all-MiniLM-L6-v2` (384 dimensions, runs locally) |
| 4. Vector storage | Index and persist embeddings for similarity search | FAISS (Facebook AI Similarity Search), saved to `faiss_index/` on disk |
| 5. Retrieval | Find relevant chunks for a given question | FAISS cosine similarity search |
| 6. Answer generation | Generate a natural language answer using retrieved context | OpenRouter API → DeepSeek V3 (`deepseek/deepseek-chat`) |

**Performance optimisation**: The embedding model and FAISS index are cached in memory. The index is only reloaded from disk when the file modification time changes, avoiding repeated I/O on every request.

**Fallback mechanism**: If no document context is available, a web scrape (BeautifulSoup + Google Search) is used to retrieve supplementary information.

---

## 3. Document Processing

**Supported file formats**: PDF, DOCX (Word), PPTX (PowerPoint), TXT

**Extraction methods**:
- PDF — `PyPDF2.PdfReader`, iterates over all pages
- DOCX — `python-docx`, joins all paragraph text
- PPTX — `python-pptx`, iterates over slides and extracts shape text
- TXT — direct UTF-8 decode

**Index management**: New document uploads extend (merge into) the existing FAISS index rather than replacing it, preserving all previously indexed content.

---

## 4. Large Language Model (LLM) Integration — DeepSeek API

> **Full documentation:** See [DEEPSEEK_API_DOCUMENTATION.md](DEEPSEEK_API_DOCUMENTATION.md) for architecture diagrams, request/response structure, sequence flows, and thesis-ready wording.

### 4.1 Provider and model

- **Gateway**: [OpenRouter](https://openrouter.ai) — OpenAI-compatible `POST /v1/chat/completions`
- **Model**: **DeepSeek Chat** (`deepseek/deepseek-chat`, DeepSeek V3 family)
- **Why DeepSeek**: Strong educational Q&A, reliable **JSON** for quizzes/flashcards, cost-effective via OpenRouter
- **API key**: `OPENROUTER_API_KEY` in `.env` (loaded by `python-dotenv`)

Embeddings for RAG are **not** sent to DeepSeek; they use local **sentence-transformers** (see Section 2).

### 4.2 Client structure (`testa_app/bytez_client.py`)

| Piece | Function |
|-------|----------|
| `BytezClient` | Single integration class (name retained from earlier Bytez migration) |
| `get_bytez_client()` | Process-wide singleton + shared HTTP session |
| `chat(messages)` | Low-level OpenRouter call; parses `choices[0].message.content` |
| `generate_text(prompt, system_prompt)` | Builds system + user messages |
| `answer_question(question, context)` | Q&A with RAG context and educational system prompt |
| `EmbeddingClient` | Separate — local vectors only |

### 4.3 Request payload (conceptual)

```json
{
  "model": "deepseek/deepseek-chat",
  "messages": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "Context: ...\n\nQuestion: ..." }
  ],
  "temperature": 0.3,
  "max_tokens": 768
}
```

### 4.4 Where DeepSeek is invoked

| Feature | Caller | Notes |
|---------|--------|--------|
| RAG Q&A | `get_conversational_chain()` → `answer_question` | After FAISS retrieves top-3 chunks |
| Direct Q&A | `views.question_answer` | When retrieval chain returns no answer |
| Quizzes | `QuizGenerator` | JSON parsed from model output |
| Flashcards | `FlashcardGenerator` | JSON parsed from model output |
| Summaries / study guides | `SummaryGenerator` | Longer `max_tokens` for guides |

### 4.5 Operational settings

- **Retry logic**: Up to 2 retries with exponential backoff on timeout, connection errors, or HTTP 5xx
- **Temperature**: Q&A 0.3; quiz/flashcards 0.7; summaries/guides 0.3
- **Token limits**: 768 (Q&A), 2048 (quiz/cards/summary), 4096 (study guide)
- **Fallback**: Web scrape if OpenRouter fails (`views.py`)

---

## 5. AI-Generated Study Tools

Three generator classes produce structured output by prompting the LLM and parsing the JSON response:

### QuizGenerator
- Generates MCQ, True/False, and Short Answer questions
- Adjustable difficulty: easy, medium, hard
- Output format: JSON with `title` and `questions[]` (question, type, options, correct_answer, explanation)
- Stored in `Quiz` and `QuizQuestion` models with per-attempt scoring via `QuizAttempt`

### FlashcardGenerator
- Generates front/back card pairs from document content
- Cards stored with a confidence level (0=Not Learned, 1=Learning, 2=Comfortable, 3=Mastered)
- Review count and last-reviewed timestamp tracked for spaced repetition

### SummaryGenerator
- Three summary modes: concise (2–3 paragraphs), detailed (comprehensive), bullet_points (key concepts)
- Study guide generation includes: overview, key concepts, formulas, study tips, common mistakes, 3–5 practice questions

---

## 6. Search Engine

`AdvancedSearchEngine` class (`testa_app/search_engine.py`):

- **Keyword search**: Filters `QuestionAnswer` records across `question`, `answer`, `course`, and `topic` fields using Django ORM `Q` objects (`icontains`)
- **Relevance scoring**: Custom SQL `CASE` expression assigns scores (question match=3, answer match=2, topic match=1) to rank results
- **Filters**: course, topic, difficulty level, date range, minimum upvotes, tags, bookmarked-only, user-owned content
- **Sort options**: relevance (default), newest, oldest, popular (upvotes), rated (upvote ratio)
- **Pagination**: Configurable `per_page` (default 20)
- **Caching**: Results cached in Django's cache framework for 5 minutes, keyed by `hash(query) + hash(filters) + sort + page`
- **Search history**: Every search is saved to `SearchHistory` and `RecentSearch` models
- **Auto-complete**: Suggestions drawn from the user's personal search history or globally popular topics

---

## 7. Personalised Recommendation Engine

`RecommendationEngine` class (`testa_app/recommendation_engine.py`) generates five recommendation types, each with a priority score (0–100):

| Priority | Recommendation Type | Trigger Condition |
|----------|--------------------|--------------------|
| 90 | Weak area | `TopicMastery.mastery_level < 60%` |
| 70 | Quiz | Topic has been studied (Q&A exists) but no quiz attempt recorded |
| 60 | Next topic | Unmastered topics in the user's most-studied course |
| 60 | Flashcard review | Confidence level < 2, or last reviewed > 7 days ago (spaced repetition) |
| 50 | Document | Available documents not yet linked to any Q&A by the user |

Recommendations are sorted by priority, limited to the top 10, and persisted to the `Recommendation` model. Old incomplete recommendations are deleted before each refresh.

---

## 8. Analytics & Progress Tracking

The system tracks user learning activity across four models:

| Model | What it tracks |
|-------|---------------|
| `UserAnalytics` | Total questions asked, study time (minutes), current and longest streak (days), quiz count, average quiz score, flashcard count, favourite course |
| `DailyActivity` | Per-day counts: questions asked, study minutes, quizzes completed, flashcards reviewed |
| `TopicMastery` | Per-topic mastery level (%), questions answered, correct answers, accuracy rate, last practised timestamp |
| `StudySession` | Session start/end time, duration (seconds), questions asked, flashcards reviewed, quizzes taken, topics covered (JSON array) |

**Satisfaction scoring**: Each `QuestionAnswer` record computes a satisfaction score as `(upvotes / (upvotes + downvotes)) × 100`.

**Topic accuracy**: `TopicMastery.accuracy_rate = (correct_answers / questions_answered) × 100`

---

## 9. Data Models Summary

Core models and their relationships:

- `PDFDocument` — uploaded study materials (file, course, difficulty, uploader)
- `QuestionAnswer` — Q&A pairs linked to a user and optionally to a source document; supports tags, votes, archiving
- `Quiz` / `QuizQuestion` / `QuizAttempt` — full quiz lifecycle
- `Flashcard` — individual cards with spaced-repetition metadata
- `Bookmark` / `BookmarkFolder` — user-organised saved Q&A pairs
- `SearchHistory` / `RecentSearch` / `SavedSearch` — search tracking
- `Recommendation` — AI-generated personalised suggestions
- `UserAnalytics` / `DailyActivity` / `TopicMastery` / `StudySession` — learning analytics
- `Tag` / `Vote` / `ExportHistory` — tagging, voting, and export records

---

## 10. Frontend

- **Styling**: Tailwind CSS (utility-first) with a glassmorphism design language
- **Rendering**: Server-side Django templates (no frontend JavaScript framework)
- **Typography**: Google Fonts — Montserrat, Poppins
- **Markup**: HTML5, CSS3, vanilla JavaScript

---

## 11. Authentication & Security

- **Authentication**: Django's built-in `User` model with session-based login/logout
- **Access control**: All study views protected by `@login_required` decorator
- **CSRF protection**: Django `CsrfViewMiddleware` active on all POST requests
- **Password validation**: Four-validator chain — UserAttributeSimilarity, MinimumLength, CommonPassword, NumericPassword
- **Environment variables**: API keys loaded from `.env` via `python-dotenv` (never hard-coded)

---

## 12. Key Design Decisions

1. **RAG over pure LLM**: Grounding answers in uploaded documents reduces hallucination and makes responses relevant to course material.
2. **Local embeddings**: `all-MiniLM-L6-v2` runs on the server without an external API call, reducing latency and cost for the embedding step.
3. **DeepSeek V3 via OpenRouter**: Chosen for its strong structured JSON output, which is critical for reliable quiz and flashcard generation.
4. **FAISS for vector search**: Lightweight, no external database required, suitable for a single-server academic deployment.
5. **Spaced repetition**: Flashcard review scheduling (confidence levels + last-reviewed timestamp) improves long-term retention.
6. **Caching strategy**: In-process model cache + Django query result cache reduces response time for repeated searches and document queries.
