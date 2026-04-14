"""
Global configuration for Research2Repo.
"""

import os
from dataclasses import dataclass, field


@dataclass
class R2RConfig:
    """Top-level configuration for the Research2Repo pipeline."""

    # Provider defaults
    default_provider: str = "auto"  # auto, gemini, openai, anthropic, ollama
    default_model: str = ""         # Empty = use provider default

    # Pipeline toggles
    enable_validation: bool = True
    enable_test_generation: bool = True
    enable_equation_extraction: bool = True
    enable_caching: bool = True
    max_fix_iterations: int = 2

    # Download settings
    pdf_timeout: int = 120
    pdf_max_size_mb: int = 100

    # Generation settings
    code_temperature: float = 0.15
    analysis_temperature: float = 0.1
    max_code_tokens: int = 16384
    max_analysis_tokens: int = 8192

    # Timeout settings (seconds)
    llm_generation_timeout: int = 600
    validation_timeout: int = 300
    execution_timeout: int = 900

    # Vision settings
    max_diagram_pages: int = 30
    diagram_dpi: int = 150
    vision_batch_size: int = 4

    # CodeRAG settings
    enable_code_rag: bool = False
    code_rag_max_repos: int = 3
    code_rag_max_files: int = 20

    # Document segmentation settings
    enable_segmentation: bool = True  # auto-enabled when paper exceeds token limit
    segmentation_max_chars: int = 12000
    segmentation_overlap: int = 500

    # Context management settings
    enable_context_manager: bool = True
    context_max_chars: int = 80000
    context_use_llm_summaries: bool = True

    # Cache settings
    cache_dir: str = ".r2r_cache"

    # Output settings
    verbose: bool = False

    def max_tokens_for_file(self, file_path: str) -> int:
        """Return adaptive token limit based on file type."""
        if file_path.endswith((".yaml", ".yml", ".toml", ".cfg", ".txt")):
            return 2048
        if file_path.endswith(".md"):
            return 2048
        lower = file_path.lower()
        if "model" in lower or "network" in lower or "encoder" in lower or "decoder" in lower:
            return 12288
        if "train" in lower or "trainer" in lower:
            return 10240
        if "test" in lower:
            return 6144
        if "config" in lower or "utils" in lower or "__init__" in lower:
            return 4096
        return 8192

    @classmethod
    def from_env(cls) -> "R2RConfig":
        """Create config from environment variables."""
        return cls(
            default_provider=os.environ.get("R2R_PROVIDER", "auto"),
            default_model=os.environ.get("R2R_MODEL", ""),
            enable_validation=os.environ.get("R2R_SKIP_VALIDATION", "").lower() != "true",
            enable_test_generation=os.environ.get("R2R_SKIP_TESTS", "").lower() != "true",
            enable_caching=os.environ.get("R2R_NO_CACHE", "").lower() != "true",
            cache_dir=os.environ.get("R2R_CACHE_DIR", ".r2r_cache"),
            verbose=os.environ.get("R2R_VERBOSE", "").lower() == "true",
        )
