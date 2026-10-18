"""
Enforcement actions – the "act" part of the agent.
Sets account status in FalkorDB and logs every action.
In production these would also call a banking API or SIEM webhook.
"""

from datetime import datetime, timezone
from src.graph.client import run_query

# In-memory action log (in production → write to DB / external system)
ACTION_LOG: list[dict] = []


def _log(action: str, account_id: str, detail: str = "") -> None:
    ACTION_LOG.append(
        {
            "action": action,
            "account_id": account_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": detail,
        }
    )


def flag_account(account_id: str) -> str:
    """
    Set account status to 'flagged' for human review.
    Returns a confirmation string for the agent to include in its report.
    """
    rows = run_query(
        "MATCH (a:Account {id: $id}) RETURN a.status", {"id": account_id}
    )
    if not rows:
        return f"⚠️  Account {account_id} not found in the graph."

    current_status = rows[0][0]
    if current_status in ("frozen",):
        return (
            f"ℹ️  Account {account_id} is already {current_status}. "
            "No downgrade applied."
        )

    run_query(
        "MATCH (a:Account {id: $id}) SET a.status = 'flagged'",
        {"id": account_id},
    )
    _log("FLAG", account_id, f"previous_status={current_status}")
    return (
        f"🚩 Account {account_id} has been FLAGGED for manual review.\n"
        f"   Previous status: {current_status}\n"
        f"   Action logged at {ACTION_LOG[-1]['timestamp']}"
    )


def freeze_account(account_id: str) -> str:
    """
    Set account status to 'frozen' – immediate action to halt transactions.
    Returns a confirmation string for the agent to include in its report.
    """
    rows = run_query(
        "MATCH (a:Account {id: $id}) RETURN a.status", {"id": account_id}
    )
    if not rows:
        return f"⚠️  Account {account_id} not found in the graph."

    current_status = rows[0][0]
    run_query(
        "MATCH (a:Account {id: $id}) SET a.status = 'frozen'",
        {"id": account_id},
    )
    _log("FREEZE", account_id, f"previous_status={current_status}")
    return (
        f"🔒 Account {account_id} has been FROZEN.\n"
        f"   Previous status: {current_status}\n"
        f"   Action logged at {ACTION_LOG[-1]['timestamp']}"
    )


def get_action_log() -> list[dict]:
    """Return the full in-session action log."""
    return ACTION_LOG
