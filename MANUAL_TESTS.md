# Manual Fault Injection Tests

These scenarios demonstrate the durability primitives through hands-on experimentation.

## Prerequisites

Start the Temporal server:
```bash
temporal server start-dev
```

Open Temporal UI at http://localhost:8233 to observe workflow state during tests.

---

## Scenario 1: Infrastructure Fault (Worker SIGKILL)

**Primitive Tested:** Deterministic Control Flow Separation

**Goal:** Verify workflow recovers after worker process is killed mid-execution.

### Steps

1. **Terminal 1 - Start the client:**
   ```bash
   uv run start_workflow.py
   ```

2. **Terminal 2 - Start the worker:**
   ```bash
   uv run worker.py
   ```

3. **In Terminal 1, send a message that triggers a tool:**
   ```
   You: What is 25 * 4?
   ```

4. **Immediately kill the worker (Terminal 2):**
   ```bash
   pgrep -f "worker.py" | xargs kill -9
   ```

5. **Observe:** Client is waiting for response. Check Temporal UI - workflow shows as "Running".

6. **Stop and restart the worker:**
   ```bash
   uv run worker.py
   ```

7. **Observe:** Response appears in client without re-sending the message.

### Expected Outcome

- Workflow resumes from where it left off
- If the LLM call completed before crash, it is NOT re-executed
- Event history in Temporal UI shows the original activity result was reused

---

## Scenario 2: External Service Timeouts (API Unavailability)

**Primitive Tested:** Managed Side-Effect Abstraction

**Goal:** Verify workflow retries and recovers from transient API failures.

### Steps

1. **Modify `activities.py`** - add failure simulation to `plan_next_action`:
   ```python
   @activity.defn(name="plan_next_action")
   async def plan_next_action(
       self, 
       context: str,
       conversation_history: List[Dict[str, str]],
       available_tools: List[Dict[str, Any]]
   ) -> PlanResult:
       activity.logger.info(f"Planning for context: {context[:100]}...")
       
       # Uncomment this block to simulate API unavailability
       import time
       if not hasattr(self, '_attempt_count'):
           self._attempt_count = 0
       self._attempt_count += 1
       
       if self._attempt_count <= 3:
           activity.logger.error(f"API unavailable (attempt {self._attempt_count}/3)")
           raise Exception("ServiceUnavailable: LLM API temporarily unavailable")
       
       # ... rest of the method unchanged
   ```

2. **Stop and restart the worker:**
   ```bash
   uv run worker.py
   ```

3. **Send a message:**
   ```
   You: Hello, how are you?
   ```

4. **Observe worker logs:** See retry attempts with exponential backoff:
   ```
   API unavailable (attempt 1/3)
   API unavailable (attempt 2/3)
   API unavailable (attempt 3/3)
   Planning for context: Hello...  # Success on attempt 4
   ```

5. **Observe client:** Response eventually arrives.

6. **Remove the failure simulation block from `activities.py`.**

### Expected Outcome

- Workflow remains running during failures (check Temporal UI)
- Automatic retries with backoff (no manual intervention)
- Success after transient failures resolve
- No error handling code needed in workflow logic

---

## Scenario 3: Logic Fault and Hot-Fix

**Primitive Tested:** Event-Sourced State Persistence

**Goal:** Verify a bug can be fixed without losing workflow state.

### Steps

1. **Modify `activities.py`** - introduce a bug in `_run_calculator`:
   ```python
   @activity.defn(name="execute_tool")
   async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
       activity.logger.info(f"Executing {tool_name} with {args}")
       
       # Uncomment this to simulate a bug
       raise RuntimeError("Simulated bug: crash before tool execution")
       
       if tool_name == "calculator":
           # ... rest of method
   ```

2. **Stop and Restart the worker:**
   ```bash
   uv run worker.py
   ```

3. **Send a calculation:**
   ```
   You: What is 10 + 5?
   ```

4. **Observe worker logs:** Repeated failures.

5. **Check Temporal UI:** Workflow is "Running", activity is retrying.

6. **Fix the bug** - comment out the line.

7. **Stop and Restart the worker:**
   ```bash
   uv run worker.py
   ```

8. **Observe:** Response appears in client.

### Expected Outcome

- Workflow does NOT restart from the beginning
- LLM planning result (already stored) is reused
- Only the fixed code path executes
- State accumulated before the bug is preserved

---

## Verification Checklist

For each scenario, verify in Temporal UI (http://localhost:8233):

| Check | Where to Look |
|-------|---------------|
| Workflow stays "Running" during failures | Workflow list |
| Activity results are persisted | Event History → ActivityTaskCompleted |
| Retries use backoff | Event History → ActivityTaskScheduled timestamps |
| No duplicate LLM calls after recovery | Count ActivityTaskCompleted events |