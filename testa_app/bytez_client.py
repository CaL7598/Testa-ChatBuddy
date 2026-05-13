"""
OpenRouter API Client for Testa studyBuddy
Replaces Bytez API with OpenRouter (OpenAI-compatible endpoint)

Model: deepseek/deepseek-chat (DeepSeek V3)
- Excellent structured JSON output for quiz/flashcard generation
- Strong educational Q&A capabilities
- Cost-effective on OpenRouter

This client provides AI capabilities for all university students across
all departments and faculties.
"""
import json
import logging
import os
import threading
import time
from typing import List, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_session_lock = threading.Lock()
_http_session: Optional[requests.Session] = None

_bytez_client_lock = threading.Lock()
_bytez_client_singleton: Optional["BytezClient"] = None


def _get_http_session() -> requests.Session:
    """Shared Session for TLS connection reuse (lower latency on repeat calls)."""
    global _http_session
    if _http_session is not None:
        return _http_session
    with _session_lock:
        if _http_session is None:
            session = requests.Session()
            adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8, max_retries=0)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            _http_session = session
        return _http_session


def get_bytez_client() -> "BytezClient":
    """Process-wide shared client (avoids rebuilding Session + headers each request)."""
    global _bytez_client_singleton
    if _bytez_client_singleton is not None:
        return _bytez_client_singleton
    with _bytez_client_lock:
        if _bytez_client_singleton is None:
            _bytez_client_singleton = BytezClient()
        return _bytez_client_singleton

# Selected model: DeepSeek V3 via OpenRouter
# - Best-in-class for structured JSON output (quizzes, flashcards)
# - Strong instruction following for educational content
# - Competitive pricing on OpenRouter
DEFAULT_MODEL = "deepseek/deepseek-chat"

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1/chat/completions"


class BytezClient:
    """Client for interacting with OpenRouter API (drop-in replacement for Bytez)"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found. Please set it in your .env file.")
        self.model = model or DEFAULT_MODEL
        self._session = _get_http_session()

    def chat(self, messages: List[Dict[str, str]], stream: bool = False, **kwargs) -> str:
        """
        Send a chat request to OpenRouter API

        Args:
            messages: List of message dicts with 'role' and 'content'
            stream: Whether to stream the response (not supported, ignored)
            **kwargs: Additional parameters (temperature, max_length, etc.)

        Returns:
            Response text from the model
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://testa-studybuddy.app",
            "X-Title": "Testa studyBuddy",
        }

        data = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_length", 2048),
        }

        # (connect, read) — scale read budget with max_tokens (study guides need more time)
        request_timeout = kwargs.pop("request_timeout", None)
        if request_timeout is None:
            mt = int(data["max_tokens"])
            read_budget = 70 if mt <= 900 else (95 if mt <= 2200 else 150)
            request_timeout = (12, read_budget)

        max_retries = 2
        retry_delay = 0.75  # seconds

        for attempt in range(max_retries):
            try:
                logger.debug(
                    "OpenRouter request model=%s attempt=%s/%s",
                    self.model,
                    attempt + 1,
                    max_retries,
                )

                response = self._session.post(
                    OPENROUTER_API_BASE,
                    headers=headers,
                    json=data,
                    timeout=request_timeout,
                )

                logger.debug("OpenRouter response status=%s", response.status_code)
                response.raise_for_status()

                result = response.json()

                if result.get("error"):
                    raise Exception(f"OpenRouter API error: {result['error']}")

                # Standard OpenAI-compatible response format
                choices = result.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    if content:
                        return content

                raise Exception(f"Unexpected response format from OpenRouter API: {result}")

            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.warning("OpenRouter timeout attempt %s, retry in %ss", attempt + 1, retry_delay)
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                raise Exception(
                    f"OpenRouter API request timed out after {max_retries} attempts. "
                    "The service may be slow or unavailable."
                )

            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    logger.warning("OpenRouter connection error attempt %s, retry in %ss", attempt + 1, retry_delay)
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                raise Exception(
                    f"Could not connect to OpenRouter API after {max_retries} attempts. "
                    "Please check your internet connection."
                )

            except requests.exceptions.HTTPError as e:
                error_detail = ""
                try:
                    error_detail = response.json().get("error", response.text[:200])
                except Exception:
                    error_detail = response.text[:200] if hasattr(response, "text") else str(e)

                if response.status_code < 500:
                    raise Exception(f"OpenRouter API error ({response.status_code}): {error_detail}")

                if attempt < max_retries - 1:
                    logger.warning(
                        "OpenRouter HTTP %s on attempt %s, retrying...",
                        response.status_code,
                        attempt + 1,
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                raise Exception(f"OpenRouter API server error ({response.status_code}): {error_detail}")

            except Exception as e:
                raise Exception(f"OpenRouter API error: {str(e)}")

        raise Exception("OpenRouter API request failed after all retry attempts")

    def generate_text(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """
        Generate text from a prompt (simpler interface)

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional parameters

        Returns:
            Generated text
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        return self.chat(messages, **kwargs)

    def answer_question(self, question: str, context: str = None, **kwargs) -> str:
        """
        Answer a question, optionally with context

        Args:
            question: The question to answer
            context: Optional context to base answer on
            **kwargs: Additional parameters

        Returns:
            Answer text
        """
        system_prompt = """You are an educational AI assistant for university students across all departments and faculties.
Answer questions clearly and accurately. If context is provided, base your answer on it.
If the answer is not in the context, use your knowledge but indicate uncertainty.
Provide helpful explanations suitable for students from any academic discipline.
When you include tables, use GitHub-flavored markdown pipe tables only: a header row, a separator row with dashes (e.g. | --- | --- |), then body rows — do not use ASCII box-drawing or dash-only grids without pipes."""

        if context:
            prompt = f"""Context:
{context}

Question:
{question}

Provide a clear, educational answer with examples where appropriate."""
        else:
            prompt = f"Question: {question}\n\nProvide a clear, educational answer."

        return self.generate_text(
            prompt,
            system_prompt=system_prompt,
            temperature=kwargs.get("temperature", 0.3),
            # Shorter cap speeds up Q&A vs long essays; override for study guides etc.
            max_length=kwargs.get("max_length", 768),
            **{k: v for k, v in kwargs.items() if k not in ("temperature", "max_length")}
        )


# ============================================================
# BYTEZ API CLIENT (commented out — replaced by OpenRouter)
# ============================================================
# DEFAULT_MODEL_BYTEZ = "Qwen/Qwen3-4B"
# BYTEZ_API_BASE = "https://api.bytez.com/models/v2"
#
# class BytezClientLegacy:
#     """Original Bytez API client — kept for reference"""
#
#     def __init__(self, api_key=None, model=None):
#         self.api_key = api_key or os.getenv("BYTEZ_API_KEY")
#         if not self.api_key:
#             raise ValueError("BYTEZ_API_KEY not found.")
#         self.model = model or DEFAULT_MODEL_BYTEZ
#         self.base_url = f"{BYTEZ_API_BASE}/{self.model}"
#
#     def chat(self, messages, stream=False, **kwargs):
#         headers = {
#             "Authorization": self.api_key,
#             "Content-Type": "application/json"
#         }
#         data = {
#             "messages": messages,
#             "stream": stream,
#             "params": {
#                 "temperature": kwargs.get("temperature", 0.7),
#                 "max_length": kwargs.get("max_length", 2048),
#                 "min_length": kwargs.get("min_length", 10),
#                 **kwargs.get("extra_params", {})
#             }
#         }
#         response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
#         response.raise_for_status()
#         result = response.json()
#         if result.get("output"):
#             if isinstance(result["output"], dict):
#                 return result["output"].get("content") or result["output"].get("text", "")
#             return result["output"]
#         if result.get("content"):
#             return result["content"]
#         raise Exception(f"Unexpected Bytez response format: {result}")


# For embeddings, we'll use sentence-transformers (free, local)
class EmbeddingClient:
    """Client for text embeddings - using sentence-transformers"""

    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
            # Using a free, lightweight embedding model (384 dimensions)
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.use_local = True
        except ImportError:
            self.use_local = False
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if self.use_local:
            return self.model.encode(
                text, convert_to_numpy=True, show_progress_bar=False
            ).tolist()
        raise RuntimeError("Embedding model not initialized")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (batch)"""
        if self.use_local:
            return self.model.encode(
                texts, convert_to_numpy=True, show_progress_bar=False
            ).tolist()
        raise RuntimeError("Embedding model not initialized")
