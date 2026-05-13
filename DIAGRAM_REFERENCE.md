# Diagram reference — UENR Testa StudyBuddy

Structured material for **use case**, **system architecture**, and **data flow** diagrams. Sourced from `testa_app/urls.py`, `testa_app/models.py`, `testa_project/settings.py`, and `METHODOLOGY_NOTES.md`.

---

## 1. Use case diagram

### Actors

| Actor | Notes |
|--------|--------|
| **Student (authenticated user)** | Primary user; study features use `@login_required` where applicable. |
| **Guest** | Public pages (e.g. index, about, register/login). |
| **Administrator** | Django admin at `/admin/`. |
| **OpenRouter API** | LLM provider for chat, quizzes, flashcards, summaries, study guides (`BytezClient`). |
| **External web (optional)** | Fallback: HTTP fetch + BeautifulSoup when document context is missing. |

Optional: omit **Sentence Transformers + FAISS** as actors; show as internal «system» components on architecture diagrams instead.

### Use cases by feature area

**Authentication & account**

- Register, log in, log out
- Forgot password / reset password (Django reset views)

**Documents & Q&A**

- View home / about
- Upload document (`pdf_upload`, AJAX upload)
- Ask question / view Q&A (`question_answer`)
- Vote on Q&A
- Delete Q&A (single or all)
- List all questions

**Analytics**

- View analytics dashboard
- Load chart data (`analytics/chart-data/`)

**Study assistant**

- Generate quiz → take quiz → view results
- Generate flashcards → study flashcards → update confidence
- Generate summary
- Generate study guide (per document)

**Search & bookmarks**

- Advanced search, search suggestions
- Save search, list saved searches, load saved search
- Search history, clear history, export search results
- Bookmarks (create, favorite, delete), folders, export bookmarks

**Recommendations & profile**

- View recommendations, complete recommendation
- View profile

**UML hints**

- **«include»**: e.g. “Ask question” includes “Retrieve chunks from FAISS” and “Call LLM with context.”
- **«extend»**: e.g. “Fallback web search” extends “Answer question” when no document context exists.

---

## 2. System architecture

### Layers (MVT)

| Layer | Responsibility |
|--------|----------------|
| **Presentation** | Django templates, Tailwind CSS, vanilla JavaScript |
| **Application** | `views.py`, `analytics_views.py`, `study_assistant_views.py`, `search_views.py`; routing `testa_project/urls.py` → `testa_app/urls.py` |
| **Domain / data** | Django ORM — `testa_app/models.py` |
| **Infrastructure** | `utils.py` (RAG, chunking, FAISS), `bytez_client.py` (OpenRouter), `search_engine.py`, `recommendation_engine.py`; uploaded files (`PDFDocument` → `pdfs/`) |

### Logical components (boxes)

1. **Django web application** — HTTP, sessions, CSRF, authentication  
2. **SQLite** (`db.sqlite3`) — persistent entities  
3. **File storage** — uploaded study documents  
4. **FAISS vector index** (`faiss_index/`) — on-disk index, merged on new uploads  
5. **Local embeddings** — Sentence Transformers `all-MiniLM-L6-v2` (384 dimensions), in-process  
6. **LLM gateway** — HTTPS to **OpenRouter** (`deepseek/deepseek-chat`)  
7. **Optional web fallback** — HTTP + BeautifulSoup  
8. **Django cache** — search result caching (e.g. 5-minute TTL per methodology notes)

### Technology annotations

- Django **5.0.3**, WSGI  
- **LangChain ecosystem**: `RecursiveCharacterTextSplitter`; `langchain_community` FAISS; `langchain_core` prompts  
- **PyPDF2**, **python-docx**, **python-pptx**  
- **FAISS**, **sentence-transformers**  
- **OpenRouter** + DeepSeek V3  

### Security (small subsystem)

- Session-based auth, `@login_required`, `CsrfViewMiddleware`  
- Environment variables via **python-dotenv** (e.g. `OPENROUTER_API_KEY`; `OPENAI_API_KEY` appears in `settings.py` if used)

---

## 3. Data flow diagram — main flows

### A. Document upload → index (ingestion)

1. User uploads file (PDF / DOCX / PPTX / TXT).  
2. **Extract text** (PyPDF2 / python-docx / python-pptx / UTF-8 read).  
3. **Chunk** with `RecursiveCharacterTextSplitter` (methodology: ~50,000 chars, ~1,000 overlap).  
4. **Embed** chunks locally (`all-MiniLM-L6-v2`).  
5. **Merge** vectors into **FAISS** on disk; persist **`PDFDocument`** (and user/course metadata) in **SQLite**.

### B. Question answering (RAG)

1. User submits question.  
2. **Embed query** → **FAISS** similarity (cosine) → retrieve top chunks.  
3. Build prompt (question + context) → **OpenRouter** → natural language answer.  
4. Store **`QuestionAnswer`**; update votes/tags/analytics as implemented.  
5. **Fallback** (if weak/no context): web search + scrape → supplement LLM.

### C. Quiz / flashcards / summary / study guide

1. User selects scope (e.g. document).  
2. Load text/chunks from storage or linked document.  
3. **LLM** with structured JSON prompt (methodology: higher temperature for quiz/flashcards, lower for summaries).  
4. Parse JSON → persist **`Quiz`** / **`QuizQuestion`**, **`Flashcard`**, or return summary/study-guide content.

### D. Advanced search (keyword, not vector)

1. Query + filters → **Django ORM** on **`QuestionAnswer`** (`icontains` on question, answer, course, topic; additional filters per `AdvancedSearchEngine`).  
2. Rank, paginate → optional **cache** write.  
3. Record **`SearchHistory`** / **`RecentSearch`**.

### E. Recommendations

1. **`RecommendationEngine`** reads **`TopicMastery`**, **`QuestionAnswer`**, **`Quiz`**, **`QuizAttempt`**, **`Flashcard`**, **`PDFDocument`**, **`UserAnalytics`**.  
2. Produce prioritized suggestions → persist **`Recommendation`** (types: weak area, quiz, flashcard, document, topic, etc.).

### F. Analytics

- Read/write **`UserAnalytics`**, **`DailyActivity`**, **`TopicMastery`**, **`StudySession`** driven by user activity (Q&A, quizzes, flashcards).

---

## 4. Entity summary (ER / data store labels)

| Model / group | Role |
|---------------|------|
| `PDFDocument` | Uploaded materials |
| `QuestionAnswer`, `Vote`, `Tag` | Q&A core + engagement |
| `Quiz`, `QuizQuestion`, `QuizAttempt` | Quiz lifecycle |
| `Flashcard` | Spaced-repetition cards |
| `Bookmark`, `BookmarkFolder` | Saved Q&A organization |
| `SearchHistory`, `SavedSearch`, `RecentSearch` | Search tracking |
| `Recommendation` | Personalized suggestions |
| `UserAnalytics`, `DailyActivity`, `TopicMastery`, `StudySession` | Learning analytics |
| `ExportHistory` | Export audit trail |

**Key FKs (for relationship arrows):** `QuestionAnswer` → `PDFDocument` (`source_document`); `Bookmark` → `QuestionAnswer`; `Quiz` → `PDFDocument`; all major entities → `User`.

---

## 5. Cross-reference

Detailed methodology prose (temperatures, token limits, retry behavior) lives in **`METHODOLOGY_NOTES.md`**. Use this file for diagram inventory; use methodology notes for report text.
