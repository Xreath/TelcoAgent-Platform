import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import HumanMessage
from agents.orchestrator.state import AgentState
from agents.orchestrator.supervisor import supervisor_graph

async def test_run():
    # Use dev settings 
    os.environ["DEV_MODE"] = "true"
    
    # Needs valid openai api key - assuming it's in the environment or using deepseek
    customer_id = "613a0ac0-6699-4f1f-8a22-065896f948ea"
    
    initial_state = AgentState(
        messages=[HumanMessage(content="Faturam 3 kat gelmis neden?")],
        customer_id=customer_id,
        metadata={"priority": "high", "invoice_id": "01fa42d7-97c3-4587-a9df-a04e459b06af"},
        domain="",
        routing_decision="",
        final_response="",
        tools_used=[],
        error=None,
    )
    
    print(f"Submitting complaint for {customer_id}...")
    
    # We invoke the orchestrator graph
    try:
        result = await supervisor_graph.ainvoke(initial_state)
        print(f"\nFinal Result:\nDomain: {result.get('domain')}")
        print(f"Reasoning: {result.get('routing_decision')}")
        print(f"Tools Used: {result.get('tools_used')}")
        print(f"Response: {result.get('final_response')}")
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_run())
