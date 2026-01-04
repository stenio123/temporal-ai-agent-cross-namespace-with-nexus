"""
Performance Benchmark for Durable Agent Loop

Measures latency in two modes:
1. Real LLM: End-to-end latency with actual LLM calls
2. Mock LLM: Temporal overhead only (LLM returns instantly)

The difference isolates the durability cost from LLM inference time.

Usage:
  uv run performance_benchmark.py           # Real LLM mode
  uv run performance_benchmark.py --mock    # Mock LLM mode (swap llm_client.py first)

For mock mode, swap the LLM client before running:
  cp llm_client.py llm_client_real.py       # backup
  cp mock_llm_client.py llm_client.py       # use mock
  # restart worker, run benchmark
  cp llm_client_real.py llm_client.py       # restore
"""
import asyncio
import sys
import time
import statistics

from temporalio.client import Client
from workflow import DurableAgentWorkflow, AgentInput


# =============================================================================
# CONFIGURATION
# =============================================================================

ITERATIONS = 50
TEMPORAL_ADDRESS = "localhost:7233"
TASK_QUEUE = "durable-agent-queue"


# =============================================================================
# BENCHMARK
# =============================================================================

async def run_benchmark(mode: str):
    print("=" * 60)
    print("DURABLE AGENT LOOP - LATENCY BENCHMARK")
    print("=" * 60)
    print(f"Mode: {mode.upper()} LLM")
    print(f"Iterations: {ITERATIONS}")
    
    # Connect
    client = await Client.connect(TEMPORAL_ADDRESS)
    print("Connected to Temporal.\n")
    
    # Start workflow
    handle = await client.start_workflow(
        DurableAgentWorkflow.run,
        AgentInput(),
        id=f"benchmark-{mode}-{time.time()}",
        task_queue=TASK_QUEUE,
    )
    
    # Run iterations
    latencies = []
    for i in range(ITERATIONS):
        start = time.perf_counter()
        await handle.execute_update(
            DurableAgentWorkflow.send_message,
            f"Reply with the number {i}."
        )
        latencies.append((time.perf_counter() - start) * 1000)
        print(f"  [{i+1}/{ITERATIONS}] {latencies[-1]:,.0f} ms")
    
    # Cleanup
    await handle.signal(DurableAgentWorkflow.end_chat)
    await handle.result()
    
    # Report
    print("\n" + "=" * 60)
    print(f"RESULTS ({mode.upper()} LLM)")
    print("=" * 60)
    print(f"  Iterations:    {ITERATIONS}")
    print(f"  Mean latency:  {statistics.mean(latencies):,.0f} ms")
    print(f"  Std deviation: {statistics.stdev(latencies):,.0f} ms")
    print(f"  Min:           {min(latencies):,.0f} ms")
    print(f"  Max:           {max(latencies):,.0f} ms")
    print("=" * 60)


if __name__ == "__main__":
    mode = "mock" if "--mock" in sys.argv else "real"
    asyncio.run(run_benchmark(mode))