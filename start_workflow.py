"""
Workflow Starter - Client

Note - the while loop is only for client interaction. 
The durable agent workflow is running in workflow.py.
"""
import asyncio
import uuid

from temporalio.client import Client

from workflow import AgentInput, DurableAgentWorkflow


async def main():
    # Connect to Temporal
    print("Connecting to Temporal server...")
    client = await Client.connect("localhost:7233")
    print("✓ Connected\n")
    
    workflow_id = f"agent-{uuid.uuid4().hex[:8]}"
    
    # Start workflow
    print(f"Starting workflow: {workflow_id}")
    handle = await client.start_workflow(
        DurableAgentWorkflow.run,
        AgentInput(),
        id=workflow_id,
        task_queue="durable-agent-queue",
    )
    print("✓ Workflow started\n")
    print("Type 'quit' to exit.\n")
    print("Enter your message to the AI agent here. You can ask any questions or use tools available: calculator, weather.\n")
    
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
            # We could instead use a loop with queue, however update more efficient
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
        print("\n=== Conversation Transcript ===")
        print(result)
    except asyncio.TimeoutError:
        print("Workflow still running...")


if __name__ == "__main__":
    asyncio.run(main())