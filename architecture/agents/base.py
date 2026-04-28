"""
Base agent abstraction for the Research2Repo multi-agent system.

Every specialised agent inherits from :class:`BaseAgent`, which provides:
  - A name identifier and an associated LLM provider.
  - A lightweight ``communicate`` method for agent-to-agent message passing.
  - A ``log`` helper that prefixes output with the agent's name.

Concrete agents override :meth:`execute` to perform their stage-specific
work (analysis, planning, coding, validation, …).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from providers import get_provider
from providers.base import BaseProvider


# ---------------------------------------------------------------------------
# Message dataclass
# ---------------------------------------------------------------------------

@dataclass
class AgentMessage:
    """A simple message exchanged between agents.

    Attributes:
        role: Sender role / identifier (e.g. ``"planner"``, ``"coder"``).
        content: The message body — free-form text or serialised data.
        metadata: Arbitrary key-value pairs for structured side-channel info
                  (e.g. ``{"stage": "planning", "iteration": 2}``).
    """

    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract base agent
# ---------------------------------------------------------------------------

class BaseAgent(ABC):
    """Abstract base class for all pipeline agents.

    Every agent wraps a single pipeline module (``PaperAnalyzer``,
    ``DecomposedPlanner``, ``CodeSynthesizer``, …) and exposes a
    uniform :meth:`execute` interface.

    Args:
        name: Human-readable agent name used in log output.
        provider: LLM provider instance.  When *None* the best
                  available provider is auto-detected via
                  :func:`providers.get_provider`.
    """

    def __init__(
        self,
        name: str,
        provider: Optional[BaseProvider] = None,
    ) -> None:
        self._name = name
        self._provider = provider or get_provider()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Return the human-readable agent name."""
        return self._name

    @property
    def provider(self) -> BaseProvider:
        """Return the underlying LLM provider."""
        return self._provider

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """Run the agent's primary action.

        Subclasses must implement this.  Keyword arguments and return
        types vary per agent — the orchestrator is responsible for
        wiring the right data between agents.
        """
        ...

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def log(self, message: str) -> None:
        """Print a log line prefixed with the agent name.

        Example output::

            [PlannerAgent] Decomposing paper into 12 tasks …
        """
        print(f"[{self._name}] {message}")

    def communicate(
        self,
        target_agent: BaseAgent,
        message: AgentMessage,
    ) -> AgentMessage:
        """Send a message to *target_agent* and return its reply.

        This is intentionally simple — direct, synchronous, in-process
        message passing.  The target agent receives the message and
        returns an ``AgentMessage`` acknowledgement.

        In a future iteration this could be extended with message queues,
        async I/O, or an event bus, but the synchronous version is
        sufficient for the current single-process pipeline.

        Args:
            target_agent: The agent to deliver the message to.
            message: The outgoing message.

        Returns:
            An ``AgentMessage`` from the target agent confirming receipt.
        """
        self.log(f"→ sending message to {target_agent.name}")
        target_agent.log(f"← received message from {self._name}")
        return AgentMessage(
            role=target_agent.name,
            content="acknowledged",
            metadata={
                "from": self._name,
                "original_content": message.content,
            },
        )

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{self.__class__.__name__} name={self._name!r}>"
