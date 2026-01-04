"""
LLM Client

Wraps LiteLLM to support multiple providers (OpenAI, Anthropic, etc.)
Configure via LLM_MODEL environment variable.

NOTE: This must ONLY be called from Activities, never from Workflows.
LLM responses are non-deterministic and must be captured in event history.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from litellm import completion

load_dotenv(dotenv_path=Path(__file__).parent / '.env')


def call_llm(messages: List[Dict[str, str]], model: str | None = None) -> Dict[str, Any]:
    """
    Call LLM with messages, returning parsed JSON.
    
    Args:
        messages: List of {"role": "...", "content": "..."} dicts
        model: Model ID (defaults to LLM_MODEL env var or gpt-4o-mini)
    
    Returns:
        Parsed JSON dict with action, tool, args, and/or message fields
    """
    model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    response = completion(
        model=model,
        messages=messages,
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    
    return json.loads(response.choices[0].message.content)