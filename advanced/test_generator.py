"""
TestGenerator — Auto-generates unit tests for the generated ML codebase.
Covers dimension checks, equation verification, config validation, and integration.
"""

import os
from typing import Optional

from providers.base import BaseProvider, GenerationConfig, ModelCapability
from providers import get_provider
from core.analyzer import PaperAnalysis
from core.architect import ArchitecturePlan


class TestGenerator:
    """
    Generates comprehensive pytest test suites for generated ML code.

    Test categories:
      - Dimension tests: tensor shape verification through forward pass
      - Equation tests: numerical correctness of key operations
      - Config tests: hyperparameter injection and defaults
      - Integration tests: full forward/backward pass
    """

    PROMPT_FILE = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "prompts", "test_generator.txt"
    )

    def __init__(self, provider: Optional[BaseProvider] = None):
        self.provider = provider or get_provider(
            required_capability=ModelCapability.CODE_GENERATION
        )

    def _load_prompt(self, path: str) -> str:
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
        return ""

    def generate_tests(
        self,
        generated_files: dict[str, str],
        analysis: PaperAnalysis,
        plan: ArchitecturePlan,
    ) -> dict[str, str]:
        """
        Generate test files for the codebase.

        Returns:
            Dict mapping test file paths to content.
        """
        print("  [TestGenerator] Generating test suite...")

        prompt = self._load_prompt(self.PROMPT_FILE)
        if not prompt:
            prompt = self._default_prompt()

        # Build context
        context = self._build_context(generated_files, analysis, plan)

        # Generate tests for model components
        test_files = {}

        # 1. Model dimension tests
        model_files = {k: v for k, v in generated_files.items()
                       if "model" in k and k.endswith(".py") and "__init__" not in k}
        if model_files:
            test_content = self._generate_test_file(
                context, model_files, analysis, prompt,
                "model dimension and forward pass"
            )
            test_files["tests/test_model.py"] = test_content

        # 2. Loss function tests
        loss_files = {k: v for k, v in generated_files.items()
                      if any(term in k.lower() for term in ("loss", "criterion", "objective"))}
        train_files = {k: v for k, v in generated_files.items()
                       if "train" in k.lower() and k.endswith(".py")}
        if loss_files or train_files:
            test_content = self._generate_test_file(
                context, {**loss_files, **train_files}, analysis, prompt,
                "loss function correctness"
            )
            test_files["tests/test_loss.py"] = test_content

        # 3. Config and integration tests
        test_content = self._generate_integration_tests(context, generated_files, analysis, plan)
        test_files["tests/test_integration.py"] = test_content

        # 4. conftest.py
        test_files["tests/conftest.py"] = self._generate_conftest(analysis, plan)

        # 5. tests/__init__.py
        test_files["tests/__init__.py"] = ""

        print(f"  [TestGenerator] Generated {len(test_files)} test files.")
        return test_files

    def _generate_test_file(
        self,
        context: str,
        target_files: dict[str, str],
        analysis: PaperAnalysis,
        prompt: str,
        focus: str,
    ) -> str:
        """Generate a single test file focusing on specific aspects."""
        file_context = "\n".join(
            f"\n## {path}\n```python\n{content}\n```"
            for path, content in target_files.items()
        )

        full_prompt = (
            f"{context}\n\n"
            f"## Code to Test\n{file_context}\n\n"
            f"## Focus: {focus}\n\n"
            f"---\n\n{prompt}"
        )

        result = self.provider.generate(
            prompt=full_prompt,
            system_prompt=(
                "You are an expert at writing pytest tests for ML code. "
                "Output ONLY the test file content. No markdown fences."
            ),
            config=GenerationConfig(temperature=0.15, max_output_tokens=8192),
        )

        return self._clean_output(result.text)

    def _generate_integration_tests(
        self,
        context: str,
        generated_files: dict[str, str],
        analysis: PaperAnalysis,
        plan: ArchitecturePlan,
    ) -> str:
        """Generate integration tests for full pipeline."""
        prompt = f"""{context}

## Task: Generate integration tests that verify:
1. Model can be instantiated with the paper's config
2. Full forward pass produces correct output shape
3. Backward pass computes gradients for all parameters
4. A single training step reduces loss
5. Model can be saved and loaded
6. Config defaults match paper values

Use pytest fixtures, parametrize where useful.
Output ONLY the test file content. No explanations."""

        result = self.provider.generate(
            prompt=prompt,
            system_prompt="You are an ML test engineer. Write thorough pytest integration tests.",
            config=GenerationConfig(temperature=0.15, max_output_tokens=8192),
        )

        return self._clean_output(result.text)

    def _generate_conftest(self, analysis: PaperAnalysis, plan: ArchitecturePlan) -> str:
        """Generate pytest conftest.py with shared fixtures."""
        config_values = "\n".join(
            f'    "{k}": {repr(v)},' for k, v in list(analysis.hyperparameters.items())[:20]
        )

        return f'''"""
Shared pytest fixtures for {analysis.title} tests.
Auto-generated by Research2Repo.
"""

import pytest
import torch


@pytest.fixture
def device():
    """Get available device."""
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


@pytest.fixture
def paper_config():
    """Default config matching the paper\'s hyperparameters."""
    return {{
{config_values}
    }}


@pytest.fixture
def small_config():
    """Reduced config for fast testing."""
    return {{
        "d_model": 64,
        "num_heads": 4,
        "num_layers": 2,
        "d_ff": 128,
        "dropout": 0.0,
        "max_seq_len": 32,
        "vocab_size": 100,
        "batch_size": 2,
    }}


@pytest.fixture
def sample_batch(small_config, device):
    """Generate a sample batch for testing."""
    batch_size = small_config.get("batch_size", 2)
    seq_len = small_config.get("max_seq_len", 32)
    vocab_size = small_config.get("vocab_size", 100)

    return {{
        "input_ids": torch.randint(0, vocab_size, (batch_size, seq_len), device=device),
        "attention_mask": torch.ones(batch_size, seq_len, dtype=torch.long, device=device),
        "labels": torch.randint(0, vocab_size, (batch_size, seq_len), device=device),
    }}
'''

    def _build_context(
        self,
        generated_files: dict[str, str],
        analysis: PaperAnalysis,
        plan: ArchitecturePlan,
    ) -> str:
        """Build context for test generation."""
        parts = [
            f"# Paper: {analysis.title}",
            f"\n## Key Equations",
        ]
        for eq in analysis.equations[:15]:
            parts.append(f"  - {eq}")

        parts.append("\n## Hyperparameters")
        for k, v in analysis.hyperparameters.items():
            parts.append(f"  - {k}: {v}")

        parts.append(f"\n## Repository Structure\n{plan.directory_tree}")

        parts.append(f"\n## Requirements: {', '.join(plan.requirements)}")

        return "\n".join(parts)

    def _clean_output(self, text: str) -> str:
        """Clean model output."""
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].rstrip()
        return text

    def _default_prompt(self) -> str:
        return (
            "Generate comprehensive pytest tests. Include dimension tests, "
            "equation verification, and integration tests. "
            "Output ONLY the test file content."
        )
