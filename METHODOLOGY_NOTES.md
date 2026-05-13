# Methodology Notes — UENR Testa StudyBuddy

Key technical details for writing the methodology section of the project documentation.

---

## 1. System Architecture

- **Framework**: Django 5.0.3 using the MVT (Model-View-Template) architectural pattern
- **Database**: SQLite via Django ORM (development); optimised with database indexes on `user`, `created_at`, `course`, `topic`, and `upvotes` fields
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

## 4. Large Language Model (LLM) Integration

- **Provider**: OpenRouter API (OpenAI-compatible endpoint)
- **Model**: DeepSeek V3 (`deepseek/deepseek-chat`)
  - Selected for strong structured JSON output (required for quiz/flashcard generation)
  - Strong instruction-following for educational content
  - Cost-effective for the project scale
- **Client**: Custom `BytezClient` class wrapping `requests.post` to the OpenRouter endpoint
- **Retry logic**: Up to 2 retries with exponential backoff (1s → 2s) on timeout or server errors
- **Temperature settings**:
  - Q&A answering: 0.3 (more factual)
  - Quiz/flashcard generation: 0.7 (more varied)
  - Summaries/study guides: 0.3 (more structured)
- **Token limit**: 2,048 tokens (standard); 4,096 tokens for study guides

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
