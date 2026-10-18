"""
GraphSentinel Data Model

Nodes:
- Account (id, name, balance, created_at, status, risk_score)
- Device (id, type, last_seen)
- IP (address, country, risk_level)
- Transaction (id, amount, timestamp, type)

Relationships:
- (Account)-[:OWNS]->(Device)
- (Account)-[:USED_IP]->(IP)
- (Account)-[:SENT]->(Transaction)-[:RECEIVED_BY]->(Account)
- (Transaction)-[:VIA_DEVICE]->(Device)
- (Account)-[:LINKED_TO]->(Account)   # shared device / IP / rapid transfer
"""

SCHEMA_DESCRIPTION = """
Nodes:
  (:Account {id, name, balance, created_at, status, risk_score})
  (:Device {id, type, last_seen})
  (:IP {address, country, risk_level})
  (:Transaction {id, amount, timestamp, type})

Relationships:
  (:Account)-[:OWNS]->(:Device)
  (:Account)-[:USED_IP]->(:IP)
  (:Account)-[:SENT]->(:Transaction)-[:RECEIVED_BY]->(:Account)
  (:Transaction)-[:VIA_DEVICE]->(:Device)
  (:Account)-[:LINKED_TO]->(:Account)
"""
