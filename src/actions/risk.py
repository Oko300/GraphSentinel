"""
Risk scoring logic.
Produces a 0–100 composite score from graph evidence and writes it back to FalkorDB.
"""

from src.graph.client import run_query
from src.graph.queries import (
    detect_fraud_ring,
    get_shared_devices_and_ips,
    find_suspicious_funneling,
)


def compute_and_update_risk_score(account_id: str) -> tuple[float, dict]:
    """
    Compute a risk score for a single account and persist it.

    Scoring breakdown (max 100):
      - Ring membership     : 0–40  (ring size drives the score)
      - Shared device / IP  : 0–30  (number of shared resources)
      - Active funneling    : 0–30  (appears in suspicious funneling scan)

    Returns (score, breakdown_dict)
    """
    breakdown = {"ring_score": 0.0, "shared_score": 0.0, "funnel_score": 0.0}

    # ── Ring membership ───────────────────────────────────────────────────────
    ring_rows = detect_fraud_ring(account_id)
    if ring_rows:
        ring_size = ring_rows[0][1]          # number of connected ring members
        # Cap at ring size 8+ → full 40 points
        breakdown["ring_score"] = min(40.0, (ring_size / 8) * 40.0)

    # ── Shared devices / IPs ──────────────────────────────────────────────────
    shared_rows = get_shared_devices_and_ips(account_id)
    if shared_rows:
        # Each shared resource adds up to 10 points, max 30
        breakdown["shared_score"] = min(30.0, len(shared_rows) * 10.0)

    # ── Active funneling ──────────────────────────────────────────────────────
    funnel_rows = find_suspicious_funneling(hours=48, min_tx=2)
    account_ids_in_funnel = {r[0] for r in funnel_rows} | {r[1] for r in funnel_rows}
    if account_id in account_ids_in_funnel:
        # Find matching rows to gauge intensity
        matching = [
            r for r in funnel_rows if r[0] == account_id or r[1] == account_id
        ]
        max_tx_count = max(r[2] for r in matching) if matching else 0
        breakdown["funnel_score"] = min(30.0, (max_tx_count / 5) * 30.0)

    score = round(
        breakdown["ring_score"] + breakdown["shared_score"] + breakdown["funnel_score"],
        2,
    )

    # ── Persist back to FalkorDB ──────────────────────────────────────────────
    run_query(
        "MATCH (a:Account {id: $id}) SET a.risk_score = $score",
        {"id": account_id, "score": score},
    )

    return score, breakdown
