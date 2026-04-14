"""
PipelineCache — Caches expensive operations (PDF uploads, analysis results,
generated files) to avoid redundant API calls on re-runs.

Uses a content-addressed cache keyed on file hashes.
"""

import hashlib
import json
import os
import pickle
from pathlib import Path
from typing import Optional


class PipelineCache:
    """
    File-system cache for Research2Repo pipeline stages.

    Cache structure:
      .r2r_cache/
        {pdf_hash}/
          analysis.json       # Paper analysis
          architecture.json   # Architecture plan
          equations.json      # Extracted equations
          files/              # Generated code files
            model/attention.py
            ...
          validation.json     # Validation report
          metadata.json       # Run metadata (timestamps, models used)
    """

    DEFAULT_DIR = ".r2r_cache"

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or self.DEFAULT_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._file_hash_cache: dict[str, str] = {}  # path -> truncated hex digest

    def _hash_file(self, file_path: str) -> str:
        """SHA-256 hash of a file for cache keying (memoized per instance)."""
        cached = self._file_hash_cache.get(file_path)
        if cached is not None:
            return cached
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        digest = h.hexdigest()[:16]
        self._file_hash_cache[file_path] = digest
        return digest

    def _hash_string(self, content: str) -> str:
        """SHA-256 hash of a string."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _run_dir(self, pdf_path: str) -> Path:
        """Get the cache directory for a specific PDF."""
        pdf_hash = self._hash_file(pdf_path)
        run_dir = self.cache_dir / pdf_hash
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def has_analysis(self, pdf_path: str) -> bool:
        """Check if analysis is cached for this PDF."""
        return (self._run_dir(pdf_path) / "analysis.json").exists()

    def save_analysis(self, pdf_path: str, analysis: object) -> None:
        """Cache the paper analysis."""
        run_dir = self._run_dir(pdf_path)
        with open(run_dir / "analysis.pkl", "wb") as f:
            pickle.dump(analysis, f)
        # Also save a JSON summary for human inspection
        if hasattr(analysis, "__dict__"):
            summary = {k: str(v)[:500] for k, v in analysis.__dict__.items()}
            with open(run_dir / "analysis.json", "w") as f:
                json.dump(summary, f, indent=2)
        print(f"  [Cache] Saved analysis to {run_dir / 'analysis.json'}")

    def load_analysis(self, pdf_path: str) -> Optional[object]:
        """Load cached analysis."""
        pkl_path = self._run_dir(pdf_path) / "analysis.pkl"
        if pkl_path.exists():
            with open(pkl_path, "rb") as f:
                print(f"  [Cache] Loaded analysis from cache.")
                return pickle.load(f)
        return None

    def has_architecture(self, pdf_path: str) -> bool:
        return (self._run_dir(pdf_path) / "architecture.pkl").exists()

    def save_architecture(self, pdf_path: str, plan: object) -> None:
        run_dir = self._run_dir(pdf_path)
        with open(run_dir / "architecture.pkl", "wb") as f:
            pickle.dump(plan, f)
        print(f"  [Cache] Saved architecture plan.")

    def load_architecture(self, pdf_path: str) -> Optional[object]:
        pkl_path = self._run_dir(pdf_path) / "architecture.pkl"
        if pkl_path.exists():
            with open(pkl_path, "rb") as f:
                print(f"  [Cache] Loaded architecture plan from cache.")
                return pickle.load(f)
        return None

    def has_generated_files(self, pdf_path: str) -> bool:
        files_dir = self._run_dir(pdf_path) / "files"
        return files_dir.exists() and any(files_dir.rglob("*"))

    def save_generated_files(self, pdf_path: str, files: dict[str, str]) -> None:
        run_dir = self._run_dir(pdf_path)
        files_dir = run_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        for path, content in files.items():
            file_path = files_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
        # Save manifest
        with open(run_dir / "files_manifest.json", "w") as f:
            json.dump(list(files.keys()), f, indent=2)
        print(f"  [Cache] Saved {len(files)} generated files.")

    def load_generated_files(self, pdf_path: str) -> Optional[dict[str, str]]:
        files_dir = self._run_dir(pdf_path) / "files"
        if not files_dir.exists():
            return None
        files = {}
        for file_path in files_dir.rglob("*"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(files_dir))
                files[rel_path] = file_path.read_text()
        if files:
            print(f"  [Cache] Loaded {len(files)} files from cache.")
        return files if files else None

    def save_validation(self, pdf_path: str, report: object) -> None:
        run_dir = self._run_dir(pdf_path)
        with open(run_dir / "validation.pkl", "wb") as f:
            pickle.dump(report, f)

    def load_validation(self, pdf_path: str) -> Optional[object]:
        pkl_path = self._run_dir(pdf_path) / "validation.pkl"
        if pkl_path.exists():
            with open(pkl_path, "rb") as f:
                return pickle.load(f)
        return None

    def save_metadata(self, pdf_path: str, metadata: dict) -> None:
        """Save run metadata (provider, model, timestamps, etc.)."""
        run_dir = self._run_dir(pdf_path)
        with open(run_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

    def load_metadata(self, pdf_path: str) -> Optional[dict]:
        meta_path = self._run_dir(pdf_path) / "metadata.json"
        if meta_path.exists():
            with open(meta_path) as f:
                return json.load(f)
        return None

    def clear(self, pdf_path: Optional[str] = None) -> None:
        """Clear cache for a specific PDF, or all caches."""
        import shutil
        if pdf_path:
            run_dir = self._run_dir(pdf_path)
            if run_dir.exists():
                shutil.rmtree(run_dir)
                print(f"  [Cache] Cleared cache for {pdf_path}")
        else:
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                print("  [Cache] Cleared all caches.")

    def summary(self) -> str:
        """Return a summary of cached runs."""
        if not self.cache_dir.exists():
            return "No cache entries."
        entries = list(self.cache_dir.iterdir())
        lines = [f"Cache: {self.cache_dir} ({len(entries)} entries)"]
        for entry in entries:
            if entry.is_dir():
                meta_path = entry / "metadata.json"
                if meta_path.exists():
                    with open(meta_path) as f:
                        meta = json.load(f)
                    lines.append(f"  {entry.name}: {meta.get('pdf_url', 'unknown')} "
                                 f"({meta.get('timestamp', 'unknown')})")
                else:
                    lines.append(f"  {entry.name}: (no metadata)")
        return "\n".join(lines)
