# Durable Agent Loop - OpenAI Agents SDK Implementation

**Approach:** OpenAI Agents SDK with AI agent loop management

This implementation demonstrates a complete durable agent loop built with:
- **OpenAI Agents SDK** - AI agent orchestration via Runner.run()
- **LiteLLM integration** - Support for any LLM provider (OpenAI, Anthropic Claude, Google Gemini, etc.)
- **Temporal activities** - Local tools wrapped as activities
- **Nexus operations** - Cross-namespace tool execution (IT and Finance services)
- **Automatic conversation memory** - SDK manages conversation history
- **Multi-turn conversations** - Interactive chat via Temporal Updates

## Architecture

![Architecture](../images/openai_temporal.png)

### Components

1. **Orchestrator Workflow** (`app/workflow.py`)
   - OpenAI Agent SDK integration with Runner.run()
   - Automatic agent loop and conversation history
   - Local tools via activity_as_tool()
   - Remote tools via nexus_operation_as_tool() for each operation

2. **Activities** (`app/activities.py`)
   - Local tools: calculator, weather
   - Wrapped as activities for durability

3. **Nexus Services** (Remote namespaces)
   - IT Service: jira_metrics, get_ip (individual operations)
   - Finance Service: stock_price, calculate_roi (individual operations)
   - Each operation uses Pydantic models for inputs (Temporal best practice)

4. **Workers**
   - `orchestrator_worker.py` - Main workflow and activities
   - `it_nexus_worker.py` - IT tools in separate namespace
   - `finance_nexus_worker.py` - Finance tools in separate namespace

5. **Client** (`client.py`)
   - Interactive CLI for multi-turn conversations
   - Uses Temporal Updates for request/response

## Prerequisites

1. **Temporal Server** running locally:
   ```bash
   temporal server start-dev
   ```

2. **Python 3.11+** with uv:
   ```bash
   # Install uv if needed
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **LLM API Key** (OpenAI, Anthropic, etc.):
   ```bash
   # For OpenAI
   export OPENAI_API_KEY=your_key_here

   # For Anthropic
   export ANTHROPIC_API_KEY=your_key_here
   ```

## Setup

1. **Navigate to this directory:**
   ```bash
   cd openai_temporal
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API key
   ```

4. **Create Nexus endpoints** (one-time setup):
   ```bash
   # Create namespaces
   temporal operator namespace create --namespace it-namespace
   temporal operator namespace create --namespace finance-namespace

   # Create Nexus endpoints
   temporal operator nexus endpoint create \
     --name it-nexus-endpoint \
     --target-namespace it-namespace \
     --target-task-queue it-task-queue

   temporal operator nexus endpoint create \
     --name finance-nexus-endpoint \
     --target-namespace finance-namespace \
     --target-task-queue finance-task-queue
   ```

## Running the Demo

You need **3 terminal windows** running simultaneously:

### Terminal 1: IT Nexus Worker
```bash
cd openai_temporal
uv run it_nexus_worker.py
```

### Terminal 2: Finance Nexus Worker
```bash
cd openai_temporal
uv run finance_nexus_worker.py
```

### Terminal 3: Orchestrator Worker
```bash
cd openai_temporal
uv run orchestrator_worker.py
```

### Terminal 4: Client (Interactive Chat)
```bash
cd openai_temporal
uv run client.py
```

## Example Interactions

```
You: Calculate 15 * 23
Agent: The result is 345.

You: What is my IP address?
Agent: Your IP address is 172.16.0.1

You: What is the stock price of AAPL?
Agent: The current stock price of AAPL is $185.50

You: Calculate the ROI for $10000 invested at 5% for 10 years
Agent: The ROI for $10,000 invested at 5% annually over 10 years is $16,288.95

You: quit
```

## Switching LLM Providers

This implementation uses LiteLLM, so you can easily switch providers by:

1. **Edit `.env` file** and change the model:
   ```bash
   # For OpenAI (default)
   LLM_MODEL=gpt-4

   # For Anthropic Claude
   LLM_MODEL=claude-3-5-sonnet-20241022

   # For Google Gemini
   LLM_MODEL=gemini/gemini-pro
   ```

2. **Set appropriate API key in `.env`:**
   ```bash
   # For Claude
   ANTHROPIC_API_KEY=your_key

   # For Gemini
   GOOGLE_API_KEY=your_key
   ```

3. **Restart workers** for changes to take effect


**Non-OpenAI Model Warnings:**
When using non-OpenAI models (e.g., Anthropic Claude), you may see harmless tracing warnings:
```
Current span is not a FunctionSpanData, skipping tool output
OPENAI_API_KEY is not set, skipping trace export
```
These warnings are expected and do not affect functionality. The OpenAI Agents SDK includes optional tracing features that attempt to export traces to OpenAI when available.

## Learn More

- [Temporal Documentation](https://docs.temporal.io)
- [Temporal Nexus](https://docs.temporal.io/nexus)
- [LiteLLM Providers](https://docs.litellm.ai/docs/providers)
- [Temporal Python SDK](https://github.com/temporalio/sdk-python)
