"""
GraphSentinel – Streamlit UI
Track 1: Agents That Act on Connected Data  •  Graph Hacks 2026
"""

import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

from src.graph.queries import (
    get_account_neighborhood,
    detect_fraud_ring,
    get_shared_devices_and_ips,
    find_suspicious_funneling,
    get_explanation_paths,
)
from src.graph.schema import SCHEMA_DESCRIPTION
from src.actions.enforcement import get_action_log

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GraphSentinel",
    page_icon="🛡️",
    layout="wide",
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.image(
    "https://img.shields.io/badge/Powered%20by-FalkorDB-blue?style=flat-square",
    width=200,
)
st.sidebar.title("🛡️ GraphSentinel")
st.sidebar.caption("Multi-hop Fraud Ring Detective")
st.sidebar.markdown("---")

mode = st.sidebar.radio(
    "Mode",
    ["🤖 AI Investigation", "🔍 Manual Queries"],
    index=0,
)

account_id = st.sidebar.text_input(
    "Flagged Account ID",
    value="RING_A_ACC_00",
    help="Try RING_A_ACC_00 or RING_B_ACC_00",
)

run_btn = st.sidebar.button("Run Investigation", type="primary", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**Quick test IDs**")
st.sidebar.code("RING_A_ACC_00\nRING_B_ACC_00\nNORM_ACC_000")

# ── Main area ──────────────────────────────────────────────────────────────────
st.title("🛡️ GraphSentinel")
st.caption("Multi-hop Fraud Ring Detective • Powered by FalkorDB • Graph Hacks 2026")


# ── Helper: build interactive graph from neighborhood data ─────────────────────
def build_graph_visualization(account_id: str):
    """
    Pull the account neighborhood and render an interactive agraph.
    Color code: red = ring accounts, orange = devices, blue = IPs, green = normal.
    """
    rows = get_account_neighborhood(account_id)
    ring_result = detect_fraud_ring(account_id)
    ring_members = set()
    if ring_result:
        try:
            ring_members = set(ring_result[0][2] or [])
        except Exception:
            ring_members = set()

    nodes_seen: set = set()
    edges_seen: set = set()
    nodes: list[Node] = []
    edges: list[Edge] = []

    def add_node(node_id: str, label: str, color: str, size: int = 20):
        if node_id and node_id not in nodes_seen:
            nodes_seen.add(node_id)
            nodes.append(Node(id=str(node_id), label=str(label), color=color, size=size))

    def add_edge(src: str, dst: str, label: str = ""):
        if not src or not dst:
            return
        key = f"{src}->{dst}"
        if key not in edges_seen:
            edges_seen.add(key)
            edges.append(Edge(source=str(src), target=str(dst), label=label))

    # Seed account
    seed_color = "#e74c3c" if account_id in ring_members else "#e67e22"
    add_node(account_id, account_id, seed_color, size=30)

    def _props(node):
        if node is None:
            return {}
        if hasattr(node, "properties"):
            return node.properties or {}
        return {}

    def _labels(node):
        if node is None:
            return []
        if hasattr(node, "labels"):
            return list(node.labels or [])
        return []

    for row in rows:
        try:
            # New query returns: a, d, ip, t, linked, other1, other2
            a, d, ip, t, linked, other1, other2 = (list(row) + [None] * 7)[:7]

            # Devices
            if d is not None:
                props = _props(d)
                did = props.get("id") or getattr(d, "id", None)
                if did:
                    nid = f"DEV_{did}"
                    add_node(nid, f"📱 {did}", "#e67e22", size=15)
                    add_edge(account_id, nid, "OWNS")

            # IPs
            if ip is not None:
                props = _props(ip)
                addr = props.get("address") or getattr(ip, "id", None)
                if addr:
                    nid = f"IP_{addr}"
                    add_node(nid, f"🌐 {addr}", "#3498db", size=15)
                    add_edge(account_id, nid, "USED_IP")

            # Transactions
            if t is not None:
                props = _props(t)
                tid = props.get("id") or getattr(t, "id", None)
                amt = props.get("amount", 0)
                if tid:
                    nid = f"TX_{tid}"
                    add_node(nid, f"💸 ${amt:,.0f}", "#9b59b6", size=12)
                    add_edge(account_id, nid, "SENT")

            # Directly linked accounts
            for other in (linked, other1, other2):
                if other is None:
                    continue
                props = _props(other)
                oid = props.get("id")
                if oid and oid != account_id:
                    color = "#e74c3c" if oid in ring_members else "#2ecc71"
                    add_node(oid, oid, color)
                    add_edge(account_id, oid, "LINKED")

        except Exception:
            continue

    return nodes, edges


# ═══════════════════════════════════════════════════════════════════════════════
# MODE 1: AI INVESTIGATION
# ═══════════════════════════════════════════════════════════════════════════════
if mode == "🤖 AI Investigation":

    if run_btn or "last_ai_account" in st.session_state:
        if run_btn:
            st.session_state["last_ai_account"] = account_id
            st.session_state.pop("ai_report", None)  # clear old report

        acc = st.session_state["last_ai_account"]
        tab_report, tab_graph, tab_log = st.tabs(
            ["📋 Report", "🕸️ Graph", "📜 Action Log"]
        )

        # ── Graph tab (always available, no LLM needed) ────────────────────
        with tab_graph:
            st.markdown(f"### Graph Neighborhood: `{acc}`")
            try:
                nodes, edges = build_graph_visualization(acc)
                if nodes:
                    config = Config(
                        width=900,
                        height=500,
                        directed=True,
                        physics=True,
                        hierarchical=False,
                        nodeHighlightBehavior=True,
                        highlightColor="#f1c40f",
                    )
                    agraph(nodes=nodes, edges=edges, config=config)
                    legend_cols = st.columns(4)
                    legend_cols[0].markdown("🔴 **Red** = Ring member")
                    legend_cols[1].markdown("🟢 **Green** = Normal account")
                    legend_cols[2].markdown("🟠 **Orange** = Device")
                    legend_cols[3].markdown("🔵 **Blue** = IP address")
                else:
                    st.info("No neighborhood data found. Is FalkorDB running and seeded?")
            except Exception as e:
                st.error(f"Graph visualization error: {e}")

        # ── Report tab (triggers LLM agent) ───────────────────────────────
        with tab_report:
            if "ai_report" not in st.session_state:
                with st.spinner(f"🤖 Investigating `{acc}` via FalkorDB + AI…"):
                    try:
                        from src.agent.agent import investigate
                        result = investigate(acc)
                        st.session_state["ai_report"] = result
                    except Exception as e:
                        st.error(f"Agent error: {e}")
                        st.session_state["ai_report"] = {"output": str(e), "intermediate_steps": []}

            report = st.session_state.get("ai_report", {})
            if report:
                st.markdown(report.get("output", "No report generated."))

                with st.expander("🔧 Agent reasoning steps"):
                    steps = report.get("intermediate_steps", [])
                    for i, step in enumerate(steps):
                        try:
                            action, observation = step
                            tool_name = getattr(action, "tool", getattr(action, "name", str(action)))
                            tool_input = getattr(action, "tool_input", getattr(action, "args", ""))
                            st.markdown(f"**Step {i+1} – `{tool_name}`**")
                            st.code(f"Input : {tool_input}\nOutput: {observation}")
                        except Exception:
                            st.write(step)

        # ── Action log tab ─────────────────────────────────────────────────
        with tab_log:
            st.markdown("### Enforcement Action Log")
            log = get_action_log()
            if log:
                for entry in log:
                    st.markdown(
                        f"- **{entry.get('action', '?')}** | `{entry.get('account_id', '')}` | {entry.get('timestamp', '')} | {entry.get('detail', '')}"
                    )
            else:
                st.info("No enforcement actions taken yet in this session.")

    else:
        st.info(
            "👈 Enter an account ID in the sidebar and click **Run Investigation** to start."
        )
        st.markdown("""
### How it works

1. **Enter** a flagged account ID (e.g. `RING_A_ACC_00`)
2. The **AI agent** traverses the FalkorDB graph with specialised tools
3. It detects fraud rings, shared devices/IPs, and suspicious money flows
4. It computes a **risk score** and takes an enforcement action (flag / freeze)
5. The **Graph tab** renders an interactive visual of the account's connections

```
Account ──OWNS──▶ Device ◀──OWNS── Ring member
   │                                    │
   └──USED_IP──▶ IP ◀──USED_IP──────────┘
   │
   └──SENT──▶ Transaction ──RECEIVED_BY──▶ Ring member
```
        """)


# ═══════════════════════════════════════════════════════════════════════════════
# MODE 2: MANUAL QUERIES
# ═══════════════════════════════════════════════════════════════════════════════
else:
    if run_btn:
        st.session_state["last_account"] = account_id

    if "last_account" in st.session_state:
        acc = st.session_state["last_account"]
        st.subheader(f"Manual Investigation: `{acc}`")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🔗 Fraud Ring Detection")
            try:
                ring_result = detect_fraud_ring(acc)
                if ring_result:
                    row = ring_result[0]
                    st.metric("Ring Size", row[1])
                    st.write("**Members:**", row[2])
                else:
                    st.info("No dense ring detected.")
            except Exception as e:
                st.error(f"Query error: {e}")

        with col2:
            st.markdown("### 📱 Shared Devices & IPs")
            try:
                shared = get_shared_devices_and_ips(acc)
                if shared:
                    for row in shared:
                        st.write(f"- **{row[0]}**: `{row[1]}` → Account `{row[2]}`")
                else:
                    st.info("No shared devices/IPs found.")
            except Exception as e:
                st.error(f"Query error: {e}")

        st.markdown("### 💸 Suspicious Funneling (last 24h)")
        try:
            funnel = find_suspicious_funneling()
            if funnel:
                st.write([{"From": r[0], "To": r[1], "Tx Count": r[2], "Total Amount": f"${r[3]:,.2f}"} for r in funnel])
            else:
                st.info("No strong funneling patterns detected.")
        except Exception as e:
            st.error(f"Query error: {e}")

        st.markdown("### 🕸️ Graph Visualization")
        try:
            nodes, edges = build_graph_visualization(acc)
            if nodes:
                config = Config(width=900, height=450, directed=True, physics=True)
                agraph(nodes=nodes, edges=edges, config=config)
            else:
                st.info("No graph data. Run `python data/generate_data.py` first.")
        except Exception as e:
            st.error(f"Graph error: {e}")

        st.markdown("### 🛤️ Explanation Paths")
        try:
            paths = get_explanation_paths(acc)
            if paths:
                for i, p in enumerate(paths[:5]):
                    st.code(str(p[0]), language="text")
            else:
                st.write("No paths returned.")
        except Exception as e:
            st.error(f"Query error: {e}")

    else:
        st.info("👈 Enter an account ID and click **Run Investigation**.")

# ── Schema expander (always visible at the bottom) ─────────────────────────────
with st.expander("📊 Graph Schema"):
    st.code(SCHEMA_DESCRIPTION, language="text")
