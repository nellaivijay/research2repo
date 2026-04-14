"""
ExecutionSandbox — Docker-based (or local) execution sandbox for testing
generated repositories.

Builds a Docker image from the generated repo, runs the entrypoint with
a configurable timeout, captures stdout/stderr, and classifies errors.
Falls back to direct subprocess execution when Docker is unavailable
or disabled.
"""

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional


# Pre-compiled error-classification patterns (ordered most → least specific)
_ERROR_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"ModuleNotFoundError",  re.IGNORECASE), "ModuleNotFoundError"),
    (re.compile(r"ImportError",          re.IGNORECASE), "ImportError"),
    (re.compile(r"SyntaxError",          re.IGNORECASE), "SyntaxError"),
    (re.compile(r"IndentationError",     re.IGNORECASE), "IndentationError"),
    (re.compile(r"NameError",            re.IGNORECASE), "NameError"),
    (re.compile(r"TypeError",            re.IGNORECASE), "TypeError"),
    (re.compile(r"ValueError",           re.IGNORECASE), "ValueError"),
    (re.compile(r"AttributeError",       re.IGNORECASE), "AttributeError"),
    (re.compile(r"KeyError",             re.IGNORECASE), "KeyError"),
    (re.compile(r"IndexError",           re.IGNORECASE), "IndexError"),
    (re.compile(r"FileNotFoundError",    re.IGNORECASE), "FileNotFoundError"),
    (re.compile(r"ZeroDivisionError",    re.IGNORECASE), "ZeroDivisionError"),
    (re.compile(r"RuntimeError",         re.IGNORECASE), "RuntimeError"),
    (re.compile(r"cuda.*out of memory",  re.IGNORECASE), "CudaOOMError"),
    (re.compile(r"OOM",                  re.IGNORECASE), "CudaOOMError"),
    (re.compile(r"AssertionError",       re.IGNORECASE), "AssertionError"),
    (re.compile(r"NotImplementedError",  re.IGNORECASE), "NotImplementedError"),
    (re.compile(r"PermissionError",      re.IGNORECASE), "PermissionError"),
    (re.compile(r"OSError",              re.IGNORECASE), "OSError"),
    (re.compile(r"Traceback",            re.IGNORECASE), "UnclassifiedError"),
]


@dataclass
class ExecutionResult:
    """Outcome of running a generated repository's entrypoint."""
    success: bool = False
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    duration_seconds: float = 0.0
    error_type: str = ""           # empty if success, else "ImportError", "RuntimeError", etc.
    modified_files: list[str] = field(default_factory=list)


class ExecutionSandbox:
    """
    Sandbox for executing generated ML repositories.

    Supports two modes:
      - **Docker** (default): builds an isolated image and runs
        the entrypoint inside a container.
      - **Local**: runs the entrypoint directly via ``subprocess``.

    Args:
        use_docker: Whether to use Docker isolation (default ``True``).
        timeout: Maximum execution time in seconds (default 300).
        gpu: If ``True``, passes ``--gpus all`` to ``docker run``.
    """

    def __init__(
        self,
        use_docker: bool = True,
        timeout: int = 300,
        gpu: bool = False,
    ) -> None:
        self.use_docker = use_docker
        self.timeout = timeout
        self.gpu = gpu

        # Verify Docker is available if requested
        if self.use_docker and not shutil.which("docker"):
            print("[ExecutionSandbox] Docker not found on PATH; falling back to local execution.")
            self.use_docker = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        repo_dir: str,
        entrypoint: str = "train.py",
        args: Optional[list[str]] = None,
    ) -> ExecutionResult:
        """
        Execute the generated repository's entrypoint.

        Args:
            repo_dir: Path to the generated repository root.
            entrypoint: Script to run (relative to *repo_dir*).
            args: Extra CLI arguments to pass to the entrypoint.

        Returns:
            :class:`ExecutionResult` capturing success/failure, output,
            timing, and error classification.
        """
        args = args or []
        repo_dir = os.path.abspath(repo_dir)

        if not os.path.isdir(repo_dir):
            return ExecutionResult(
                success=False,
                stderr=f"Repository directory not found: {repo_dir}",
                exit_code=1,
                error_type="FileNotFoundError",
            )

        entrypoint_path = os.path.join(repo_dir, entrypoint)
        if not os.path.isfile(entrypoint_path):
            return ExecutionResult(
                success=False,
                stderr=f"Entrypoint not found: {entrypoint_path}",
                exit_code=1,
                error_type="FileNotFoundError",
            )

        print(f"[ExecutionSandbox] Executing {entrypoint} in {repo_dir} "
              f"(docker={self.use_docker}, timeout={self.timeout}s)...")

        if self.use_docker:
            try:
                image_tag = self._build_docker_image(repo_dir)
                return self._run_in_docker(image_tag, entrypoint, args, self.timeout)
            except Exception as exc:
                print(f"[ExecutionSandbox] Docker execution failed ({exc}); "
                      "falling back to local execution.")
                return self._run_locally(repo_dir, entrypoint, args, self.timeout)
        else:
            return self._run_locally(repo_dir, entrypoint, args, self.timeout)

    # ------------------------------------------------------------------
    # Docker helpers
    # ------------------------------------------------------------------

    def _build_docker_image(self, repo_dir: str) -> str:
        """Build a Docker image from the repository.

        Generates a ``Dockerfile`` if one does not already exist, then
        runs ``docker build`` and returns the image tag.
        """
        dockerfile_path = os.path.join(repo_dir, "Dockerfile")
        if not os.path.isfile(dockerfile_path):
            print("[ExecutionSandbox] No Dockerfile found; generating one...")
            self._generate_dockerfile(repo_dir)

        tag = f"r2r-sandbox:{os.path.basename(repo_dir).lower()}"
        print(f"[ExecutionSandbox] Building Docker image '{tag}'...")

        result = subprocess.run(
            ["docker", "build", "-t", tag, "."],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min build timeout
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Docker build failed (exit {result.returncode}):\n{result.stderr[:2000]}"
            )

        print(f"[ExecutionSandbox] Docker image '{tag}' built successfully.")
        return tag

    def _generate_dockerfile(self, repo_dir: str) -> str:
        """Generate a basic Dockerfile for the repository.

        Uses ``python:3.10-slim`` as the base image.  If a
        ``requirements.txt`` exists, it is pip-installed.

        Returns:
            Path to the generated Dockerfile.
        """
        has_requirements = os.path.isfile(os.path.join(repo_dir, "requirements.txt"))

        lines = [
            "FROM python:3.10-slim",
            "",
            "WORKDIR /app",
            "",
            "COPY . /app",
            "",
        ]

        if has_requirements:
            lines += [
                "RUN pip install --no-cache-dir -r requirements.txt",
                "",
            ]

        lines += [
            'CMD ["python", "train.py"]',
            "",
        ]

        dockerfile_path = os.path.join(repo_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write("\n".join(lines))

        print(f"[ExecutionSandbox] Generated Dockerfile at {dockerfile_path}")
        return dockerfile_path

    def _run_in_docker(
        self,
        image_tag: str,
        entrypoint: str,
        args: list[str],
        timeout: int,
    ) -> ExecutionResult:
        """Run the entrypoint inside a Docker container.

        Uses ``docker run --rm`` with an optional GPU flag.
        """
        cmd = ["docker", "run", "--rm"]

        if self.gpu:
            cmd += ["--gpus", "all"]

        # Memory / CPU limits for safety
        cmd += ["--memory", "8g", "--cpus", "4"]

        cmd += [image_tag, "python", entrypoint] + args

        print(f"[ExecutionSandbox] Running: {' '.join(cmd)}")

        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = time.monotonic() - start

            success = proc.returncode == 0
            error_type = "" if success else self._classify_error(proc.stderr)

            result = ExecutionResult(
                success=success,
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
                duration_seconds=round(duration, 2),
                error_type=error_type,
                modified_files=[],
            )

        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start
            # Kill the timed-out container
            result = ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds.",
                exit_code=-1,
                duration_seconds=round(duration, 2),
                error_type="TimeoutError",
                modified_files=[],
            )

        status = "SUCCESS" if result.success else f"FAILED ({result.error_type})"
        print(f"[ExecutionSandbox] Docker execution {status} "
              f"in {result.duration_seconds:.1f}s (exit code {result.exit_code}).")
        return result

    # ------------------------------------------------------------------
    # Local execution
    # ------------------------------------------------------------------

    def _run_locally(
        self,
        repo_dir: str,
        entrypoint: str,
        args: list[str],
        timeout: int,
    ) -> ExecutionResult:
        """Run the entrypoint directly via subprocess.

        Captures stdout/stderr, timing, and exit code.
        Detects files modified during execution.
        """
        cmd = ["python", entrypoint] + args

        print(f"[ExecutionSandbox] Running locally: {' '.join(cmd)} (cwd={repo_dir})")

        # Snapshot file modification times before execution
        pre_mtimes = self._snapshot_mtimes(repo_dir)

        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = time.monotonic() - start

            success = proc.returncode == 0
            error_type = "" if success else self._classify_error(proc.stderr)

            # Detect modified files
            post_mtimes = self._snapshot_mtimes(repo_dir)
            modified = [
                f for f, mtime in post_mtimes.items()
                if f not in pre_mtimes or pre_mtimes[f] < mtime
            ]

            result = ExecutionResult(
                success=success,
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
                duration_seconds=round(duration, 2),
                error_type=error_type,
                modified_files=modified,
            )

        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start
            result = ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds.",
                exit_code=-1,
                duration_seconds=round(duration, 2),
                error_type="TimeoutError",
                modified_files=[],
            )

        status = "SUCCESS" if result.success else f"FAILED ({result.error_type})"
        print(f"[ExecutionSandbox] Local execution {status} "
              f"in {result.duration_seconds:.1f}s (exit code {result.exit_code}).")
        return result

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _classify_error(self, stderr: str) -> str:
        """Classify a Python error from stderr into a category.

        Returns the most specific Python exception class name found, or
        ``"UnknownError"`` if no recognisable pattern is matched.
        """
        for compiled_re, error_name in _ERROR_PATTERNS:
            if compiled_re.search(stderr):
                return error_name

        return "UnknownError" if stderr.strip() else ""

    @staticmethod
    def _snapshot_mtimes(directory: str) -> dict[str, float]:
        """Snapshot modification times for all files in *directory*."""
        mtimes: dict[str, float] = {}
        for root, _dirs, files in os.walk(directory):
            for fname in files:
                full_path = os.path.join(root, fname)
                try:
                    mtimes[os.path.relpath(full_path, directory)] = os.path.getmtime(full_path)
                except OSError:
                    pass
        return mtimes
