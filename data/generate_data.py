"""
Generate synthetic financial graph data with planted fraud rings.
Safe for the hackathon – all data is fake.
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from falkordb import FalkorDB

from src.config import FALKORDB_HOST, FALKORDB_PORT, FALKORDB_GRAPH

fake = Faker()
random.seed(42)  # reproducible


def get_graph():
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph(FALKORDB_GRAPH)


def clear_graph(graph):
    graph.query("MATCH (n) DETACH DELETE n")


def create_account(graph, account_id: str, name: str = None, balance: float = None):
    name = name or fake.name()
    balance = balance if balance is not None else round(random.uniform(100, 50000), 2)
    status = "active"
    created = (datetime.utcnow() - timedelta(days=random.randint(30, 800))).isoformat()
    graph.query(
        """
        CREATE (a:Account {
            id: $id,
            name: $name,
            balance: $balance,
            created_at: $created,
            status: $status,
            risk_score: 0.0
        })
        """,
        {"id": account_id, "name": name, "balance": balance, "created": created, "status": status},
    )


def create_device(graph, device_id: str, device_type: str = None):
    device_type = device_type or random.choice(["mobile", "desktop", "tablet"])
    last_seen = (datetime.utcnow() - timedelta(hours=random.randint(1, 200))).isoformat()
    graph.query(
        "CREATE (d:Device {id: $id, type: $type, last_seen: $last_seen})",
        {"id": device_id, "type": device_type, "last_seen": last_seen},
    )


def create_ip(graph, address: str, country: str = None):
    country = country or fake.country_code()
    risk = random.choice(["low", "medium", "high"])
    graph.query(
        "CREATE (ip:IP {address: $address, country: $country, risk_level: $risk})",
        {"address": address, "country": country, "risk": risk},
    )


def link_account_device(graph, account_id: str, device_id: str):
    graph.query(
        """
        MATCH (a:Account {id: $aid}), (d:Device {id: $did})
        CREATE (a)-[:OWNS]->(d)
        """,
        {"aid": account_id, "did": device_id},
    )


def link_account_ip(graph, account_id: str, ip_address: str):
    graph.query(
        """
        MATCH (a:Account {id: $aid}), (ip:IP {address: $ip})
        CREATE (a)-[:USED_IP]->(ip)
        """,
        {"aid": account_id, "ip": ip_address},
    )


def create_transaction(graph, tx_id: str, from_id: str, to_id: str, amount: float, hours_ago: int):
    ts = (datetime.utcnow() - timedelta(hours=hours_ago)).isoformat()
    graph.query(
        """
        MATCH (src:Account {id: $from_id}), (dst:Account {id: $to_id})
        CREATE (t:Transaction {id: $tx_id, amount: $amount, timestamp: $ts, type: 'transfer'})
        CREATE (src)-[:SENT]->(t)-[:RECEIVED_BY]->(dst)
        """,
        {"tx_id": tx_id, "from_id": from_id, "to_id": to_id, "amount": amount, "ts": ts},
    )


def create_linked_to(graph, a1: str, a2: str):
    graph.query(
        """
        MATCH (a:Account {id: $a1}), (b:Account {id: $a2})
        CREATE (a)-[:LINKED_TO]->(b)
        """,
        {"a1": a1, "a2": a2},
    )


def plant_fraud_ring(graph, ring_prefix: str, size: int = 5):
    """Create a tight fraud ring that shares devices/IPs and moves money."""
    accounts = [f"{ring_prefix}_ACC_{i:02d}" for i in range(size)]
    shared_device = f"{ring_prefix}_DEV_SHARED"
    shared_ip = f"{ring_prefix}.suspicious.ip"

    # Create shared resources
    create_device(graph, shared_device, "mobile")
    create_ip(graph, shared_ip, "XX")

    for acc in accounts:
        create_account(graph, acc)
        link_account_device(graph, acc, shared_device)
        link_account_ip(graph, acc, shared_ip)

    # Money funneling toward the last account
    for i in range(size - 1):
        create_transaction(
            graph,
            tx_id=f"{ring_prefix}_TX_{i}",
            from_id=accounts[i],
            to_id=accounts[-1],
            amount=round(random.uniform(1200, 8000), 2),
            hours_ago=random.randint(2, 20),
        )
        create_linked_to(graph, accounts[i], accounts[-1])

    # Cross links to make the ring dense
    for i in range(size):
        for j in range(i + 1, size):
            if random.random() > 0.4:
                create_linked_to(graph, accounts[i], accounts[j])

    return accounts


def generate_normal_accounts(graph, count: int = 40):
    """Create normal looking accounts with some light connections."""
    accounts = []
    for i in range(count):
        acc_id = f"NORM_ACC_{i:03d}"
        create_account(graph, acc_id)
        accounts.append(acc_id)

        # Some personal devices/IPs
        if random.random() > 0.3:
            dev_id = f"NORM_DEV_{i:03d}"
            create_device(graph, dev_id)
            link_account_device(graph, acc_id, dev_id)

        if random.random() > 0.4:
            ip = fake.ipv4_public()
            create_ip(graph, ip)
            link_account_ip(graph, acc_id, ip)

    # A few normal transfers
    for _ in range(30):
        src, dst = random.sample(accounts, 2)
        create_transaction(
            graph,
            tx_id=f"NORM_TX_{random.randint(1000,9999)}",
            from_id=src,
            to_id=dst,
            amount=round(random.uniform(50, 2000), 2),
            hours_ago=random.randint(5, 200),
        )

    return accounts


def main():
    print("Connecting to FalkorDB...")
    graph = get_graph()

    print("Clearing existing data...")
    clear_graph(graph)

    print("Creating normal accounts...")
    normal = generate_normal_accounts(graph, 45)

    print("Planting fraud rings...")
    ring1 = plant_fraud_ring(graph, "RING_A", size=6)
    ring2 = plant_fraud_ring(graph, "RING_B", size=4)

    # Make one normal account slightly connected for interesting demos
    create_linked_to(graph, normal[0], ring1[0])

    print("\n✅ Data generation complete!")
    print(f"   Normal accounts : {len(normal)}")
    print(f"   Fraud Ring A    : {ring1}")
    print(f"   Fraud Ring B    : {ring2}")
    print("\nTry investigating: RING_A_ACC_00  or  RING_B_ACC_00")


if __name__ == "__main__":
    main()
