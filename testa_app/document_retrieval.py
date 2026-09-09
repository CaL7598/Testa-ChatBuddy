"""
Document retrieval for question answering — works without the ML stack.

The FAISS/embeddings path (see ``_ml_enabled`` in utils.py) is switched off in
production: render.yaml sets ``DISABLE_ML=1`` and requirements-render.txt ships
neither faiss-cpu nor langchain. That meant uploads were never indexed and every
question reached the model with an empty context, so answers came back as
"I don't have access to the content of <file>".

This module retrieves passages from text stored on ``PDFDocument.content_text``
using pure-Python keyword scoring, so document questions work on Render and
locally alike. Storing the text in the database also survives Render's ephemeral
disk, which drops uploaded files on every restart.
"""
import math
import re
from collections import Counter

from django.db.models import Q

_WORD_RE = re.compile(r"[a-z0-9]+")

# Words too common to help rank a passage.
_STOPWORDS = {
    'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'any', 'can', 'has',
    'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'his', 'how', 'its',
    'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'use', 'man',
    'from', 'this', 'that', 'with', 'have', 'they', 'been', 'were', 'what',
    'when', 'your', 'said', 'each', 'she', 'them', 'then', 'than', 'into',
    'some', 'very', 'more', 'most', 'over', 'such', 'also', 'about', 'would',
    'there', 'their', 'which', 'these', 'those', 'other', 'could', 'should',
    'please', 'give', 'tell', 'show', 'make', 'need', 'want', 'like', 'know',
    'does', 'doing', 'here', 'much', 'many', 'will', 'shall', 'may', 'might',
}

# Question phrasings that call for broad coverage of a document rather than a
# few keyword-matched passages.
_SUMMARY_PATTERNS = (
    'summary', 'summarise', 'summarize', 'summarizing', 'overview',
    'key idea', 'key point', 'key concept', 'main idea', 'main point',
    'what is this', 'what is it about', 'what does this cover', 'brief me',
    'go through', 'walk me through', 'explain this', 'explain the',
    'outline', 'takeaway', 'highlight',
)

# Phrases that refer to an upload without naming it.
_DEICTIC_PATTERNS = (
    'this slide', 'these slides', 'the slide', 'the slides',
    'this document', 'the document', 'this file', 'the file',
    'this material', 'the material', 'this reading', 'the reading',
    'this lecture', 'the lecture', 'this note', 'these notes', 'the notes',
    'this pdf', 'the pdf', 'this chapter', 'the chapter', 'my upload',
    'i uploaded', 'i just uploaded', 'the upload', 'attached',
)

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150
MAX_DOCUMENTS = 12


def _normalize(text):
    """Lowercase and collapse everything non-alphanumeric to single spaces."""
    return re.sub(r'[^a-z0-9]+', ' ', (text or '').lower()).strip()


def _tokenize(text):
    return [t for t in _WORD_RE.findall((text or '').lower())
            if len(t) > 2 and t not in _STOPWORDS]


def _chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into paragraph-aware chunks small enough to rank meaningfully.

    utils.get_text_chunks uses 50,000-character chunks, which is far too coarse
    to tell one passage from another; these are sized for retrieval.
    """
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r'\n\s*\n|\n', text) if p.strip()]
    chunks = []
    current = ''

    for para in paragraphs:
        # A single oversized paragraph gets hard-split.
        while len(para) > size:
            if current:
                chunks.append(current)
                current = ''
            chunks.append(para[:size])
            para = para[size - overlap:]
        if not current:
            current = para
        elif len(current) + len(para) + 1 <= size:
            current += '\n' + para
        else:
            chunks.append(current)
            current = para

    if current:
        chunks.append(current)
    return chunks


def extract_document_text(file):
    """Extract text from an uploaded file object, rewinding it first."""
    from .utils import get_file_text

    try:
        file.seek(0)
    except (AttributeError, ValueError, OSError):
        pass
    text = get_file_text(file) or ''
    try:
        file.seek(0)
    except (AttributeError, ValueError, OSError):
        pass
    return text


def store_document_text(pdf_doc, file=None, save=True):
    """Extract and persist a document's text so it can be searched later.

    Returns the extracted text, or '' when extraction is not possible.
    """
    text = ''
    try:
        text = extract_document_text(file if file is not None else pdf_doc.file)
    except Exception as exc:  # unreadable/corrupt file must not break upload
        print(f"Could not extract text from document {pdf_doc.pk}: {exc}")
        return ''

    text = (text or '').strip()
    if text and save and pdf_doc.pk:
        pdf_doc.content_text = text
        pdf_doc.save(update_fields=['content_text'])
    elif text:
        pdf_doc.content_text = text
    return text


def get_document_text(pdf_doc):
    """Return a document's text, extracting and caching it on first use."""
    if pdf_doc.content_text:
        return pdf_doc.content_text
    return store_document_text(pdf_doc)


def _document_label(pdf_doc):
    if pdf_doc.title:
        return pdf_doc.title
    try:
        name = pdf_doc.file.name or ''
    except Exception:
        name = ''
    return name.rsplit('/', 1)[-1] or f'Document {pdf_doc.pk}'


def _document_aliases(pdf_doc):
    """Names a student might use for this document, normalized for matching."""
    aliases = set()
    for raw in (pdf_doc.title, getattr(pdf_doc.file, 'name', '') or ''):
        if not raw:
            continue
        base = raw.rsplit('/', 1)[-1]
        aliases.add(_normalize(base))
        stem = base.rsplit('.', 1)[0]
        aliases.add(_normalize(stem))
        # Django appends a random suffix on filename collisions
        # (UNIT_3_y15Lnk6.pptx); match the original name too.
        aliases.add(_normalize(re.sub(r'_[A-Za-z0-9]{7}$', '', stem)))
    return {a for a in aliases if len(a) >= 3}


def _mentioned_documents(question, documents):
    """Documents whose name the question refers to, best match first."""
    norm_q = _normalize(question)
    padded_q = f' {norm_q} '
    matches = []

    for doc in documents:
        best = 0
        for alias in _document_aliases(doc):
            if f' {alias} ' in padded_q:
                best = max(best, len(alias))
            else:
                # Every significant word of the name appears in the question.
                parts = [p for p in alias.split() if len(p) > 1]
                if parts and all(f' {p} ' in padded_q for p in parts):
                    best = max(best, len(alias) - 1)
        if best:
            matches.append((best, doc))

    matches.sort(key=lambda pair: pair[0], reverse=True)
    return [doc for _, doc in matches]


def _wants_summary(question):
    norm = (question or '').lower()
    return any(pattern in norm for pattern in _SUMMARY_PATTERNS)


def _refers_to_upload(question):
    norm = (question or '').lower()
    return any(pattern in norm for pattern in _DEICTIC_PATTERNS)


def _rank_chunks(question, entries, top_k):
    """Rank (document, chunk) pairs against the question with TF-IDF scoring."""
    query_terms = set(_tokenize(question))
    if not query_terms or not entries:
        return []

    doc_freq = Counter()
    prepared = []
    for doc, chunk in entries:
        counts = Counter(_tokenize(chunk))
        prepared.append((doc, chunk, counts))
        for term in counts:
            if term in query_terms:
                doc_freq[term] += 1

    total = len(prepared)
    scored = []
    for doc, chunk, counts in prepared:
        score = 0.0
        for term in query_terms:
            tf = counts.get(term, 0)
            if not tf:
                continue
            idf = math.log((total + 1) / (doc_freq[term] + 0.5)) + 1.0
            score += idf * (1.0 + math.log(tf))
        if score > 0:
            # Damp long chunks so they do not win on length alone.
            length = sum(counts.values()) or 1
            scored.append((score / math.sqrt(length), doc, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [(doc, chunk) for _, doc, chunk in scored[:top_k]]


def _assemble(selected, max_chars):
    """Join selected passages into a context block labelled by source."""
    parts = []
    sources = []
    used = 0

    for doc, chunk in selected:
        label = _document_label(doc)
        if label not in sources:
            sources.append(label)
        block = f'[From: {label}]\n{chunk}'
        if used + len(block) > max_chars:
            remaining = max_chars - used
            if remaining > 400:
                parts.append(block[:remaining])
            break
        parts.append(block)
        used += len(block) + 2

    return '\n\n'.join(parts).strip(), sources


def retrieve_context(user, question, max_chars=None):
    """Find passages from the user's uploaded documents relevant to a question.

    Returns ``(context, sources)`` where sources is a list of document titles.
    """
    from .utils import _RAG_CONTEXT_CHAR_LIMIT
    from .models import PDFDocument

    if max_chars is None:
        max_chars = _RAG_CONTEXT_CHAR_LIMIT
    if not question or user is None or not getattr(user, 'is_authenticated', False):
        return '', []

    # The user's own uploads plus any unowned (seeded/shared) material.
    documents = list(
        PDFDocument.objects
        .filter(Q(uploaded_by=user) | Q(uploaded_by__isnull=True))
        .order_by('-uploaded_at')[:MAX_DOCUMENTS]
    )
    if not documents:
        return '', []

    named = _mentioned_documents(question, documents)
    candidates = named or documents

    texts = []
    for doc in candidates:
        text = get_document_text(doc)
        if text:
            texts.append((doc, text))
    if not texts:
        return '', []

    # A summary request needs the top of the document, not scattered keyword
    # hits — and when only one document is in play, it is unambiguous.
    target = None
    if named:
        target = texts[0]
    elif len(texts) == 1 and (_wants_summary(question) or _refers_to_upload(question)):
        target = texts[0]
    elif _refers_to_upload(question):
        target = texts[0]  # most recent upload

    if target is not None and _wants_summary(question):
        doc, text = target
        selected = [(doc, chunk) for chunk in _chunk_text(text)]
        return _assemble(selected, max_chars)

    search_space = [target] if target is not None else texts
    entries = []
    for doc, text in search_space:
        for chunk in _chunk_text(text):
            entries.append((doc, chunk))

    selected = _rank_chunks(question, entries, top_k=8)

    # Keyword search found nothing, but the student is clearly asking about an
    # upload — fall back to the opening of the relevant document.
    if not selected and target is not None:
        doc, text = target
        selected = [(doc, chunk) for chunk in _chunk_text(text)[:6]]

    return _assemble(selected, max_chars)
