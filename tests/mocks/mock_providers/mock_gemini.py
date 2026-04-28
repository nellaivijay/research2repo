"""
Mock Gemini provider for testing
Simulates Gemini provider behavior without making actual API calls
"""

from typing import List, Optional, Dict, Any
import time


class MockGeminiProvider:
    """Mock Gemini provider for testing."""
    
    def __init__(self, model_name: str = "gemini-1.5-pro"):
        """
        Initialize the mock Gemini provider.
        
        Args:
            model_name: Name of the model to simulate
        """
        self.model_name = model_name
        self.call_count = 0
        self.call_history = []
        self.responses = []
        self.latency = 0.1  # Simulated latency in seconds
    
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
            return "Mock response for general query"
    
    def _mock_analysis_response(self) -> str:
        """Mock paper analysis response."""
        return """
{
  "title": "Attention Is All You Need",
  "authors": ["Vaswani et al."],
  "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
  "sections": ["Introduction", "Background", "Model Architecture", "Training", "Results", "Conclusion"],
  "equations": [
    "Attention(Q,K,V) = softmax(QK^T / sqrt(d_k))V",
    "FFN(x) = max(0, xW_1 + b_1)W_2 + b_2"
  ],
  "hyperparameters": {
    "d_model": 512,
    "d_ff": 2048,
    "heads": 8,
    "layers": 6,
    "dropout": 0.1
  }
}
"""
    
    def _mock_architecture_response(self) -> str:
        """Mock architecture design response."""
        return """
{
  "repo_name": "attention-transformer",
  "description": "Implementation of Attention Is All You Need",
  "files": [
    "src/model.py",
    "src/data.py", 
    "src/train.py",
    "config.yaml",
    "requirements.txt",
    "README.md"
  ],
  "dependencies": ["torch", "numpy", "pandas"],
  "structure": {
    "src": ["model.py", "data.py", "train.py"],
    "tests": ["test_model.py"],
    "config": ["config.yaml"]
  }
}
"""
    
    def _mock_code_response(self) -> str:
        """Mock code generation response."""
        return """
import torch
import torch.nn as nn

class AttentionModel(nn.Module):
    def __init__(self, d_model=512, nhead=8):
        super().__init__()
        self.attention = nn.MultiheadAttention(d_model, nhead)
        self.feed_forward = nn.Sequential(
            nn.Linear(d_model, 2048),
            nn.ReLU(),
            nn.Linear(2048, d_model)
        )
    
    def forward(self, x):
        attn_output, _ = self.attention(x, x, x)
        output = self.feed_forward(attn_output)
        return output
"""
    
    def _mock_test_response(self) -> str:
        """Mock test generation response."""
        return """
import pytest
import torch
from src.model import AttentionModel

def test_attention_model():
    model = AttentionModel(d_model=512, nhead=8)
    x = torch.randn(10, 32, 512)  # seq_len, batch, d_model
    output = model(x)
    assert output.shape == x.shape
    
def test_model_parameters():
    model = AttentionModel(d_model=512, nhead=8)
    assert sum(p.numel() for p in model.parameters()) > 0
"""
    
    def _mock_validation_response(self) -> str:
        """Mock validation response."""
        return """
{
  "score": 92,
  "equation_coverage": 95,
  "hyperparam_coverage": 88,
  "critical_issues": [],
  "warnings": [
    {
      "file": "src/model.py",
      "line": 10,
      "message": "Consider adding dropout for regularization"
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