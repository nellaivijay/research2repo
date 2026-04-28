"""HuggingFace provider implementation."""

from architecture.base.base_provider import BaseProvider
from architecture.core.registry import register_provider
from typing import Optional
import os


@register_provider("huggingface")
class HuggingFaceProvider(BaseProvider):
    """
    HuggingFace LLM provider.
    
    Args:
        api_key: HuggingFace API key (or use HUGGINGFACE_API_KEY env var)
        model: Model identifier (default: "meta-llama/Llama-2-7b-chat-hf")
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "meta-llama/Llama-2-7b-chat-hf",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 120,
        **kwargs
    ):
        super().__init__(api_key, model, temperature, max_tokens, timeout, **kwargs)
        self.api_key = api_key or os.getenv("HUGGINGFACE_API_KEY")
        if not self.api_key:
            raise ValueError("HUGGINGFACE_API_KEY environment variable must be set")

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using HuggingFace Inference API."""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            
            # For demonstration, use a simple approach
            # In production, you would use the HuggingFace Inference API
            tokenizer = AutoTokenizer.from_pretrained(self.model)
            model = AutoModelForCausalLM.from_pretrained(self.model)
            
            inputs = tokenizer(prompt, return_tensors="pt")
            outputs = model.generate(
                **inputs,
                max_new_tokens=self.max_tokens,
                temperature=self.temperature,
                do_sample=True
            )
            
            result = tokenizer.decode(outputs[0], skip_special_tokens=True)
            return result
            
        except ImportError:
            # Fallback to API call if transformers not available
            import requests
            
            API_URL = f"https://api-inference.huggingface.co/models/{self.model}"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            response = requests.post(
                API_URL,
                headers=headers,
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": self.max_tokens,
                        "temperature": self.temperature
                    }
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if isinstance(result, list):
                return result[0].get("generated_text", "")
            return result.get("generated_text", "")

    def generate_stream(self, prompt: str, **kwargs):
        """Generate text with streaming using HuggingFace API."""
        import requests
        
        API_URL = f"https://api-inference.huggingface.co/models/{self.model}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        response = requests.post(
            API_URL,
            headers=headers,
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": self.max_tokens,
                    "temperature": self.temperature
                },
                "stream": True
            },
            timeout=self.timeout,
            stream=True
        )
        
        for chunk in response.iter_lines():
            if chunk:
                yield chunk.decode()
