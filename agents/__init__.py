"""
Multi-agent architecture for Research2Repo.

Provides an orchestrator that coordinates specialized agents through
the full paper-to-repository pipeline.
"""

from agents.orchestrator import AgentOrchestrator

__all__ = ["AgentOrchestrator"]
