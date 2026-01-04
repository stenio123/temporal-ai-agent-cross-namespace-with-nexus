"""
Mock LLM Client for Benchmarking

Identical interface to llm_client.py but returns instant responses.
Used to isolate Temporal overhead from LLM latency in benchmarks.

Usage: 
  Copy this file to llm_client.py when running latency benchmarks,
  then restore the original llm_client.py after.
"""
from typing import Any, Dict, List


def call_llm(messages: List[Dict[str, str]], model: str | None = None) -> Dict[str, Any]:
    """
    Mock LLM call - returns instant structured response.
    
    Same signature as the real llm_client.call_llm()
    """
    return {
        "action": "respond",
        "tool": None,
        "args": {},
        "message": "Mock response"
    }