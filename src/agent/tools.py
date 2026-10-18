"""
LangChain tool definitions that wrap the FalkorDB Cypher queries.
Each tool becomes a callable the agent can invoke during its reasoning loop.
"""

from langchain.tools import tool
from src.graph.queries import (
    get_account_neighborhood,
    detect_fraud_ring,
    find_suspicious_funneling,
    get_shared_devices_and_ips,
    get_explanation_paths,
)
from src.actions.risk import compute_and_update_risk_score
from src.actions.enforcement import flag_account, freeze_account


@tool
def tool_get_neighborhood(account_id: str) -> str:
    """
    Expand the graph around a flagged account.
    Returns connected accounts, devices, IPs and transactions.
    Use this first when investigating any account.
    Input: account_id (string)
    """
    rows = get_account_neighborhood(account_id)
    if not rows:
        return f"No connections found for account {account_id}."
    lines = [f"Found {len(rows)} connected nodes/paths around {account_id}:"]
    for r in rows[:20]:
        lines.append(f"  - {r}")
    return "\n".join(lines)


@tool
def tool_detect_fraud_ring(account_id: str) -> str:
    """
    Detect whether this account is part of a dense fraud ring.
    Returns ring size and member account IDs.
    Use after neighborhood expansion to identify coordinated fraud groups.
    Input: account_id (string)
    """
    rows = detect_fraud_ring(account_id)
    if not rows:
        return f"No fraud ring detected around account {account_id}."
    result = rows[0]
    seed, ring_size, members = result[0], result[1], result[2]
    return (
        f"Fraud ring detected!\n"
        f"  Seed account : {seed}\n"
        f"  Ring size    : {ring_size} accounts\n"
        f"  Members      : {members}"
    )


@tool
def tool_find_suspicious_funneling(hours: int = 24) -> str:
    """
    Scan the entire graph for rapid money-movement patterns in the last N hours.
    Returns account pairs with high transaction counts and total amounts.
    Use to find active funneling that may not be centered on one account.
    Input: hours (int, default 24)
    """
    rows = find_suspicious_funneling(hours=hours)
    if not rows:
        return f"No suspicious funneling detected in the last {hours} hours."
    lines = [f"Suspicious funneling patterns (last {hours}h):"]
    for r in rows[:10]:
        lines.append(
            f"  {r[0]} → {r[1]}  |  {r[2]} transactions  |  ${r[3]:,.2f} total"
        )
    return "\n".join(lines)


@tool
def tool_get_shared_devices_ips(account_id: str) -> str:
    """
    Find other accounts that share the same device or IP address.
    Shared hardware/IP is one of the strongest signals for coordinated fraud.
    Input: account_id (string)
    """
    rows = get_shared_devices_and_ips(account_id)
    if not rows:
        return f"No shared devices or IPs found for account {account_id}."
    lines = [f"Shared resources for {account_id}:"]
    for r in rows:
        lines.append(f"  {r[0].upper()} shared: `{r[1]}` with account `{r[2]}`")
    return "\n".join(lines)


@tool
def tool_get_explanation_paths(account_id: str, target_id: str = "") -> str:
    """
    Return the shortest paths explaining *why* two accounts are connected.
    Critical for producing explainable, auditable investigation reports.
    Input: account_id (string), target_id (string, optional)
    """
    target = target_id.strip() if target_id else None
    rows = get_explanation_paths(account_id, target_id=target or None)
    if not rows:
        return f"No explanation paths found for {account_id}."
    lines = [f"Explanation paths from {account_id}:"]
    for i, r in enumerate(rows[:8]):
        lines.append(f"  Path {i+1}: {r[0]}")
    return "\n".join(lines)


@tool
def tool_compute_risk_score(account_id: str) -> str:
    """
    Compute a 0–100 risk score for an account based on ring membership,
    shared devices/IPs, and funneling behavior. Updates the node in FalkorDB.
    Always call this before recommending any enforcement action.
    Input: account_id (string)
    """
    score, breakdown = compute_and_update_risk_score(account_id)
    lines = [
        f"Risk score for {account_id}: {score:.1f} / 100",
        f"  Ring membership  : {breakdown['ring_score']:.1f}",
        f"  Shared resources : {breakdown['shared_score']:.1f}",
        f"  Funneling        : {breakdown['funnel_score']:.1f}",
    ]
    return "\n".join(lines)


@tool
def tool_flag_account(account_id: str) -> str:
    """
    Flag an account for manual review. Sets status='flagged' in FalkorDB
    and logs the enforcement action.
    Use when risk score is 40–74 or evidence is moderate but not conclusive.
    Input: account_id (string)
    """
    result = flag_account(account_id)
    return result


@tool
def tool_freeze_account(account_id: str) -> str:
    """
    Freeze an account immediately. Sets status='frozen' in FalkorDB
    and logs the enforcement action with timestamp.
    Use only when risk score >= 75 or a confirmed fraud ring is found.
    Input: account_id (string)
    """
    result = freeze_account(account_id)
    return result


# ── Exported list of all tools ────────────────────────────────────────────────
AGENT_TOOLS = [
    tool_get_neighborhood,
    tool_detect_fraud_ring,
    tool_find_suspicious_funneling,
    tool_get_shared_devices_ips,
    tool_get_explanation_paths,
    tool_compute_risk_score,
    tool_flag_account,
    tool_freeze_account,
]
