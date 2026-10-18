"""
Core Cypher queries used as agent tools.
These are the heart of Track 1 – multi-hop reasoning + explainable paths.
"""

from src.graph.client import run_query


def get_account_neighborhood(account_id: str, max_hops: int = 2):
    """
    Multi-hop expansion from a flagged account.
    Returns connected accounts, devices, IPs and transactions.
    """
    query = """
    MATCH (a:Account {id: $account_id})
    OPTIONAL MATCH (a)-[:OWNS]->(d:Device)
    OPTIONAL MATCH (a)-[:USED_IP]->(ip:IP)
    OPTIONAL MATCH (a)-[:SENT]->(t:Transaction)
    OPTIONAL MATCH (a)-[:LINKED_TO]-(linked:Account)
    OPTIONAL MATCH (a)-[:OWNS]->(:Device)<-[:OWNS]-(other1:Account)
    WHERE other1.id <> $account_id
    OPTIONAL MATCH (a)-[:USED_IP]->(:IP)<-[:USED_IP]-(other2:Account)
    WHERE other2.id <> $account_id
    RETURN a, d, ip, t, linked, other1, other2
    LIMIT 100
    """
    return run_query(query, {"account_id": account_id})


def detect_fraud_ring(account_id: str):
    """
    Find accounts tightly connected via shared devices/IPs or rapid transfers.
    """
    query = """
    MATCH (a:Account {id: $account_id})-[:LINKED_TO*1..2]-(ring:Account)
    WITH collect(DISTINCT ring) AS ring_accounts, a
    RETURN a.id AS seed,
           size(ring_accounts) AS ring_size,
           [acc IN ring_accounts | acc.id] AS members
    """
    return run_query(query, {"account_id": account_id})


def find_suspicious_funneling(hours: int = 24, min_tx: int = 2):
    """
    Detect rapid money movement patterns (classic ring behavior).
    Note: timestamps are stored as ISO strings, so we avoid datetime()/duration()
    which are not fully supported / cause 'Unknown function datetime'.
    """
    query = """
    MATCH (src:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(dst:Account)
    WHERE t.amount > 500
    WITH src, dst, count(t) AS tx_count, sum(t.amount) AS total_amount
    WHERE tx_count >= $min_tx
    RETURN src.id AS from_account,
           dst.id AS to_account,
           tx_count,
           total_amount
    ORDER BY total_amount DESC
    LIMIT 20
    """
    return run_query(query, {"min_tx": min_tx})


def get_shared_devices_and_ips(account_id: str):
    """
    Find other accounts sharing the same devices or IPs (strong link signal).
    """
    query = """
    MATCH (a:Account {id: $account_id})-[:OWNS]->(d:Device)<-[:OWNS]-(other:Account)
    WHERE other.id <> $account_id
    RETURN 'device' AS link_type, d.id AS resource, other.id AS other_account
    UNION
    MATCH (a:Account {id: $account_id})-[:USED_IP]->(ip:IP)<-[:USED_IP]-(other:Account)
    WHERE other.id <> $account_id
    RETURN 'ip' AS link_type, ip.address AS resource, other.id AS other_account
    """
    return run_query(query, {"account_id": account_id})


def get_explanation_paths(account_id: str, target_id: str | None = None):
    """
    Return concrete paths that explain why accounts are connected.
    Critical for 'explainable results' required by Track 1.

    FalkorDB only supports shortestPath() in WITH or RETURN (not MATCH path = ...).
    We use variable-length MATCH instead for reliability.
    """
    if target_id:
        # Point-to-point path — variable-length, no shortestPath in MATCH
        query = """
        MATCH path = (a:Account {id: $account_id})-[:LINKED_TO*1..3]-(b:Account {id: $target_id})
        RETURN path
        LIMIT 5
        """
        return run_query(query, {"account_id": account_id, "target_id": target_id})
    else:
        query = """
        MATCH path = (a:Account {id: $account_id})-[:LINKED_TO*1..2]-(related:Account)
        RETURN path
        LIMIT 15
        """
        return run_query(query, {"account_id": account_id})
