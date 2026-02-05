"""
Durable Agent Loop Workflow - OpenAI Agents SDK Implementation

This implementation uses the OpenAI Agents SDK with Temporal integration,
resulting in dramatically simpler code compared to manual orchestration.

Key simplifications:
- Runner.run() handles the agent loop automatically
- Automatic conversation memory (no manual history tracking)
- Tools defined declaratively (activities and Nexus operations)
- SDK handles tool routing and execution
- Individual Nexus operations (idiomatic Temporal Nexus)
"""
from collections import deque
from dataclasses import dataclass
from datetime import timedelta
from typing import Deque, Optional

from temporalio import workflow

# Pass through llm_client module (uses os.getenv which is deterministic for workflow execution)
with workflow.unsafe.imports_passed_through():
    from app import llm_client

from temporalio.contrib.openai_agents.workflow import (
    activity_as_tool,
    nexus_operation_as_tool,
)
from agents import Runner

from app.activities import AgentActivities
from app.it_service import ITService
from app.finance_service import FinanceService
from app.shared import ENDPOINT_IT, ENDPOINT_FINANCE


@dataclass
class AgentInput:
    initial_prompt: str = ""


@workflow.defn
class DurableAgentWorkflow:
    """
    Durable Agent using OpenAI Agents SDK.

    Uses idiomatic Temporal Nexus with individual operations per tool.
    Each remote tool is its own Nexus operation with explicit types.
    """

    def __init__(self) -> None:
        self.message_queue: Deque[str] = deque()
        self.pending_response: Optional[str] = None
        self.chat_ended: bool = False

    @workflow.run
    async def run(self, input: AgentInput) -> str:
        workflow.logger.info("Starting DurableAgentWorkflow with OpenAI Agents SDK")

        # Build instructions
        instructions = """You are a helpful AI agent with access to various tools.

LOCAL TOOLS:
- calculator: Evaluate mathematical expressions (e.g., "2 + 2", "15 * 23")
- weather: Get weather information for cities

REMOTE TOOLS (IT Namespace):
- jira_metrics: Get JIRA project metrics and statistics (requires project parameter)
- get_ip: Get current IP address (no parameters)

REMOTE TOOLS (Finance Namespace):
- stock_price: Get stock price for a ticker symbol (requires ticker parameter)
- calculate_roi: Calculate return on investment (requires principal, rate, and years parameters)

Use the appropriate tool to help the user. Be concise and helpful in your responses.

IMPORTANT: Respond in plain text only. Do not use LaTeX, MathJax, or any mathematical notation formatting like \\( \\), \\[ \\], or \\times. Just use regular text and symbols."""

        # Build tools list
        tools = [
                # Local tools (activities)
                activity_as_tool(
                    AgentActivities.calculator,
                    start_to_close_timeout=timedelta(seconds=30),
                ),
                activity_as_tool(
                    AgentActivities.weather,
                    start_to_close_timeout=timedelta(seconds=30),
                ),

                # Remote tools (Nexus operations) - IT namespace
                nexus_operation_as_tool(
                    ITService.jira_metrics,
                    service=ITService,
                    endpoint=ENDPOINT_IT,
                ),
                nexus_operation_as_tool(
                    ITService.get_ip,
                    service=ITService,
                    endpoint=ENDPOINT_IT,
                ),

                # Remote tools (Nexus operations) - Finance namespace
                nexus_operation_as_tool(
                    FinanceService.stock_price,
                    service=FinanceService,
                    endpoint=ENDPOINT_FINANCE,
                ),
                nexus_operation_as_tool(
                    FinanceService.calculate_roi,
                    service=FinanceService,
                    endpoint=ENDPOINT_FINANCE,
                ),
        ]

        # Create agent with LLM client
        agent = llm_client.create_agent(
            instructions=instructions,
            tools=tools,
        )

        # Handle initial prompt if provided
        if input.initial_prompt:
            self.message_queue.append(input.initial_prompt)

        # Multi-turn conversation loop
        while not self.chat_ended:
            # Wait for a message or end signal
            await workflow.wait_condition(
                lambda: self.message_queue or self.chat_ended
            )

            if self.chat_ended:
                break

            # Process message
            message = self.message_queue.popleft()
            workflow.logger.info(f"Processing message: {message}")

            # Run agent - SDK handles everything!
            result = await Runner.run(agent, input=message)

            # Store response for client
            self.pending_response = result.final_output
            workflow.logger.info(f"Agent response ready: {result.final_output}")

        workflow.logger.info("Chat ended")
        return "Conversation ended"

    # -------------------------------------------------------------------------
    # MULTI-TURN INTERACTION: Update + Signal pattern
    # -------------------------------------------------------------------------

    @workflow.update
    async def send_message(self, message: str) -> str:
        """
        Send a message and wait for response (blocking).

        Uses Temporal Update pattern - blocks until response is ready.
        """
        if self.chat_ended:
            return "[Chat has ended]"

        workflow.logger.info(f"Received message via update: {message}")

        # Add message to queue
        self.message_queue.append(message)

        # Wait for agent to process and respond
        await workflow.wait_condition(lambda: self.pending_response is not None)

        # Get and clear response
        response = self.pending_response
        self.pending_response = None
        return response

    @workflow.signal
    async def end_chat(self) -> None:
        """Signal to end the conversation gracefully"""
        workflow.logger.info("Received end_chat signal")
        self.chat_ended = True
