"""
Activities: Local tool implementations for OpenAI Agents SDK

These are simple tool activities that will be converted to agent tools
using activity_as_tool() helper from temporalio.contrib.openai_agents.

Each activity should:
- Return a string or primitive type (required by OpenAI Agents SDK)
- Be simple and focused on one task
- Handle errors gracefully with descriptive messages
"""
from typing import Any, Dict

from temporalio import activity
from simpleeval import simple_eval


class AgentActivities:
    """Local tool activities for the agent"""

    @activity.defn(name="calculator")
    async def calculator(self, expression: str) -> str:
        """
        Evaluate a mathematical expression and return the result.

        Args:
            expression: A mathematical expression to evaluate (e.g., "2 + 2", "15 * 23")

        Returns:
            The result as a string, or an error message if evaluation fails
        """
        try:
            activity.logger.info(f"Calculating: {expression}")
            result = simple_eval(expression)
            return str(result)
        except Exception as e:
            error_msg = f"Error evaluating expression '{expression}': {e}"
            activity.logger.error(error_msg)
            return error_msg

    @activity.defn(name="weather")
    async def weather(self, city: str) -> str:
        """
        Get weather information for a city (mock implementation).

        Args:
            city: The name of the city

        Returns:
            Weather information as a string
        """
        activity.logger.info(f"Getting weather for: {city}")
        # Mock implementation - replace with real weather API in production
        return f"Weather in {city}: Sunny, 72°F"
