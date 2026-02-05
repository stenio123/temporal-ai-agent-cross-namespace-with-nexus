"""
Workflow Starter - Client with OpenAI Agents SDK

Interactive CLI for multi-turn conversations with the durable agent.
The agent loop runs in the workflow with OpenAI Agents SDK handling orchestration.
"""
import asyncio
import uuid

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from app.workflow import AgentInput, DurableAgentWorkflow


async def main():
    # Connect to Temporal with OpenAI Agents SDK plugin
    # Plugin ensures serialization compatibility with the worker
    print("Connecting to Temporal server...")
    client = await Client.connect(
        "localhost:7233",
        plugins=[OpenAIAgentsPlugin()],
    )
    print("✓ Connected\n")

    workflow_id = f"agent-{uuid.uuid4().hex[:8]}"

    # Start workflow
    print(f"Starting workflow: {workflow_id}")
    handle = await client.start_workflow(
        DurableAgentWorkflow.run,
        AgentInput(),
        id=workflow_id,
        task_queue="orchestrator-queue",
    )
    print("✓ Workflow started\n")
    print("=" * 60)
    print("Interactive AI Agent with OpenAI Agents SDK")
    print("=" * 60)
    print("")
    print("The agent has access to:")
    print("  • Local tools: calculator, weather")
    print("  • Remote tools: IT namespace (jira_metrics, get_ip)")
    print("  • Remote tools: Finance namespace (stock_price, calculate_roi)")
    print("")
    print("Type 'quit' to exit.\n")

    try:
        while True:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "bye"):
                try:
                    await handle.signal(DurableAgentWorkflow.end_chat)
                except Exception:
                    pass
                print("Ending chat...")
                break

            # Send message and wait for response
            # Uses Temporal Update pattern for blocking request/response
            # https://temporal.io/blog/announcing-a-new-operation-workflow-update
            try:
                response = await handle.execute_update(
                    DurableAgentWorkflow.send_message,
                    user_input
                )
                print(f"Agent: {response}\n")
            except Exception as e:
                print(f"\n[Unexpected Error]: {e}")
                break

    except KeyboardInterrupt:
        print("\nInterrupted")
        await handle.signal(DurableAgentWorkflow.end_chat)

    # Get final result
    try:
        result = await asyncio.wait_for(handle.result(), timeout=5.0)
        print("\n=== Conversation Ended ===")
        print(result)
    except asyncio.TimeoutError:
        print("Workflow still running...")


if __name__ == "__main__":
    asyncio.run(main())
