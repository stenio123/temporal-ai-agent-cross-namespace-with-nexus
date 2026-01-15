# Cross Namespace AI Agent Orchestration with Temporal Nexus

## 🚀 Quick Start

```bash
# 1. Install Temporal CLI
brew install temporal  # macOS
# or: curl -sSf https://temporal.download/cli.sh | sh  # Linux

# 2. Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Set your LLM API key
export OPENAI_API_KEY='sk-your-key-here'

# 4. Install dependencies
cd /path/to/researchPaper/code
uv sync

# 5. Start Temporal (in separate terminal)
temporal server start-dev

# 6. Start worker (in another terminal)
uv run worker.py

# 7. Run the agent (in third terminal)
uv run start_workflow.py
```

### Create Namespace in local dev
```
temporal operator namespace create it-namespace
temporal operator namespace create finance-namespace
```
### Create Namespace in Temporal Cloud
```
cd infrastructure
terraform apply
# Make sure to update the namespace in the it_nexus_worker.py and the finance_nexus_worker.py file
```


---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  DurableAgentWorkflow                   │
│              (Deterministic Orchestrator)               │
│  • Manages agent loop                                   │
│  • Makes no I/O calls directly                          │
│  • Delegates to activities                              │
└────────────┬────────────────────────────────┬───────────┘
             │                                │
             ▼                                ▼
    ┌────────────────────┐             ┌──────────────────┐
    │ plan_next_action   │             │  execute_tool    │
    │   (Activity)       │             │   (Activity)     │
    └────────┬───────────┘             └───────┬──────────┘
             │                                 │
             ▼                                 ▼
      ┌──────────┐                    ┌─────────────┐
      │   LLM    │                    │   Tools     │
      │  Client  │                    │ (calc, etc) │
      └──────────┘                    └─────────────┘
```

Execution flow:

![Alt Text](images/execution_flow.png)


## Prerequisites

1. **Temporal CLI**: Install the Temporal CLI for running the dev server
   ```bash
   # On macOS:
   brew install temporal
   
   # On Linux:
   curl -sSf https://temporal.download/cli.sh | sh
   
   # For other platforms, see: https://docs.temporal.io/cli
   ```

2. **uv**: Fast Python package installer and manager
   ```bash
   # On macOS/Linux:
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Or via pip:
   pip install uv
   ```

3. **Python 3.8+**: Managed automatically by `uv`

4. **LLM API Key**: You'll need an API key for your LLM provider

## Installation

### 1. Set up your LLM API Key

- Make a copy of .env.example and name it .env 
- Choose your provider and set the appropriate environment variable

### 2. Install Dependencies

```bash
# Create virtual environment and install dependencies
uv sync

# This will:
# - Create a .venv directory with a virtual environment
# - Install all dependencies from pyproject.toml
# - Lock dependencies in uv.lock for reproducibility
```

### 3. Start Temporal Dev Server

In a **separate terminal** (keep it running):

```bash
# Start Temporal development server
temporal server start-dev

# This will:
# - Start Temporal server on localhost:7233
# - Start Web UI on http://localhost:8233
# - Use in-memory database
```

**Verify Temporal is running:**
- Open http://localhost:8233 in your browser
- You should see the Temporal Web UI

## Running the Agent

**Prerequisites:** Make sure you have:
1. ✅ Set your LLM API key environment variable
2. ✅ Temporal dev server running (`temporal server start-dev`)
3. ✅ Installed dependencies (`uv sync`)

### 1. Start the Worker

In one terminal:
```bash
uv run worker.py
```

This starts the Temporal worker that executes workflows and activities.

### 2. Start an Interactive Session

In **another terminal** (keep the worker running):
```bash
uv run start_workflow.py
```

You can now chat with the agent. Try these examples:
- "What is 25 + 17?"
- "What's the weather in Seattle?"
- "Calculate 100 / 5"

Type `quit`, `exit`, or `bye` to end the session.


## Note
This implementation is for educational purposes only and is not intended to be used in production. Current limitations include no context window management and no session management.