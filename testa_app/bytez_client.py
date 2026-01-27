"""
Bytez API Client for Testa ChatBuddy
Replaces Google Gemini API with free open-source models via Bytez

This client provides AI capabilities for all university students across
all departments and faculties.
"""
import os
import json
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Default model - can be changed in settings
# Bytez API endpoint format: https://api.bytez.com/models/v2/{owner}/{model}
# Try different model formats if one doesn't work
DEFAULT_MODEL = "Qwen/Qwen3-4B"  # Using the example from Bytez docs
# Alternative models to try:
# "Qwen/Qwen2.5-7B-Instruct"
# "Meta-Llama/Llama-3.1-8B-Instruct"
# "mistralai/Mistral-7B-Instruct-v0.2"

BYTEZ_API_BASE = "https://api.bytez.com/models/v2"


class BytezClient:
    """Client for interacting with Bytez API"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("BYTEZ_API_KEY")
        if not self.api_key:
            raise ValueError("BYTEZ_API_KEY not found. Please set it in your .env file.")
        self.model = model or DEFAULT_MODEL
        self.base_url = f"{BYTEZ_API_BASE}/{self.model}"
    
    def chat(self, messages: List[Dict[str, str]], stream: bool = False, **kwargs) -> str:
        """
        Send a chat request to Bytez API
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            stream: Whether to stream the response
            **kwargs: Additional parameters (temperature, max_length, etc.)
        
        Returns:
            Response text from the model
        """
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Bytez API format based on documentation
        data = {
            "messages": messages,
            "stream": stream,
            "params": {
                "temperature": kwargs.get("temperature", 0.7),
                "max_length": kwargs.get("max_length", 2048),
                "min_length": kwargs.get("min_length", 10),
                **kwargs.get("extra_params", {})
            }
        }
        
        # Retry logic with exponential backoff
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                print(f"Calling Bytez API (attempt {attempt + 1}/{max_retries}): {self.base_url}")
                print(f"Model: {self.model}")
                
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=data,
                    timeout=30  # Reduced timeout for faster failure
                )
                
                print(f"Response status: {response.status_code}")
                
                response.raise_for_status()
                
                result = response.json()
                print(f"Response received successfully")
                
                if result.get("error"):
                    error_msg = result.get("error", "Unknown error")
                    # Don't retry on API errors, only on network/timeout errors
                    raise Exception(f"Bytez API error: {error_msg}")
                
                # Check for output in response
                if result.get("output"):
                    if isinstance(result["output"], dict):
                        if result["output"].get("content"):
                            return result["output"]["content"]
                        elif result["output"].get("text"):
                            return result["output"]["text"]
                    elif isinstance(result["output"], str):
                        return result["output"]
                
                # Fallback: check for direct content field
                if result.get("content"):
                    return result["content"]
                
                # If we get here, the response format is unexpected
                raise Exception(f"Unexpected response format from Bytez API: {result}")
                    
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    print(f"Timeout on attempt {attempt + 1}, retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    raise Exception(f"Bytez API request timed out after {max_retries} attempts. The service may be slow or unavailable.")
                    
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    print(f"Connection error on attempt {attempt + 1}, retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise Exception(f"Could not connect to Bytez API after {max_retries} attempts. Please check your internet connection.")
                    
            except requests.exceptions.HTTPError as e:
                error_detail = ""
                try:
                    error_detail = response.json().get("error", response.text[:200])
                except:
                    error_detail = response.text[:200] if hasattr(response, 'text') else str(e)
                
                # Don't retry on 4xx errors (client errors)
                if response.status_code < 500:
                    raise Exception(f"Bytez API error ({response.status_code}): {error_detail}")
                
                # Retry on 5xx errors (server errors)
                if attempt < max_retries - 1:
                    print(f"Server error {response.status_code} on attempt {attempt + 1}, retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise Exception(f"Bytez API server error ({response.status_code}): {error_detail}")
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"Request error on attempt {attempt + 1}, retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise Exception(f"Bytez API request failed: {str(e)}")
                    
            except Exception as e:
                # Don't retry on other exceptions
                raise Exception(f"Bytez API error: {str(e)}")
        
        # Should never reach here, but just in case
        raise Exception("Bytez API request failed after all retry attempts")
    
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
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
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
Provide helpful explanations suitable for students from any academic discipline."""
        
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
            **kwargs
        )


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
            return self.model.encode(text, convert_to_numpy=True).tolist()
        else:
            raise RuntimeError("Embedding model not initialized")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (batch)"""
        if self.use_local:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        else:
            raise RuntimeError("Embedding model not initialized")
