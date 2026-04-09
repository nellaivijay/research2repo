"""
EquationExtractor — Extracts ALL mathematical equations from a paper,
converts them to LaTeX + PyTorch pseudocode, and maps them to code locations.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from providers.base import BaseProvider, GenerationConfig, ModelCapability
from providers import get_provider


@dataclass
class ExtractedEquation:
    """A single equation extracted from the paper."""
    equation_number: str = ""
    section: str = ""
    latex: str = ""
    pytorch: str = ""
    description: str = ""
    variables: dict[str, str] = field(default_factory=dict)
    category: str = ""  # forward_pass, loss, initialization, optimization, metric


class EquationExtractor:
    """
    Dedicated equation extraction using vision-capable models.
    Extracts equations from both text and rendered figures.
    """

    PROMPT_FILE = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "prompts", "equation_extractor.txt"
    )

    def __init__(self, provider: Optional[BaseProvider] = None):
        self.provider = provider or get_provider(
            required_capability=ModelCapability.VISION
        )

    def _load_prompt(self, path: str) -> str:
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
        return ""

    def extract_from_text(self, paper_text: str) -> list[ExtractedEquation]:
        """Extract equations from extracted paper text."""
        prompt = self._load_prompt(self.PROMPT_FILE)
        if not prompt:
            prompt = self._default_prompt()

        full_prompt = f"## Paper Text\n\n{paper_text[:80000]}\n\n---\n\n{prompt}"

        config = GenerationConfig(
            temperature=0.1,
            max_output_tokens=8192,
            response_format="json",
        )

        result = self.provider.generate(
            prompt=full_prompt,
            system_prompt="You are an expert at extracting mathematical equations from ML papers.",
            config=config,
        )

        return self._parse_equations(result.text)

    def extract_from_images(self, page_images: list[bytes]) -> list[ExtractedEquation]:
        """Extract equations from PDF page images using vision."""
        if not self.provider.supports(ModelCapability.VISION):
            print("  [EquationExtractor] No vision support; skipping image extraction.")
            return []

        prompt = self._load_prompt(self.PROMPT_FILE)
        if not prompt:
            prompt = self._default_prompt()

        all_equations = []
        batch_size = 4
        for i in range(0, len(page_images), batch_size):
            batch = page_images[i:i + batch_size]
            result = self.provider.generate(
                prompt=prompt,
                system_prompt="Extract all mathematical equations from these pages.",
                images=batch,
                config=GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=4096,
                    response_format="json",
                ),
            )
            all_equations.extend(self._parse_equations(result.text))

        return all_equations

    def extract(
        self,
        paper_text: str,
        page_images: Optional[list[bytes]] = None,
    ) -> list[ExtractedEquation]:
        """Extract equations from both text and images, deduplicate."""
        print("  [EquationExtractor] Extracting equations...")

        text_eqs = self.extract_from_text(paper_text)
        image_eqs = self.extract_from_images(page_images) if page_images else []

        # Deduplicate by LaTeX content
        seen = set()
        unique = []
        for eq in text_eqs + image_eqs:
            key = eq.latex.strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(eq)

        print(f"  [EquationExtractor] Found {len(unique)} unique equations.")
        return unique

    def map_to_files(
        self,
        equations: list[ExtractedEquation],
        generated_files: dict[str, str],
    ) -> dict[str, list[ExtractedEquation]]:
        """Map equations to the files that should implement them."""
        mapping: dict[str, list[ExtractedEquation]] = {}

        for eq in equations:
            # Search for equation terms in generated files
            search_terms = [
                eq.latex[:30] if eq.latex else "",
                eq.description[:50] if eq.description else "",
            ]
            for file_path, content in generated_files.items():
                content_lower = content.lower()
                for term in search_terms:
                    if term and term.lower()[:20] in content_lower:
                        mapping.setdefault(file_path, []).append(eq)
                        break

        return mapping

    def _parse_equations(self, text: str) -> list[ExtractedEquation]:
        """Parse JSON response into ExtractedEquation objects."""
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
            if isinstance(data, dict) and "equations" in data:
                data = data["equations"]
            if not isinstance(data, list):
                data = [data]
        except json.JSONDecodeError:
            return []

        equations = []
        for item in data:
            if isinstance(item, dict):
                equations.append(ExtractedEquation(
                    equation_number=item.get("equation_number", ""),
                    section=item.get("section", ""),
                    latex=item.get("latex", ""),
                    pytorch=item.get("pytorch", ""),
                    description=item.get("description", ""),
                    variables=item.get("variables", {}),
                    category=item.get("category", ""),
                ))
        return equations

    def _default_prompt(self) -> str:
        return (
            "Extract ALL mathematical equations from this paper. "
            "For each, provide: equation_number, section, latex, pytorch pseudocode, "
            "description, variables dict, and category. "
            "Return a JSON array."
        )
