"""
Bytez API Client for Testa ChatBuddy
Replaces Google Gemini API with free open-source models via Bytez
"""
import os
import json
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Default model - can be changed in settings
DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"  # Good balance of quality and speed
# Alternative models: "Qwen/Qwen3-4B", "Meta-Llama/Llama-3.1-8B-Instruct", "mistralai/Mistral-7B-Instruct-v0.2"

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
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("error"):
                raise Exception(f"Bytez API error: {result['error']}")
            
            if result.get("output") and result["output"].get("content"):
                return result["output"]["content"]
            else:
                raise Exception("Unexpected response format from Bytez API")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Bytez API request failed: {str(e)}")
    
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
        system_prompt = """You are an educational AI assistant for Computer and Electrical Engineering students.
Answer questions clearly and accurately. If context is provided, base your answer on it.
If the answer is not in the context, use your knowledge but indicate uncertainty."""
        
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
