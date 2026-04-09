"""
DevOpsGenerator — Produces Docker, CI/CD, build, and packaging files
for the generated ML repository.

Creates production-ready infrastructure files that let users immediately
build, train, test, and deploy the generated codebase:

  - ``Dockerfile``              (CPU + GPU variants)
  - ``docker-compose.yml``      (training & inference services)
  - ``Makefile``                (common developer targets)
  - ``.github/workflows/ci.yml`` (GitHub Actions CI)
  - ``setup.py``                (pip-installable package)

Each generator method has a sensible hardcoded template but can
optionally call the LLM for smarter, context-aware generation.
"""

from __future__ import annotations

import textwrap
from typing import Any, Optional

from providers import get_provider
from providers.base import BaseProvider, GenerationConfig


class DevOpsGenerator:
    """Generate DevOps / CI / packaging artefacts for a generated repo.

    Args:
        provider: LLM provider used when smarter, context-aware generation
                  is desired.  Falls back to deterministic templates when
                  *None* or when the LLM call fails.
    """

    def __init__(self, provider: Optional[BaseProvider] = None) -> None:
        self._provider = provider or get_provider()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_all(
        self,
        plan: Any,
        analysis: Any,
        generated_files: dict[str, str],
    ) -> dict[str, str]:
        """Produce every DevOps file and return them as ``path → content``.

        Args:
            plan: ``ArchitecturePlan`` from the architect / planner.
            analysis: ``PaperAnalysis`` from the paper analyser.
            generated_files: Already-generated source files (used to
                             detect language features, frameworks, etc.).

        Returns:
            Dict mapping file paths to their generated content.
        """
        print("  [DevOps] Generating infrastructure files …")

        devops_files: dict[str, str] = {}

        # --- Dockerfile ---
        print("  [DevOps]  → Dockerfile")
        devops_files["Dockerfile"] = self._generate_dockerfile(plan, analysis)

        # --- docker-compose.yml ---
        print("  [DevOps]  → docker-compose.yml")
        devops_files["docker-compose.yml"] = self._generate_docker_compose(plan)

        # --- Makefile ---
        print("  [DevOps]  → Makefile")
        devops_files["Makefile"] = self._generate_makefile(plan)

        # --- GitHub Actions CI ---
        print("  [DevOps]  → .github/workflows/ci.yml")
        devops_files[".github/workflows/ci.yml"] = self._generate_ci_yml(plan)

        # --- setup.py ---
        print("  [DevOps]  → setup.py")
        devops_files["setup.py"] = self._generate_setup_py(plan, analysis)

        print(f"  [DevOps] Done — {len(devops_files)} files generated.")
        return devops_files

    # ------------------------------------------------------------------
    # Dockerfile
    # ------------------------------------------------------------------

    def _generate_dockerfile(self, plan: Any, analysis: Any) -> str:
        """Generate a multi-stage Dockerfile with CPU and GPU variants.

        Uses ``python:3.10-slim`` for the CPU image and
        ``nvidia/cuda:12.1.0-runtime-ubuntu22.04`` for the GPU variant.
        """
        python_version = getattr(plan, "python_version", "3.10")
        training_entry = getattr(plan, "training_entrypoint", "train.py")

        requirements = getattr(plan, "requirements", [])
        needs_gpu = any(
            pkg in requirements
            for pkg in ("torch", "pytorch", "tensorflow", "jax", "cupy")
        )

        # Detect if we need extra system packages
        system_deps = ["git", "build-essential"]
        if any(pkg.startswith("opencv") for pkg in requirements):
            system_deps.append("libgl1-mesa-glx")
            system_deps.append("libglib2.0-0")

        sys_install = " ".join(system_deps)

        lines = [
            f"# ── CPU image ────────────────────────────────────────────",
            f"FROM python:{python_version}-slim AS cpu",
            f"",
            f"LABEL maintainer=\"Research2Repo\"",
            f"LABEL description=\"{getattr(analysis, 'title', 'Generated ML Repo')}\"",
            f"",
            f"ENV PYTHONDONTWRITEBYTECODE=1 \\",
            f"    PYTHONUNBUFFERED=1",
            f"",
            f"RUN apt-get update && apt-get install -y --no-install-recommends \\",
            f"        {sys_install} \\",
            f"    && rm -rf /var/lib/apt/lists/*",
            f"",
            f"WORKDIR /app",
            f"",
            f"COPY requirements.txt .",
            f"RUN pip install --no-cache-dir -r requirements.txt",
            f"",
            f"COPY . .",
            f"",
            f"CMD [\"python\", \"{training_entry}\"]",
        ]

        if needs_gpu:
            lines += [
                f"",
                f"# ── GPU image ────────────────────────────────────────────",
                f"FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04 AS gpu",
                f"",
                f"ENV PYTHONDONTWRITEBYTECODE=1 \\",
                f"    PYTHONUNBUFFERED=1 \\",
                f"    DEBIAN_FRONTEND=noninteractive",
                f"",
                f"RUN apt-get update && apt-get install -y --no-install-recommends \\",
                f"        python{python_version} python3-pip {sys_install} \\",
                f"    && ln -sf /usr/bin/python{python_version} /usr/bin/python \\",
                f"    && rm -rf /var/lib/apt/lists/*",
                f"",
                f"WORKDIR /app",
                f"",
                f"COPY requirements.txt .",
                f"RUN pip install --no-cache-dir -r requirements.txt",
                f"",
                f"COPY . .",
                f"",
                f"CMD [\"python\", \"{training_entry}\"]",
            ]

        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # docker-compose.yml
    # ------------------------------------------------------------------

    def _generate_docker_compose(self, plan: Any) -> str:
        """Generate ``docker-compose.yml`` with training and inference services."""
        training_entry = getattr(plan, "training_entrypoint", "train.py")
        inference_entry = getattr(plan, "inference_entrypoint", "inference.py")
        repo_name = getattr(plan, "repo_name", "ml-project")

        requirements = getattr(plan, "requirements", [])
        needs_gpu = any(
            pkg in requirements
            for pkg in ("torch", "pytorch", "tensorflow", "jax", "cupy")
        )

        gpu_block = ""
        if needs_gpu:
            gpu_block = textwrap.dedent("""\
                deploy:
                  resources:
                    reservations:
                      devices:
                        - driver: nvidia
                          count: all
                          capabilities: [gpu]
            """)
            # Indent to match service nesting (6 spaces)
            gpu_block = textwrap.indent(gpu_block, "      ")

        compose = textwrap.dedent(f"""\
            version: "3.8"

            services:
              train:
                build:
                  context: .
                  target: {"gpu" if needs_gpu else "cpu"}
                image: {repo_name}:latest
                container_name: {repo_name}-train
                command: ["python", "{training_entry}"]
                volumes:
                  - ./data:/app/data
                  - ./checkpoints:/app/checkpoints
                  - ./logs:/app/logs
            {gpu_block}
              inference:
                build:
                  context: .
                  target: {"gpu" if needs_gpu else "cpu"}
                image: {repo_name}:latest
                container_name: {repo_name}-inference
                command: ["python", "{inference_entry}"]
                ports:
                  - "8000:8000"
                volumes:
                  - ./checkpoints:/app/checkpoints
            {gpu_block}
        """)

        return compose

    # ------------------------------------------------------------------
    # Makefile
    # ------------------------------------------------------------------

    def _generate_makefile(self, plan: Any) -> str:
        """Generate a ``Makefile`` with common developer targets."""
        training_entry = getattr(plan, "training_entrypoint", "train.py")
        inference_entry = getattr(plan, "inference_entrypoint", "inference.py")
        repo_name = getattr(plan, "repo_name", "ml-project")

        makefile = textwrap.dedent(f"""\
            .PHONY: install train evaluate test lint clean docker-build docker-run help

            PYTHON   ?= python
            PIP      ?= pip
            IMAGE    ?= {repo_name}:latest

            help:  ## Show this help message
            \t@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \\
            \t\tawk 'BEGIN {{FS = ":.*?## "}}; {{printf "  \\033[36m%-15s\\033[0m %s\\n", $$1, $$2}}'

            install:  ## Install Python dependencies
            \t$(PIP) install -r requirements.txt

            train:  ## Run the training entrypoint
            \t$(PYTHON) {training_entry}

            evaluate:  ## Run the inference / evaluation script
            \t$(PYTHON) {inference_entry}

            test:  ## Run the test suite with pytest
            \t$(PYTHON) -m pytest tests/ -v --tb=short

            lint:  ## Run linters (ruff + mypy)
            \t$(PYTHON) -m ruff check .
            \t$(PYTHON) -m mypy --ignore-missing-imports .

            clean:  ## Remove build artefacts and caches
            \trm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
            \trm -rf build dist *.egg-info
            \tfind . -type d -name __pycache__ -exec rm -rf {{}} +

            docker-build:  ## Build the Docker image
            \tdocker build -t $(IMAGE) .

            docker-run:  ## Run training inside Docker
            \tdocker run --rm -v $$(pwd)/data:/app/data -v $$(pwd)/checkpoints:/app/checkpoints $(IMAGE)
        """)

        return makefile

    # ------------------------------------------------------------------
    # GitHub Actions CI
    # ------------------------------------------------------------------

    def _generate_ci_yml(self, plan: Any) -> str:
        """Generate ``.github/workflows/ci.yml`` for GitHub Actions."""
        python_version = getattr(plan, "python_version", "3.10")

        ci = textwrap.dedent(f"""\
            name: CI

            on:
              push:
                branches: [main, master]
              pull_request:
                branches: [main, master]

            permissions:
              contents: read

            jobs:
              test:
                runs-on: ubuntu-latest
                strategy:
                  matrix:
                    python-version: ["{python_version}"]

                steps:
                  - name: Checkout repository
                    uses: actions/checkout@v4

                  - name: Set up Python ${{{{ matrix.python-version }}}}
                    uses: actions/setup-python@v5
                    with:
                      python-version: ${{{{ matrix.python-version }}}}
                      cache: pip

                  - name: Install dependencies
                    run: |
                      python -m pip install --upgrade pip
                      pip install -r requirements.txt
                      pip install pytest ruff mypy

                  - name: Lint with ruff
                    run: ruff check . --output-format=github

                  - name: Type-check with mypy
                    run: mypy --ignore-missing-imports . || true

                  - name: Run tests
                    run: pytest tests/ -v --tb=short
        """)

        return ci

    # ------------------------------------------------------------------
    # setup.py
    # ------------------------------------------------------------------

    def _generate_setup_py(self, plan: Any, analysis: Any) -> str:
        """Generate a basic ``setup.py`` from plan metadata."""
        repo_name = getattr(plan, "repo_name", "ml-project")
        description = getattr(
            plan, "description",
            getattr(analysis, "title", "Generated ML repository"),
        )
        python_version = getattr(plan, "python_version", "3.10")
        requirements = getattr(plan, "requirements", [])

        # Format the requirements list as Python source
        req_lines = ",\n        ".join(f'"{r}"' for r in requirements)

        setup = textwrap.dedent(f"""\
            \"\"\"
            Minimal setup.py for {repo_name}.
            Auto-generated by Research2Repo.
            \"\"\"

            from setuptools import setup, find_packages


            def _read_requirements() -> list[str]:
                \"\"\"Read requirements.txt and return as a list.\"\"\"
                try:
                    with open("requirements.txt", encoding="utf-8") as fh:
                        return [
                            line.strip()
                            for line in fh
                            if line.strip() and not line.startswith("#")
                        ]
                except FileNotFoundError:
                    return []


            setup(
                name="{repo_name}",
                version="0.1.0",
                description="{description}",
                long_description=open("README.md", encoding="utf-8").read()
                if __import__("os").path.exists("README.md")
                else "",
                long_description_content_type="text/markdown",
                author="Research2Repo",
                python_requires=">={python_version}",
                packages=find_packages(exclude=["tests", "tests.*"]),
                install_requires=_read_requirements(),
                extras_require={{
                    "dev": [
                        "pytest>=7.0",
                        "ruff>=0.1",
                        "mypy>=1.0",
                    ],
                }},
                entry_points={{
                    "console_scripts": [
                        "{repo_name}=train:main",
                    ],
                }},
                classifiers=[
                    "Development Status :: 3 - Alpha",
                    "Intended Audience :: Science/Research",
                    "Programming Language :: Python :: {python_version.split('.')[0]}",
                    "Topic :: Scientific/Engineering :: Artificial Intelligence",
                ],
            )
        """)

        return setup

    # ------------------------------------------------------------------
    # Optional LLM-enhanced generation (unused in default mode)
    # ------------------------------------------------------------------

    def _llm_generate(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Attempt LLM-enhanced generation; return *None* on failure.

        This is a utility hook for subclasses or future enhancement.
        The public methods above use deterministic templates by default.
        """
        if self._provider is None:
            return None
        try:
            result = self._provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                config=GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=4096,
                ),
            )
            return result.text.strip()
        except Exception as exc:  # noqa: BLE001
            print(f"  [DevOps] LLM generation failed ({exc}), "
                  "using template fallback.")
            return None
