"""
Mock Anthropic provider for testing
Simulates Anthropic provider behavior without making actual API calls
"""

from typing import List, Optional, Dict, Any
import time


class MockAnthropicProvider:
    """Mock Anthropic provider for testing."""
    
    def __init__(self, model_name: str = "claude-3-5-sonnet"):
        """
        Initialize the mock Anthropic provider.
        
        Args:
            model_name: Name of the model to simulate
        """
        self.model_name = model_name
        self.call_count = 0
        self.call_history = []
        self.responses = []
        self.latency = 0.12  # Simulated latency in seconds
    
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
            return "Mock Claude response for general query"
    
    def _mock_analysis_response(self) -> str:
        """Mock paper analysis response."""
        return """
{
  "title": "ResNet: Deep Residual Learning for Image Recognition",
  "authors": ["He et al."],
  "abstract": "We present a residual learning framework to ease the training of deeper neural networks...",
  "sections": ["Introduction", "Related Work", "Method", "Experiments", "Results"],
  "equations": [
    "y = F(x, {W_i}) + x"
  ],
  "hyperparameters": {
    "layers": 50,
    "learning_rate": 0.01,
    "momentum": 0.9
  }
}
"""
    
    def _mock_architecture_response(self) -> str:
        """Mock architecture design response."""
        return """
{
  "repo_name": "resnet-implementation",
  "description": "ResNet implementation for image classification",
  "files": [
    "src/resnet.py",
    "src/training.py",
    "src/data.py",
    "config.yaml",
    "requirements.txt"
  ],
  "dependencies": ["torch", "torchvision", "pillow"],
  "structure": {
    "src": ["resnet.py", "training.py", "data.py"],
    "tests": ["test_resnet.py"],
    "configs": ["config.yaml"]
  }
}
"""
    
    def _mock_code_response(self) -> str:
        """Mock code generation response."""
        return """
import torch
import torch.nn as nn

class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, 3, stride, 1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, 3, 1, 1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 1, stride, bias=False),
                nn.BatchNorm2d(out_channels)
            )
    
    def forward(self, x):
        out = torch.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        return torch.relu(out)
"""
    
    def _mock_test_response(self) -> str:
        """Mock test generation response."""
        return """
import pytest
import torch
from src.resnet import ResidualBlock

def test_residual_block():
    block = ResidualBlock(64, 128, stride=2)
    x = torch.randn(2, 64, 32, 32)
    output = block(x)
    assert output.shape == (2, 128, 16, 16)
"""
    
    def _mock_validation_response(self) -> str:
        """Mock validation response."""
        return """
{
  "score": 94,
  "equation_coverage": 92,
  "hyperparam_coverage": 95,
  "critical_issues": [],
  "warnings": []
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