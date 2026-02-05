"""
LLM Client

Centralizes all LLM-related logic including Agent initialization.
Configure via LLM_MODEL environment variable.

NOTE: Agent creation happens in workflows (deterministic).
Agent execution via Runner.run() must happen in activities (non-deterministic).
"""
import os
from typing import List, Optional

from agents import Agent

# Read model at module import time (outside workflow sandbox)
# Use LiteLLM provider format: provider/model-name
_DEFAULT_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")


def create_agent(
    instructions: str,
    tools: List,
    mcp_servers: Optional[List] = None,
    name: str = "Durable Agent",
    model: str | None = None,
) -> Agent:
    """
    Create an OpenAI Agent with specified configuration.

    Args:
        instructions: System prompt for the agent
        tools: List of tools (activities)
        mcp_servers: List of MCP server references (optional)
        name: Agent name
        model: Model ID in LiteLLM format (provider/model-name, defaults to openai/gpt-4o-mini)

    Returns:
        Configured Agent instance
    """
    model = model or _DEFAULT_MODEL

    return Agent(
        name=name,
        model=model,
        instructions=instructions,
        tools=tools,
        mcp_servers=mcp_servers or [],
    )

