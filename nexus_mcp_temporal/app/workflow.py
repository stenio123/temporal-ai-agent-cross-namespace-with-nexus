"""
Durable Agent Loop Workflow - Nexus-MCP Bridge Implementation

This implementation uses the nexus-mcp-python bridge pattern with OpenAI Agents SDK:
- WorkflowTransport connects to MCP Gateway from within workflow
- MCP Gateway exposes Nexus operations as MCP tools
- Enables bidirectional: External MCP clients → Gateway → Nexus
                          AND: Workflow → Gateway → Nexus

Key features:
- Runner.run() handles the agent loop automatically
- Automatic conversation memory (no manual history tracking)
- Local tools defined as activities
- Remote tools accessed via MCP Gateway (which calls Nexus)
- Universal tool registry pattern
"""
from collections import deque
from dataclasses import dataclass
from datetime import timedelta
from typing import Deque, Optional

from temporalio import workflow

# Pass through modules that use os.getenv (deterministic for workflow execution)
with workflow.unsafe.imports_passed_through():
    from app import llm_client
    # WorkflowTransport needs to be imported in unsafe block
    from nexusmcp import WorkflowTransport

from temporalio.contrib.openai_agents.workflow import activity_as_tool
from agents import Runner

from app.activities import AgentActivities
from app.mcp_helpers import create_mcp_gateway_tool_from_schema, discover_tools_from_endpoint
from app.shared import ENDPOINT_IT, ENDPOINT_FINANCE


@dataclass
class AgentInput:
    initial_prompt: str = ""


@workflow.defn(sandboxed=False)  # Required for WorkflowTransport
class DurableAgentWorkflow:
    """
    Durable Agent using OpenAI Agents SDK with Nexus-MCP bridge.

    This workflow connects to an MCP Gateway (InboundGateway) which exposes
    Nexus operations as MCP tools. The workflow uses WorkflowTransport to
    call these tools.

    Architecture:
    Workflow → WorkflowTransport → MCP Gateway → Nexus Operations → Workers
    """

    def __init__(self) -> None:
        self.message_queue: Deque[str] = deque()
        self.pending_response: Optional[str] = None
        self.chat_ended: bool = False
        # Track which endpoints need tool refresh
        self.refresh_flags: dict[str, bool] = {"IT": False, "Finance": False}

    @workflow.run
    async def run(self, input: AgentInput) -> str:
        workflow.logger.info("Starting DurableAgentWorkflow with Nexus-MCP bridge")

        # Build instructions - mention dynamic discovery
        self.instructions = """You are a helpful AI agent with access to various tools.

You have LOCAL TOOLS (Activities) and REMOTE TOOLS (via MCP Gateway).

Local tools are directly available as workflow activities:
- calculator: Evaluate mathematical expressions
- weather: Get weather information for cities

Remote tools are dynamically discovered from multiple namespaces via MCP Gateway:
- Tools are discovered at workflow startup from IT and Finance namespaces
- Each tool is backed by durable Temporal workflows for reliability
- All remote tool calls use deterministic Nexus RPC (tracked in workflow history)

Use the appropriate tool to help the user. Be concise and helpful in your responses.

IMPORTANT: Respond in plain text only. Do not use LaTeX, MathJax, or any mathematical notation formatting like \\( \\), \\[ \\], or \\times. Just use regular text and symbols."""

        # Build local tools (activities)
        self.local_tools = [
            activity_as_tool(
                AgentActivities.calculator,
                start_to_close_timeout=timedelta(seconds=30),
            ),
            activity_as_tool(
                AgentActivities.weather,
                start_to_close_timeout=timedelta(seconds=30),
            ),
        ]

        # Connect to MCP Gateway via WorkflowTransport
        # This allows the workflow to call MCP tools exposed by the gateway
        workflow.logger.info("Connecting to MCP Gateway via WorkflowTransport...")

        if WorkflowTransport is None:
            raise RuntimeError(
                "nexusmcp.WorkflowTransport not available. "
                "Install nexus-mcp: uv add 'nexus-mcp @ git+https://github.com/bergundy/nexus-mcp-python.git@main'"
            )

        # Create WorkflowTransport for IT endpoint
        self.it_transport = WorkflowTransport(ENDPOINT_IT)

        # Create WorkflowTransport for Finance endpoint
        self.finance_transport = WorkflowTransport(ENDPOINT_FINANCE)

        # DYNAMIC TOOL DISCOVERY: Discover tools from each endpoint
        # This is deterministic because it happens once during workflow init
        # and uses Nexus RPC (recorded in workflow history)
        workflow.logger.info("Dynamically discovering tools from MCP Gateway...")

        # Discover IT tools
        it_mcp_tools = await discover_tools_from_endpoint(self.it_transport, "IT")

        # Discover Finance tools
        finance_mcp_tools = await discover_tools_from_endpoint(self.finance_transport, "Finance")

        # Create MCP Gateway tool wrappers from dynamically discovered tools
        workflow.logger.info("Creating MCP Gateway tool wrappers from discovered tools...")

        # Convert discovered IT tools to SDK FunctionTools
        it_tools = [
            create_mcp_gateway_tool_from_schema(mcp_tool, self.it_transport)
            for mcp_tool in it_mcp_tools
        ]

        # Convert discovered Finance tools to SDK FunctionTools
        finance_tools = [
            create_mcp_gateway_tool_from_schema(mcp_tool, self.finance_transport)
            for mcp_tool in finance_mcp_tools
        ]

        # Store remote tools for potential refresh
        self.it_tools = it_tools
        self.finance_tools = finance_tools

        # Combine all tools: local activities + dynamically discovered MCP Gateway tools
        all_tools = self.local_tools + self.it_tools + self.finance_tools

        workflow.logger.info(f"Registered {len(all_tools)} tools: {[t.name for t in all_tools]}")

        # Create agent with LLM client
        agent = llm_client.create_agent(
            instructions=self.instructions,
            tools=all_tools,
        )

        # Handle initial prompt if provided
        if input.initial_prompt:
            self.message_queue.append(input.initial_prompt)

        # Multi-turn conversation loop
        while not self.chat_ended:
            # Wait for a message, end signal, or refresh request
            await workflow.wait_condition(
                lambda: self.message_queue or self.chat_ended or any(self.refresh_flags.values())
            )

            if self.chat_ended:
                break

            # Check if tool refresh is needed
            if self.refresh_flags["IT"]:
                workflow.logger.info("Refreshing IT tools...")
                it_mcp_tools = await discover_tools_from_endpoint(self.it_transport, "IT")
                self.it_tools = [
                    create_mcp_gateway_tool_from_schema(mcp_tool, self.it_transport)
                    for mcp_tool in it_mcp_tools
                ]
                workflow.logger.info(f"IT tools refreshed: {[t.name for t in self.it_tools]}")
                self.refresh_flags["IT"] = False

                # Recreate agent with updated tools
                all_tools = self.local_tools + self.it_tools + self.finance_tools
                agent = llm_client.create_agent(
                    instructions=self.instructions,
                    tools=all_tools,
                )
                workflow.logger.info("Agent recreated with updated IT tools")

            if self.refresh_flags["Finance"]:
                workflow.logger.info("Refreshing Finance tools...")
                finance_mcp_tools = await discover_tools_from_endpoint(self.finance_transport, "Finance")
                self.finance_tools = [
                    create_mcp_gateway_tool_from_schema(mcp_tool, self.finance_transport)
                    for mcp_tool in finance_mcp_tools
                ]
                workflow.logger.info(f"Finance tools refreshed: {[t.name for t in self.finance_tools]}")
                self.refresh_flags["Finance"] = False

                # Recreate agent with updated tools
                all_tools = self.local_tools + self.it_tools + self.finance_tools
                agent = llm_client.create_agent(
                    instructions=self.instructions,
                    tools=all_tools,
                )
                workflow.logger.info("Agent recreated with updated Finance tools")

            # Process message if available
            if not self.message_queue:
                continue

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

    @workflow.signal
    async def refresh_mcp(self, endpoint_name: str) -> None:
        """
        Signal to refresh MCP tools from a specific endpoint.

        Args:
            endpoint_name: Name of the endpoint to refresh ("IT" or "Finance")
        """
        if endpoint_name not in self.refresh_flags:
            workflow.logger.warning(
                f"Unknown endpoint '{endpoint_name}'. Valid options: {list(self.refresh_flags.keys())}"
            )
            return

        workflow.logger.info(f"Received refresh_mcp signal for endpoint: {endpoint_name}")
        self.refresh_flags[endpoint_name] = True
