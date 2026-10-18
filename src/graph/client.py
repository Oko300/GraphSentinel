from falkordb import FalkorDB
from src.config import FALKORDB_HOST, FALKORDB_PORT, FALKORDB_GRAPH


def get_graph():
    """Return a connected FalkorDB graph instance."""
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph(FALKORDB_GRAPH)


def run_query(query: str, params: dict | None = None):
    """Execute a Cypher query and return the result set."""
    graph = get_graph()
    if params:
        result = graph.query(query, params)
    else:
        result = graph.query(query)
    return result.result_set
