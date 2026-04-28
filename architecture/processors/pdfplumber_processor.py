"""PDFPlumber processor implementation."""

from architecture.base.base_processor import BaseProcessor
from architecture.core.registry import register_processor
from typing import Dict, Any, List


@register_processor("pdfplumber")
class PDFPlumberProcessor(BaseProcessor):
    """
    PDFPlumber-based paper processor.
    
    PDFPlumber provides better text extraction and table detection.
    
    Args:
        cache_dir: Directory for caching processed results
        seed: Random seed for reproducibility
        extract_tables: Whether to extract tables from PDF
    """

    def __init__(
        self,
        cache_dir: str = "./cache/pdfplumber",
        seed: int = 42,
        extract_tables: bool = True,
        **kwargs
    ):
        super().__init__(cache_dir, seed, **kwargs)
        self.extract_tables = extract_tables

    def process(self, paper_path: str, **kwargs) -> Dict[str, Any]:
        """Process paper using PDFPlumber."""
        try:
            import pdfplumber
            
            content = {
                "title": "",
                "abstract": "",
                "sections": [],
                "references": [],
                "full_text": "",
                "tables": []
            }
            
            with pdfplumber.open(paper_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                    
                    # Extract tables if enabled
                    if self.extract_tables:
                        tables = page.extract_tables()
                        if tables:
                            content["tables"].extend(tables)
                
                content["full_text"] = full_text
                
                # Try to extract title (usually first line)
                lines = full_text.split('\n')
                if lines:
                    content["title"] = lines[0].strip()
                
                # Try to extract abstract
                abstract_start = full_text.lower().find("abstract")
                if abstract_start != -1:
                    abstract_end = full_text.find("\n\n", abstract_start)
                    if abstract_end != -1:
                        content["abstract"] = full_text[abstract_start:abstract_end].strip()
            
            return content
            
        except ImportError:
            raise ImportError("pdfplumber package not installed. Install with: pip install pdfplumber")
        except FileNotFoundError:
            raise FileNotFoundError(f"Paper not found: {paper_path}")

    def extract_tables(self, paper_path: str) -> List[List[List[str]]]:
        """Extract all tables from PDF."""
        try:
            import pdfplumber
            
            tables = []
            with pdfplumber.open(paper_path) as pdf:
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
            
            return tables
            
        except ImportError:
            raise ImportError("pdfplumber package not installed. Install with: pip install pdfplumber")

    def extract_images(self, paper_path: str) -> List[Dict[str, Any]]:
        """Extract images from PDF."""
        try:
            import pdfplumber
            
            images = []
            with pdfplumber.open(paper_path) as pdf:
                for page_num, page in enumerate(pdf):
                    if page.images:
                        for img in page.images:
                            images.append({
                                "page": page_num,
                                "x0": img.get("x0"),
                                "y0": img.get("y0"),
                                "x1": img.get("x1"),
                                "y1": img.get("y1"),
                                "width": img.get("width"),
                                "height": img.get("height")
                            })
            
            return images
            
        except ImportError:
            raise ImportError("pdfplumber package not installed. Install with: pip install pdfplumber")
