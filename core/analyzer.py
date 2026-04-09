"""
PaperAnalyzer — Ingests PDF, extracts text, identifies sections,
extracts architecture diagrams via vision, and produces structured
analysis for downstream pipeline stages.

Supports any provider with TEXT_GENERATION; uses VISION-capable
providers for diagram extraction when available.
"""

import io
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from providers.base import BaseProvider, GenerationConfig, ModelCapability
from providers import get_provider


@dataclass
class PaperAnalysis:
    """Structured output from paper analysis."""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    sections: dict[str, str] = field(default_factory=dict)  # section_name -> content
    equations: list[str] = field(default_factory=list)        # LaTeX strings
    hyperparameters: dict[str, str] = field(default_factory=dict)
    architecture_description: str = ""
    key_contributions: list[str] = field(default_factory=list)
    datasets_mentioned: list[str] = field(default_factory=list)
    loss_functions: list[str] = field(default_factory=list)
    full_text: str = ""
    diagrams_mermaid: list[str] = field(default_factory=list)
    raw_token_count: int = 0


class PaperAnalyzer:
    """
    Analyzes a research paper PDF using LLM providers.

    Strategy selection:
      - If provider supports FILE_UPLOAD (Gemini): upload entire PDF for
        zero-RAG long-context analysis.
      - Otherwise: extract text with PyPDF2 and send as prompt text.
      - If provider supports VISION: extract page images for diagram analysis.
    """

    # Prompt loaded from templates at runtime
    ANALYSIS_PROMPT_FILE = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "prompts", "analyzer.txt"
    )
    DIAGRAM_PROMPT_FILE = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "prompts", "diagram_extractor.txt"
    )

    def __init__(
        self,
        provider: Optional[BaseProvider] = None,
        vision_provider: Optional[BaseProvider] = None,
    ):
        """
        Args:
            provider: Primary text provider. Auto-detected if None.
            vision_provider: Provider for diagram extraction. Falls back to
                             primary if it has VISION, or auto-detects.
        """
        self.provider = provider or get_provider(
            required_capability=ModelCapability.LONG_CONTEXT
        )
        if vision_provider:
            self.vision_provider = vision_provider
        elif self.provider.supports(ModelCapability.VISION):
            self.vision_provider = self.provider
        else:
            try:
                self.vision_provider = get_provider(
                    required_capability=ModelCapability.VISION
                )
            except RuntimeError:
                self.vision_provider = None

        self._uploaded_file = None  # Gemini File API handle

    def _load_prompt(self, path: str, **kwargs) -> str:
        """Load a prompt template and substitute placeholders."""
        if os.path.exists(path):
            with open(path) as f:
                template = f.read()
            for key, value in kwargs.items():
                template = template.replace(f"{{{{{key}}}}}", str(value))
            return template
        return ""

    def _extract_text_pypdf(self, pdf_path: str) -> str:
        """Extract text from PDF using PyPDF2."""
        import PyPDF2

        text_parts = []
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n\n".join(text_parts)

    def _extract_page_images(self, pdf_path: str) -> list[bytes]:
        """Convert PDF pages to images for vision analysis."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            print("  [Analyzer] PyMuPDF not installed; skipping image extraction.")
            return []

        images = []
        doc = fitz.open(pdf_path)
        for page_num in range(min(len(doc), 30)):  # Cap at 30 pages
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            images.append(pix.tobytes("png"))
        doc.close()
        return images

    def upload_document(self, pdf_path: str) -> object:
        """
        Upload PDF via provider's file API (Gemini) if supported.
        Returns the uploaded file handle, or extracted text as fallback.
        """
        if self.provider.supports(ModelCapability.FILE_UPLOAD):
            self._uploaded_file = self.provider.upload_file(pdf_path)
            return self._uploaded_file
        else:
            print("  [Analyzer] Provider does not support file upload; extracting text locally...")
            text = self._extract_text_pypdf(pdf_path)
            self._uploaded_file = None
            return text

    def extract_diagrams_to_mermaid(self, pdf_path: str) -> list[str]:
        """
        Extract architecture diagrams from the PDF and convert to Mermaid.js.
        Uses vision-capable provider if available.
        """
        if not self.vision_provider:
            print("  [Analyzer] No vision provider available; skipping diagram extraction.")
            return []

        print("  [Analyzer] Extracting diagrams via vision model...")
        page_images = self._extract_page_images(pdf_path)
        if not page_images:
            return []

        prompt = self._load_prompt(self.DIAGRAM_PROMPT_FILE)
        if not prompt:
            prompt = (
                "Analyze these research paper pages. For each architecture diagram, "
                "neural network figure, or system flowchart you find, convert it to "
                "a Mermaid.js diagram. Return ONLY the Mermaid code blocks, separated "
                "by '---'. If no diagrams are found, respond with 'NO_DIAGRAMS'."
            )

        # Process in batches of 4 pages (vision token limits)
        mermaid_diagrams = []
        batch_size = 4
        for i in range(0, len(page_images), batch_size):
            batch = page_images[i : i + batch_size]
            result = self.vision_provider.generate(
                prompt=prompt,
                system_prompt="You are an expert at reading ML paper diagrams and converting them to Mermaid.js.",
                images=batch,
                config=GenerationConfig(temperature=0.1, max_output_tokens=4096),
            )

            if "NO_DIAGRAMS" not in result.text:
                # Parse mermaid blocks
                blocks = re.findall(
                    r"```mermaid\s*(.*?)```", result.text, re.DOTALL
                )
                if blocks:
                    mermaid_diagrams.extend(blocks)
                elif "---" in result.text:
                    parts = result.text.split("---")
                    mermaid_diagrams.extend([p.strip() for p in parts if p.strip()])

        print(f"  [Analyzer] Extracted {len(mermaid_diagrams)} diagram(s).")
        return mermaid_diagrams

    def analyze(self, document: object, vision_context: list[str]) -> PaperAnalysis:
        """
        Perform full structured analysis of the paper.

        Args:
            document: Uploaded file handle (Gemini) or extracted text string.
            vision_context: List of Mermaid diagram strings from diagram extraction.

        Returns:
            PaperAnalysis with all extracted information.
        """
        print("  [Analyzer] Running structured paper analysis...")

        prompt = self._load_prompt(self.ANALYSIS_PROMPT_FILE)
        if not prompt:
            prompt = self._default_analysis_prompt()

        if vision_context:
            diagram_section = "\n\n## Extracted Architecture Diagrams (Mermaid)\n"
            for i, d in enumerate(vision_context, 1):
                diagram_section += f"\n### Diagram {i}\n```mermaid\n{d}\n```\n"
            prompt += diagram_section

        config = GenerationConfig(
            temperature=0.1,
            max_output_tokens=8192,
            response_format="json",
        )

        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "authors": {"type": "array", "items": {"type": "string"}},
                "abstract": {"type": "string"},
                "sections": {"type": "object"},
                "equations": {"type": "array", "items": {"type": "string"}},
                "hyperparameters": {"type": "object"},
                "architecture_description": {"type": "string"},
                "key_contributions": {"type": "array", "items": {"type": "string"}},
                "datasets_mentioned": {"type": "array", "items": {"type": "string"}},
                "loss_functions": {"type": "array", "items": {"type": "string"}},
            },
        }

        # Use file-based generation for Gemini, text for others
        if self._uploaded_file and hasattr(self.provider, "generate_with_file"):
            result = self.provider.generate_with_file(
                uploaded_file=self._uploaded_file,
                prompt=prompt,
                system_prompt="You are an expert ML researcher. Analyze this paper thoroughly.",
                config=config,
            )
        else:
            # document is the extracted text
            full_prompt = f"## Paper Text\n\n{document}\n\n---\n\n{prompt}"
            result = self.provider.generate(
                prompt=full_prompt,
                system_prompt="You are an expert ML researcher. Analyze this paper thoroughly.",
                config=config,
            )

        # Parse the structured response
        try:
            data = self._parse_json_response(result.text)
        except Exception as e:
            print(f"  [Analyzer] Warning: structured parse failed ({e}), using fallback.")
            data = {}

        analysis = PaperAnalysis(
            title=data.get("title", ""),
            authors=data.get("authors", []),
            abstract=data.get("abstract", ""),
            sections=data.get("sections", {}),
            equations=data.get("equations", []),
            hyperparameters=data.get("hyperparameters", {}),
            architecture_description=data.get("architecture_description", ""),
            key_contributions=data.get("key_contributions", []),
            datasets_mentioned=data.get("datasets_mentioned", []),
            loss_functions=data.get("loss_functions", []),
            full_text=document if isinstance(document, str) else "",
            diagrams_mermaid=vision_context,
            raw_token_count=result.input_tokens + result.output_tokens,
        )

        print(f"  [Analyzer] Analysis complete: '{analysis.title}' "
              f"({len(analysis.equations)} equations, "
              f"{len(analysis.hyperparameters)} hyperparams)")
        return analysis

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from model response, handling markdown fences."""
        import json
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())

    def _default_analysis_prompt(self) -> str:
        return """Analyze this machine learning research paper and extract the following into a JSON object:

1. "title": The paper title
2. "authors": List of author names
3. "abstract": The full abstract
4. "sections": A dict mapping section names to their content summaries
5. "equations": List of ALL mathematical equations in LaTeX format (e.g., "L = -\\sum y_i \\log(p_i)")
6. "hyperparameters": Dict of hyperparameter names to their values/descriptions (learning rate, batch size, layers, dimensions, etc.)
7. "architecture_description": Detailed description of the model architecture
8. "key_contributions": List of the paper's main contributions
9. "datasets_mentioned": List of datasets used or referenced
10. "loss_functions": List of loss functions used, in LaTeX format

Be thorough — capture EVERY equation, hyperparameter, and architectural detail.
Respond with ONLY the JSON object."""
