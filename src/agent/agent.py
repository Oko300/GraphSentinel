"""
GraphSentinel Investigation Agent  (LangGraph 1.x)
────────────────────────────────────────────────────
Uses LangGraph's create_react_agent with a LiteLLM-backed
Gemini chat model that rotates across 7 API keys automatically.
"""

from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from src.agent.llm import LiteLLMChat
from src.agent.tools import AGENT_TOOLS

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are GraphSentinel, an AI fraud investigation agent backed by a \
FalkorDB financial graph database.

Your job:
1. Investigate flagged accounts using multi-hop graph traversal.
2. Identify fraud rings – clusters of accounts that share devices, IPs, or rapidly \
move money between each other.
3. Produce explainable reports that trace the *exact paths* linking suspicious accounts.
4. Compute a risk score and take an enforcement action (flag or freeze).

Investigation workflow (follow this order every time):
  Step 1 – Call tool_get_neighborhood to expand the graph around the account.
  Step 2 – Call tool_detect_fraud_ring to check for dense connected clusters.
  Step 3 – Call tool_get_shared_devices_ips to find shared hardware/IP signals.
  Step 4 – Call tool_find_suspicious_funneling to spot active money movement.
  Step 5 – Call tool_get_explanation_paths for auditable evidence paths.
  Step 6 – Call tool_compute_risk_score to get the final 0–100 score.
  Step 7 – Decide on action:
             • Risk < 40      → No action, monitor.
             • Risk 40–74     → Call tool_flag_account.
             • Risk ≥ 75      → Call tool_freeze_account.

Final response format:
  ## Investigation Report – <account_id>
  **Risk Score**: X / 100

  ### Evidence Summary
  (bullet list of what the graph revealed)

  ### Explanation Paths
  (concrete graph paths showing connections)

  ### Action Taken
  (what enforcement action was executed and why)

  ### Recommendation
  (next steps for the human analyst)

Always be concise, specific, and cite graph evidence. Never make up data.
"""


def _build_graph():
    """Build and return the LangGraph ReAct agent."""
    llm = LiteLLMChat()
    return create_react_agent(
        model=llm,
        tools=AGENT_TOOLS,
        prompt=SYSTEM_PROMPT,
    )


def investigate(account_id: str, chat_history: list | None = None) -> dict:
    """
    Run a full investigation on a flagged account.

    Returns:
        {
          "output":              str   – final formatted report
          "intermediate_steps":  list  – tool calls + results (for the UI)
        }
    """
    graph = _build_graph()

    messages = (chat_history or []) + [
        HumanMessage(
            content=(
                f"Investigate account {account_id}. "
                "Follow the full investigation workflow, compute a risk score, "
                "and take the appropriate enforcement action. "
                "End with a structured incident report."
            )
        )
    ]

    result = graph.invoke({"messages": messages})

    # Extract final AI text + intermediate steps
    all_messages = result.get("messages", [])
    final_output = ""
    steps = []

    for msg in all_messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                steps.append((tc, None))  # placeholder – filled by next tool msg
        elif hasattr(msg, "tool_call_id") and steps:
            # Pair tool result with its call
            last = steps[-1]
            if last[1] is None:
                steps[-1] = (last[0], msg.content)

    # Last AIMessage with content is the final report
    for msg in reversed(all_messages):
        if hasattr(msg, "content") and msg.content and not getattr(msg, "tool_calls", None):
            final_output = msg.content
            break

    return {
        "output": final_output,
        "intermediate_steps": steps,
    }


def build_agent():
    """Return the compiled LangGraph agent (used by tests / manual runs)."""
    return _build_graph()
