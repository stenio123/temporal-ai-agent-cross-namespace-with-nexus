"""
Durable Agent Loop Workflow

Orchestrates the agent loop with deterministic control flow.
All non-deterministic operations (LLM calls, tools) happen in activities.
"""
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities import AgentActivities, PlanResult, ToolResult


@dataclass
class AgentInput:
    initial_prompt: str = ""


@workflow.defn
class DurableAgentWorkflow:
    """
    Durable Agent Loop.
    
    States:
    - current_message: what we're processing (None = idle)
    - pending_response: result for client (None = not ready)
    - chat_ended: exit flag
    """
    
    def __init__(self) -> None:
        self.current_message: Optional[str] = None
        self.pending_response: Optional[str] = None
        self.chat_ended: bool = False
        
        # Conversation history for LLM context
        self.conversation_history: List[Dict[str, str]] = []
    
    @workflow.run
    async def run(self, input: AgentInput) -> str:
        workflow.logger.info("Starting DurableAgentWorkflow")
        
        if input.initial_prompt:
            self.current_message = input.initial_prompt
        
        while not self.chat_ended:
            # Wait for a message to process
            await workflow.wait_condition(
                lambda: self.current_message is not None or self.chat_ended
            )
            
            if self.current_message:
                await self._process_message()
        
        workflow.logger.info("Chat ended")
        return self._format_final_transcript()
    
    async def _process_message(self) -> None:
        """Process user message through the agent loop"""
        user_message = self.current_message
        workflow.logger.info(f"Processing: {user_message}")
        
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Agent loop: plan and execute until we have a response
        context = user_message
        
        while True:
            plan: PlanResult = await workflow.execute_activity(
                AgentActivities.plan_next_action,
                args=[context, self.conversation_history],
                start_to_close_timeout=timedelta(minutes=1),
                # Making these explicit for clarity, but Temporal has defaults
                # https://python.temporal.io/temporalio.common.RetryPolicy.html
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    maximum_interval=timedelta(seconds=60),
                    backoff_coefficient=2.0,
                    # Commenting out to allow time to simulate failure
                    # maximum_attempts=3 
                )
            )
            
            if plan.next_step == "execute_tool":
                workflow.logger.info(f"Executing tool: {plan.tool_name}")
                
                tool_result: ToolResult = await workflow.execute_activity(
                    AgentActivities.execute_tool,
                    args=[plan.tool_name, plan.tool_args or {}],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=2),
                        # Commenting out to allow time to simulate failure
                        # maximum_attempts=3 
                    )
                )
                
                # Add to LLM context
                self.conversation_history.append({
                    "role": "assistant",
                    "content": f"I'll use the {tool_result.tool_name} tool."
                })
                self.conversation_history.append({
                    "role": "user",
                    "content": f"Tool result: {tool_result.result}"
                })
                
                context = f"Tool {tool_result.tool_name} returned: {tool_result.result}"
                # Continue loop
            
            else:  # "respond" or "done"
                self.conversation_history.append({
                    "role": "assistant",
                    "content": plan.response
                })
                
                self.pending_response = plan.response
                self.current_message = None  # Done processing
                
                workflow.logger.info(f"Response ready: {plan.response}")
                
                if plan.next_step == "done":
                    self.chat_ended = True
                
                return
    
    # -------------------------------------------------------------------------
    # SIGNALS: How the client sends data to the workflow
    # -------------------------------------------------------------------------
    
    @workflow.update
    async def send_message(self, message: str) -> str:
        """
        Send a message and wait for response.
        
        Uses Temporal Update - blocks until response is ready.
        """
        if self.chat_ended:
            return "[Chat has ended]"
        
        if self.current_message is not None:
            return "[Agent is busy processing another message]"
        
        workflow.logger.info(f"Received: {message}")
        self.current_message = message
        
        # Wait for response
        await workflow.wait_condition(lambda: self.pending_response is not None)
        
        # Return and clear response
        response = self.pending_response
        self.pending_response = None
        return response
    
    @workflow.signal
    async def end_chat(self) -> None:
        """End the conversation"""
        workflow.logger.info("Received end_chat signal")
        self.chat_ended = True
    
    @workflow.query
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history"""
        return self.conversation_history
    
    # Returns the final transcript, showing the contents of conversation_history
    # without internal tool messages
    def _format_final_transcript(self) -> str:
        lines = []
        for msg in self.conversation_history:
            content = msg["content"]
            # Skip internal tool messages
            if content.startswith("I'll use the ") or content.startswith("Tool result:"):
                continue
            lines.append(f"{msg['role'].title()}: {content}")
        return "\n".join(lines)