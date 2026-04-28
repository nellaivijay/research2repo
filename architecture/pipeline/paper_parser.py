"""
PaperParser — Structured paper parsing module that converts research PDFs
into rich, structured formats using multiple parsing backends.

Parsing strategy (tried in order):
  1. s2orc-doc2json  — highest quality, requires local install
  2. GROBID REST API  — high quality, requires running GROBID server
  3. PyMuPDF (fitz)   — good quality, rich font/layout heuristics
  4. PyPDF2            — basic fallback, text-only extraction
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedPaper:
    """Structured representation of a parsed research paper."""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    sections: list[dict] = field(default_factory=list)       # [{name, content, subsections}]
    figures: list[dict] = field(default_factory=list)         # [{caption, page_num}]
    tables: list[dict] = field(default_factory=list)          # [{caption, content}]
    equations_raw: list[str] = field(default_factory=list)    # raw LaTeX strings
    references: list[str] = field(default_factory=list)
    full_text: str = ""
    metadata: dict = field(default_factory=dict)


class PaperParser:
    """
    Multi-backend paper parser that converts PDF files into structured
    :class:`ParsedPaper` objects.

    Tries parsing backends in order of quality:
      doc2json -> GROBID -> PyMuPDF -> PyPDF2
    Falls back gracefully when a backend is unavailable.
    """

    def __init__(self) -> None:
        self._parser_used: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, pdf_path: str) -> ParsedPaper:
        """
        Parse a PDF into a :class:`ParsedPaper`.

        Tries available backends in priority order and returns the first
        successful result.

        Args:
            pdf_path: Absolute or relative path to the PDF file.

        Returns:
            ParsedPaper with as much structure as the chosen backend can
            extract.

        Raises:
            FileNotFoundError: If *pdf_path* does not exist.
            RuntimeError: If every parsing backend fails.
        """
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Try backends in priority order
        backends = [
            ("doc2json", self._parse_with_doc2json),
            ("GROBID",   self._parse_with_grobid),
            ("PyMuPDF",  self._parse_with_pymupdf),
            ("PyPDF2",   self._parse_with_pypdf2),
        ]

        last_error: Optional[Exception] = None
        for name, method in backends:
            try:
                print(f"[PaperParser] Parsing with {name}...")
                result = method(pdf_path)
                self._parser_used = name
                print(f"[PaperParser] Successfully parsed with {name} "
                      f"({len(result.sections)} sections, "
                      f"{len(result.equations_raw)} equations).")
                return result
            except ImportError as exc:
                print(f"[PaperParser] {name} not available ({exc}). Trying next backend...")
                last_error = exc
            except ConnectionError as exc:
                print(f"[PaperParser] {name} connection failed ({exc}). Trying next backend...")
                last_error = exc
            except Exception as exc:  # noqa: BLE001
                print(f"[PaperParser] {name} failed ({exc}). Trying next backend...")
                last_error = exc

        raise RuntimeError(
            f"All parsing backends failed. Last error: {last_error}"
        )

    # ------------------------------------------------------------------
    # Backend: s2orc-doc2json
    # ------------------------------------------------------------------

    def _parse_with_doc2json(self, pdf_path: str) -> ParsedPaper:
        """Parse PDF using the s2orc-doc2json library (highest quality).

        Requires ``pip install doc2json``.
        """
        try:
            from doc2json.grobid2json.grobid.grobid_client import GrobidClient  # type: ignore[import-untyped]
            from doc2json.s2orc import load_s2orc  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError("doc2json is not installed. Install with: pip install s2orc-doc2json")

        result_dict = load_s2orc(pdf_path)

        sections: list[dict] = []
        for sec in result_dict.get("pdf_parse", {}).get("body_text", []):
            sections.append({
                "name": sec.get("section", ""),
                "content": sec.get("text", ""),
                "subsections": [],
            })

        references = [
            ref.get("title", "")
            for ref in result_dict.get("pdf_parse", {}).get("bib_entries", {}).values()
            if ref.get("title")
        ]

        full_text = "\n".join(s["content"] for s in sections)

        return ParsedPaper(
            title=result_dict.get("title", ""),
            authors=result_dict.get("authors", []),
            abstract=result_dict.get("abstract", ""),
            sections=sections,
            figures=[],
            tables=[],
            equations_raw=self._extract_equations_from_text(full_text),
            references=references,
            full_text=full_text,
            metadata=result_dict.get("metadata", {}),
        )

    # ------------------------------------------------------------------
    # Backend: GROBID REST API
    # ------------------------------------------------------------------

    def _parse_with_grobid(self, pdf_path: str) -> ParsedPaper:
        """Parse PDF using a running GROBID server (TEI XML output).

        Expects GROBID at ``http://localhost:8070``.
        """
        import requests  # type: ignore[import-untyped]

        from config.constants import DEFAULT_GROBID_URL, MAX_ABSTRACT_LENGTH

        grobid_url = os.environ.get(
            "GROBID_URL", DEFAULT_GROBID_URL
        )

        try:
            with open(pdf_path, "rb") as f:
                response = requests.post(
                    grobid_url,
                    files={"input": (os.path.basename(pdf_path), f, "application/pdf")},
                    timeout=120,
                )
            response.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            raise ConnectionError(
                f"Cannot reach GROBID server at {grobid_url}: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"GROBID request failed: {exc}") from exc

        tei_xml = response.text
        return self._parse_tei_xml(tei_xml)

    def _parse_tei_xml(self, tei_xml: str) -> ParsedPaper:
        """Extract structured data from GROBID's TEI XML output."""
        import xml.etree.ElementTree as ET

        ns = {"tei": "http://www.tei-c.org/ns/1.0"}
        root = ET.fromstring(tei_xml)

        # Title
        title_el = root.find(".//tei:titleStmt/tei:title", ns)
        title = (title_el.text or "").strip() if title_el is not None else ""

        # Authors
        authors: list[str] = []
        for author in root.findall(".//tei:sourceDesc//tei:persName", ns):
            forename = author.find("tei:forename", ns)
            surname = author.find("tei:surname", ns)
            name_parts = []
            if forename is not None and forename.text:
                name_parts.append(forename.text.strip())
            if surname is not None and surname.text:
                name_parts.append(surname.text.strip())
            if name_parts:
                authors.append(" ".join(name_parts))

        # Abstract
        abstract_el = root.find(".//tei:profileDesc/tei:abstract", ns)
        abstract = ""
        if abstract_el is not None:
            abstract = " ".join(
                (p.text or "") for p in abstract_el.findall(".//tei:p", ns)
            ).strip()

        # Body sections
        sections: list[dict] = []
        for div in root.findall(".//tei:body/tei:div", ns):
            head = div.find("tei:head", ns)
            sec_name = (head.text or "Untitled").strip() if head is not None else "Untitled"
            paragraphs = [
                (p.text or "") for p in div.findall("tei:p", ns)
            ]
            content = "\n".join(paragraphs).strip()
            sections.append({
                "name": sec_name,
                "content": content,
                "subsections": [],
            })

        # References
        references: list[str] = []
        for bibl in root.findall(".//tei:listBibl/tei:biblStruct", ns):
            ref_title = bibl.find(".//tei:title", ns)
            if ref_title is not None and ref_title.text:
                references.append(ref_title.text.strip())

        # Figures / tables
        figures: list[dict] = []
        tables: list[dict] = []
        for figure_el in root.findall(".//tei:figure", ns):
            fig_type = figure_el.attrib.get("type", "figure")
            head_el = figure_el.find("tei:head", ns)
            figdesc = figure_el.find("tei:figDesc", ns)
            caption = ""
            if head_el is not None and head_el.text:
                caption = head_el.text.strip()
            if figdesc is not None and figdesc.text:
                caption += " " + figdesc.text.strip()
            if fig_type == "table":
                tables.append({"caption": caption.strip(), "content": ""})
            else:
                figures.append({"caption": caption.strip(), "page_num": -1})

        full_text = "\n\n".join(s["content"] for s in sections)

        return ParsedPaper(
            title=title,
            authors=authors,
            abstract=abstract,
            sections=sections,
            figures=figures,
            tables=tables,
            equations_raw=self._extract_equations_from_text(full_text),
            references=references,
            full_text=full_text,
            metadata={"parser": "grobid"},
        )

    # ------------------------------------------------------------------
    # Backend: PyMuPDF (fitz)
    # ------------------------------------------------------------------

    def _parse_with_pymupdf(self, pdf_path: str) -> ParsedPaper:
        """Parse PDF using PyMuPDF for rich font/layout-aware extraction.

        Uses font-size heuristics to detect section headers and extracts
        embedded images.
        """
        try:
            import fitz  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError("PyMuPDF is not installed. Install with: pip install PyMuPDF")

        doc = fitz.open(pdf_path)

        # --- Collect text blocks with font info ---
        full_text_parts: list[str] = []
        blocks_with_meta: list[dict] = []  # {text, font_size, page, is_bold}

        for page_num, page in enumerate(doc):
            page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:  # text blocks only
                    continue
                for line in block.get("lines", []):
                    line_text = ""
                    max_font_size = 0.0
                    is_bold = False
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                        max_font_size = max(max_font_size, span.get("size", 0))
                        if "bold" in span.get("font", "").lower():
                            is_bold = True
                    line_text = line_text.strip()
                    if line_text:
                        blocks_with_meta.append({
                            "text": line_text,
                            "font_size": max_font_size,
                            "page": page_num,
                            "is_bold": is_bold,
                        })
                        full_text_parts.append(line_text)

        full_text = "\n".join(full_text_parts)

        # --- Compute median font size to detect headers ---
        font_sizes = [b["font_size"] for b in blocks_with_meta if b["font_size"] > 0]
        median_font = sorted(font_sizes)[len(font_sizes) // 2] if font_sizes else 10.0

        # --- Detect section headers via heuristics ---
        header_pattern = re.compile(
            r"^(?:\d+\.?\s+|[A-Z]\.\s+|#{1,3}\s+)"  # numbered or markdown-style
        )
        sections: list[dict] = []
        current_section: Optional[dict] = None

        for block in blocks_with_meta:
            is_header = (
                (block["font_size"] > median_font * 1.15 and block["is_bold"])
                or (block["font_size"] > median_font * 1.3)
                or bool(header_pattern.match(block["text"]))
            )
            # Don't treat very long lines as headers
            if is_header and len(block["text"]) < 120:
                if current_section is not None:
                    sections.append(current_section)
                current_section = {
                    "name": block["text"],
                    "content": "",
                    "subsections": [],
                }
            elif current_section is not None:
                current_section["content"] += block["text"] + "\n"
            # Text before the first section is ignored (title/header block)

        if current_section is not None:
            sections.append(current_section)

        # Strip trailing whitespace from section content
        for sec in sections:
            sec["content"] = sec["content"].strip()

        # --- Extract title (largest font on first page) ---
        first_page_blocks = [b for b in blocks_with_meta if b["page"] == 0]
        title = ""
        if first_page_blocks:
            title_block = max(first_page_blocks, key=lambda b: b["font_size"])
            title = title_block["text"]

        # --- Extract figures (embedded images) ---
        figures: list[dict] = []
        for page_num, page in enumerate(doc):
            for img_info in page.get_images(full=True):
                figures.append({
                    "caption": f"Image xref={img_info[0]}",
                    "page_num": page_num + 1,
                })

        # --- Try to extract abstract ---
        abstract = ""
        abstract_match = re.search(
            r"(?i)\babstract\b[\s.:—-]*\n?(.*?)(?=\n\s*\n|\n\d+[\s.]|$)",
            full_text,
            re.DOTALL,
        )
        if abstract_match:
            abstract = abstract_match.group(1).strip()[:MAX_ABSTRACT_LENGTH]

        page_count = len(doc)
        doc.close()

        return ParsedPaper(
            title=title,
            authors=[],  # Author extraction from raw layout is unreliable
            abstract=abstract,
            sections=sections,
            figures=figures,
            tables=[],
            equations_raw=self._extract_equations_from_text(full_text),
            references=[],
            full_text=full_text,
            metadata={"parser": "pymupdf", "page_count": page_count},
        )

    # ------------------------------------------------------------------
    # Backend: PyPDF2 (basic fallback)
    # ------------------------------------------------------------------

    def _parse_with_pypdf2(self, pdf_path: str) -> ParsedPaper:
        """Basic text-only extraction using PyPDF2.

        This is the lowest-quality fallback but has the fewest
        dependencies.
        """
        try:
            import PyPDF2  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError("PyPDF2 is not installed. Install with: pip install PyPDF2")

        text_parts: list[str] = []
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        full_text = "\n\n".join(text_parts)

        # Extract structure using regex heuristics
        sections = self._detect_sections(full_text)
        equations = self._extract_equations_from_text(full_text)

        # Attempt title from first non-empty line
        lines = [ln.strip() for ln in full_text.split("\n") if ln.strip()]
        title = lines[0] if lines else ""

        # Attempt abstract extraction
        abstract = ""
        abstract_match = re.search(
            r"(?i)\babstract\b[\s.:—-]*\n?(.*?)(?=\n\s*\n|\n\d+[\s.]|\bintroduction\b|$)",
            full_text,
            re.DOTALL,
        )
        if abstract_match:
            abstract = abstract_match.group(1).strip()[:MAX_ABSTRACT_LENGTH]

        return ParsedPaper(
            title=title,
            authors=[],
            abstract=abstract,
            sections=sections,
            figures=[],
            tables=[],
            equations_raw=equations,
            references=[],
            full_text=full_text,
            metadata={"parser": "pypdf2"},
        )

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _detect_sections(self, text: str) -> list[dict]:
        """Detect section boundaries using regex heuristics.

        Recognises patterns like:
          - ``1. Introduction``
          - ``2 Related Work``
          - ``## Method``
          - ``A.1 Appendix Details``
          - ``III. Experiments`` (roman numerals)
        """
        section_pattern = re.compile(
            r"^("
            r"(?:\d+\.?\d*\.?\s+)"           # 1. / 1 / 2.1 / 2.1.
            r"|(?:#{1,3}\s+)"                 # ## Markdown headers
            r"|(?:[A-Z]\.?\d*\.?\s+)"         # A. / A.1 / B
            r"|(?:[IVX]+\.?\s+)"              # Roman numerals
            r")"
            r"([A-Z][^\n]{2,80})",            # Section title (capitalised, 3-80 chars)
            re.MULTILINE,
        )

        matches = list(section_pattern.finditer(text))
        sections: list[dict] = []

        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_name = match.group(0).strip()
            content = text[start:end].strip()
            sections.append({
                "name": section_name,
                "content": content,
                "subsections": [],
            })

        return sections

    def _extract_equations_from_text(self, text: str) -> list[str]:
        r"""Extract LaTeX equations from raw text.

        Matches:
          - Inline math: ``$...$`` (not ``$$``)
          - Display math: ``$$...$$``
          - Bracket display: ``\[...\]``
          - Environments: ``\begin{equation}...\end{equation}``,
            ``\begin{align}...\end{align}``, etc.
        """
        equations: list[str] = []

        # \begin{equation/align/gather/multline}...\end{...}
        env_pattern = re.compile(
            r"\\begin\{(equation|align|gather|multline)\*?\}"
            r"(.*?)"
            r"\\end\{\1\*?\}",
            re.DOTALL,
        )
        for match in env_pattern.finditer(text):
            eq = match.group(2).strip()
            if eq:
                equations.append(eq)

        # \[...\] display math
        bracket_pattern = re.compile(r"\\\[(.*?)\\\]", re.DOTALL)
        for match in bracket_pattern.finditer(text):
            eq = match.group(1).strip()
            if eq:
                equations.append(eq)

        # $$...$$ display math
        double_dollar = re.compile(r"\$\$(.*?)\$\$", re.DOTALL)
        for match in double_dollar.finditer(text):
            eq = match.group(1).strip()
            if eq:
                equations.append(eq)

        # $...$ inline math (avoid matching $$ and currency-like patterns)
        inline_pattern = re.compile(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)")
        for match in inline_pattern.finditer(text):
            eq = match.group(1).strip()
            # Filter out likely non-equation matches (pure numbers, short)
            if eq and len(eq) > 2 and not eq.replace(",", "").replace(".", "").isdigit():
                equations.append(eq)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for eq in equations:
            normalized = eq.strip()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(normalized)

        return unique
