"""
Durable Agent Loop Workflow - OpenAI Agents SDK with Native MCP Integration

This implementation uses the OpenAI Agents SDK with native MCP protocol support.
MCP servers are Temporal clients that start durable workflows on dedicated task queues.

Key features:
- Runner.run() handles the agent loop automatically
- Automatic conversation memory (no manual history tracking)
- Local tools defined declaratively (activities)
- MCP tools accessed via native SDK protocol (Finance and IT services)
- SDK automatically discovers and exposes MCP server tools
- Each MCP server independently manages its durable workflows
"""
from collections import deque
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Deque, Optional
import warnings

from temporalio import workflow

# Pass through llm_client module (uses os.getenv which is deterministic for workflow execution)
with workflow.unsafe.imports_passed_through():
    from app import llm_client

from temporalio.contrib.openai_agents.workflow import activity_as_tool, stateless_mcp_server
from agents import Runner

import app.activities as activities
from app.shared import MCP_SERVERS

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="temporalio.worker.workflow_sandbox._importer")
warnings.filterwarnings("ignore", message="Current span is not a FunctionSpanData")

@dataclass
class AgentInput:
    initial_prompt: str = ""


@workflow.defn
class DurableAgentWorkflow:
    """
    Durable Agent using OpenAI Agents SDK with native MCP protocol integration.

    MCP tools are automatically discovered and executed via the SDK's native MCP support.
    Each MCP server is a Temporal client that starts durable workflows.
    The SDK handles tool discovery, parameter validation, and execution transparently.
    """

    def __init__(self) -> None:
        self.message_queue: Deque[str] = deque()
        self.pending_response: Optional[str] = None
        self.chat_ended: bool = False

    @workflow.run
    async def run(self, input: AgentInput) -> str:
        workflow.logger.info("Starting DurableAgentWorkflow with MCP integration")

        # Build instructions dynamically based on available tools
        mcp_descriptions = "\n".join([
            f"- {server['name']}: {server['description']}"
            for server in MCP_SERVERS
        ])

        instructions = f"""You are a helpful AI agent with access to both local and remote tools.

LOCAL TOOLS:
- calculator: Evaluate mathematical expressions (e.g., "2 + 2", "15 * 23")
- weather: Get weather information for cities

MCP TOOLS:
{mcp_descriptions}

Use the appropriate tools to help users with their requests. Be concise and helpful in your responses.

IMPORTANT: Respond in plain text only. Do not use LaTeX, MathJax, or any mathematical notation formatting like \\( \\), \\[ \\], or \\times. Just use regular text and symbols."""

        # Build tools list (local activities)
        tools = [
            activity_as_tool(
                activities.calculator,
                start_to_close_timeout=timedelta(seconds=30),
            ),
            activity_as_tool(
                activities.weather,
                start_to_close_timeout=timedelta(seconds=30),
            ),
        ]

        # MCP servers are provided by the OpenAI Agents SDK plugin
        # configured in the worker
        mcp_servers = [
            stateless_mcp_server(server["name"])
            for server in MCP_SERVERS
        ]

        # Create agent with LLM client
        agent = llm_client.create_agent(
            instructions=instructions,
            tools=tools,
            mcp_servers=mcp_servers,
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
