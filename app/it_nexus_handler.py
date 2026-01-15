import uuid
from dataclasses import dataclass
from temporalio import nexus, workflow
import nexusrpc

# We import these to use them in the handler
with workflow.unsafe.imports_passed_through():
    from workflow import DurableAgentWorkflow, AgentInput

@dataclass
class ToolOperationInput:
    """The input sent from a remote namespace to this Nexus endpoint"""
    prompt: str

@dataclass
class ToolOperationOutput:
    """The final result returned across the Nexus bridge"""
    result: str

@nexusrpc.handler.service_handler(service="mcp-gateway")
class AgentNexusHandler:
    """
    This handler receives Nexus calls and 'bridges' them 
    into a local DurableAgentWorkflow execution.
    """

    @nexus.workflow_run_operation
    async def execute_agent_tool(
        self, 
        ctx: nexus.WorkflowRunOperationContext, 
        input: ToolOperationInput
    ) -> nexus.WorkflowHandle[ToolOperationOutput]:
        """
        Starts the DurableAgentWorkflow as an asynchronous Nexus operation.
        Temporal handles the 'callback' to the caller once this workflow completes.
        """
        
        # We wrap the Nexus input into the format our workflow expects
        agent_input = AgentInput(initial_prompt=input.prompt)

        # Start the workflow. The Nexus Machinery will track this 
        # and notify the caller when it finishes.
        return await ctx.start_workflow(
            DurableAgentWorkflow.run,
            agent_input,
            id=f"nexus-agent-{uuid.uuid4()}",
            task_queue="it-task-queue" # Ensure this matches your worker's queue
        )