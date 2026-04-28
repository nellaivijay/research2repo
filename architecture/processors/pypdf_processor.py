"""PyPDF2 processor implementation."""

from architecture.base.base_processor import BaseProcessor
from architecture.core.registry import register_processor
from typing import Dict, Any


@register_processor("pypdf")
class PyPDFProcessor(BaseProcessor):
    """
    PyPDF2-based paper processor.
    
    Args:
        cache_dir: Directory for caching processed results
        seed: Random seed for reproducibility
    """

    def __init__(
        self,
        cache_dir: str = "./cache/pypdf",
        seed: int = 42,
        **kwargs
    ):
        super().__init__(cache_dir, seed, **kwargs)

    def process(self, paper_path: str, **kwargs) -> Dict[str, Any]:
        """Process paper using PyPDF2."""
        try:
            import PyPDF2
            
            content = {
                "title": "",
                "abstract": "",
                "sections": [],
                "references": [],
                "full_text": ""
            }
            
            with open(paper_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Extract text from all pages
                full_text = ""
                for page in reader.pages:
                    full_text += page.extract_text() + "\n"
                
                content["full_text"] = full_text
                
                # Try to extract title (usually first line)
                lines = full_text.split('\n')
                if lines:
                    content["title"] = lines[0].strip()
                
                # Try to extract abstract (look for "Abstract" keyword)
                abstract_start = full_text.lower().find("abstract")
                if abstract_start != -1:
                    abstract_end = full_text.find("\n\n", abstract_start)
                    if abstract_end != -1:
                        content["abstract"] = full_text[abstract_start:abstract_end].strip()
            
            return content
            
        except ImportError:
            raise ImportError("PyPDF2 package not installed. Install with: pip install PyPDF2")
        except FileNotFoundError:
            raise FileNotFoundError(f"Paper not found: {paper_path}")

    def extract_metadata(self, paper_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF."""
        try:
            import PyPDF2
            
            with open(paper_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                metadata = reader.metadata
                
                return {
                    "title": metadata.get("/Title", ""),
                    "author": metadata.get("/Author", ""),
                    "subject": metadata.get("/Subject", ""),
                    "creator": metadata.get("/Creator", ""),
                    "producer": metadata.get("/Producer", ""),
                    "creation_date": metadata.get("/CreationDate", ""),
                    "modification_date": metadata.get("/ModDate", "")
                }
                
        except ImportError:
            raise ImportError("PyPDF2 package not installed. Install with: pip install PyPDF2")
