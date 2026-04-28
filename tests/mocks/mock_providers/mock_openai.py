"""
Mock OpenAI provider for testing
Simulates OpenAI provider behavior without making actual API calls
"""

from typing import List, Optional, Dict, Any
import time


class MockOpenAIProvider:
    """Mock OpenAI provider for testing."""
    
    def __init__(self, model_name: str = "gpt-4o"):
        """
        Initialize the mock OpenAI provider.
        
        Args:
            model_name: Name of the model to simulate
        """
        self.model_name = model_name
        self.call_count = 0
        self.call_history = []
        self.responses = []
        self.latency = 0.15  # Simulated latency in seconds
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Simulate a generate call.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional parameters
            
        Returns:
            Mock response based on prompt type
        """
        self.call_count += 1
        self.call_history.append({"prompt": prompt, "kwargs": kwargs})
        
        # Simulate latency
        time.sleep(self.latency)
        
        # Return mock response based on prompt type
        return self._get_mock_response(prompt, **kwargs)
    
    def _get_mock_response(self, prompt: str, **kwargs) -> str:
        """Get mock response based on prompt type."""
        prompt_lower = prompt.lower()
        
        if "analyze" in prompt_lower or "paper" in prompt_lower:
            return self._mock_analysis_response()
        elif "architecture" in prompt_lower or "design" in prompt_lower:
            return self._mock_architecture_response()
        elif "code" in prompt_lower or "implement" in prompt_lower:
            return self._mock_code_response()
        elif "test" in prompt_lower:
            return self._mock_test_response()
        elif "validate" in prompt_lower:
            return self._mock_validation_response()
        else:
            return "Mock OpenAI response for general query"
    
    def _mock_analysis_response(self) -> str:
        """Mock paper analysis response."""
        return """
{
  "title": "BERT: Pre-training of Deep Bidirectional Transformers",
  "authors": ["Devlin et al."],
  "abstract": "We introduce a new language representation model called BERT...",
  "sections": ["Introduction", "Method", "Experiments", "Results", "Conclusion"],
  "equations": [
    "Loss = -sum(log P(w_t | context))"
  ],
  "hyperparameters": {
    "hidden_size": 768,
    "num_layers": 12,
    "num_heads": 12,
    "learning_rate": 0.0001
  }
}
"""
    
    def _mock_architecture_response(self) -> str:
        """Mock architecture design response."""
        return """
{
  "repo_name": "bert-implementation",
  "description": "BERT implementation for NLP tasks",
  "files": [
    "src/modeling.py",
    "src/tokenization.py",
    "src/training.py",
    "config.json",
    "requirements.txt"
  ],
  "dependencies": ["torch", "transformers", "tokenizers"],
  "structure": {
    "src": ["modeling.py", "tokenization.py", "training.py"],
    "tests": ["test_modeling.py"],
    "configs": ["config.json"]
  }
}
"""
    
    def _mock_code_response(self) -> str:
        """Mock code generation response."""
        return """
import torch
import torch.nn as nn

class BERT(nn.Module):
    def __init__(self, vocab_size, hidden_size=768, num_layers=12):
        super().__init__()
        self.embeddings = nn.Embedding(vocab_size, hidden_size)
        self.encoder = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(hidden_size, 12),
            num_layers
        )
    
    def forward(self, input_ids, attention_mask=None):
        embeddings = self.embeddings(input_ids)
        encoded = self.encoder(embeddings)
        return encoded
"""
    
    def _mock_test_response(self) -> str:
        """Mock test generation response."""
        return """
import pytest
import torch
from src.modeling import BERT

def test_bert_forward():
    model = BERT(vocab_size=30000, hidden_size=768)
    input_ids = torch.randint(0, 30000, (32, 128))
    output = model(input_ids)
    assert output.shape == (32, 128, 768)
"""
    
    def _mock_validation_response(self) -> str:
        """Mock validation response."""
        return """
{
  "score": 90,
  "equation_coverage": 85,
  "hyperparam_coverage": 90,
  "critical_issues": [],
  "warnings": [
    {
      "file": "src/modeling.py",
      "line": 15,
      "message": "Consider adding position embeddings"
    }
  ]
}
"""
    
    def reset(self):
        """Reset the mock provider state."""
        self.call_count = 0
        self.call_history = []
        self.responses = []
    
    def get_call_count(self) -> int:
        """Get the number of calls made to this provider."""
        return self.call_count
    
    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get the history of calls made to this provider."""
        return self.call_history