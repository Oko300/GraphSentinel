# GraphSentinel

**Track 1 — Agents That Act on Connected Data**  
[Graph Hacks 2026](https://graphhacks.dev) · Powered by **FalkorDB** × WeMakeDevs

An AI investigation agent that reasons over a **financial relationship graph**.  
It expands multi-hop neighborhoods, detects fraud rings via shared devices/IPs and money paths, scores risk, and takes explainable enforcement actions (flag / freeze).

> **Data note (honest):** All graph data is **synthetic**, generated locally with planted fraud rings that mirror real-world patterns (shared device fingerprints, shared IPs, linked accounts). No real customer or bank data is used.

---

## Demo flow (2–3 minutes)

1. Start FalkorDB + seed data (below).
2. Open the Streamlit UI → **AI Investigation**.
3. Investigate `RING_A_ACC_00` (or `RING_B_ACC_00`).
4. Show **Report** (risk score + evidence + action), **Graph** (interactive neighborhood), **Action Log** (FLAG/FREEZE).

Narrate: *"Synthetic graph with planted fraud rings that mirror real shared-device / shared-IP rings. The agent uses FalkorDB Cypher tools for multi-hop reasoning—not a flat chatbot."*

---

## Architecture (Track 1)

```
User → Streamlit UI
         ↓
   LangGraph ReAct agent (Gemini via LiteLLM)
         ↓ tool calls
   FalkorDB Cypher tools
     • neighborhood expansion
     • fraud-ring detection
     • shared device / IP
     • funneling patterns
     • explanation paths
         ↓
   Risk score + flag / freeze actions
```

FalkorDB is the **reasoning substrate**, not just storage.

---

## Quick start (local)

### Prerequisites
- Docker Desktop
- Python 3.11+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

### 1. Clone & configure
```bash
git clone https://github.com/Oko300/GraphSentinel.git
cd GraphSentinel
cp .env.example .env
# Edit .env → set GEMINI_API_KEY (and optional GEMINI_API_KEY_1..7 for rotation)
```

### 2. Start FalkorDB
```bash
docker compose up -d
```

Default mapping: host **6380** → container 6379 (avoids clashing with a local Redis on 6379).

### 3. Install deps & seed graph
```bash
pip install -r requirements.txt
set PYTHONPATH=.
python data/generate_data.py
```

Planted test IDs:
- `RING_A_ACC_00` … ring of 6 accounts + shared device/IP  
- `RING_B_ACC_00` … second ring  
- `NORM_ACC_000` … low-risk control  

### 4. Run the app
```bash
streamlit run app.py
```

Open http://localhost:8501

---

## Project structure

```
GraphSentinel/
├── app.py                 # Streamlit UI (Report / Graph / Action Log)
├── docker-compose.yml     # FalkorDB
├── requirements.txt
├── .env.example
├── data/
│   └── generate_data.py   # Synthetic accounts, devices, IPs, planted rings
├── src/
│   ├── config.py
│   ├── graph/             # FalkorDB client + Cypher query tools
│   ├── agent/             # LiteLLM chat model, tools, LangGraph agent
│   └── actions/           # Risk scoring, flag / freeze, action log
└── tests/
```

---

## Deploy notes (optional)

**Streamlit Community Cloud / Render**

1. Push this repo (never commit `.env`).
2. Set secrets: `GEMINI_API_KEY`, `FALKORDB_HOST`, `FALKORDB_PORT`, `FALKORDB_GRAPH`.
3. FalkorDB must be reachable from the host (managed FalkorDB Cloud, or a public Docker host). Local Docker on a laptop is not reachable from Streamlit Cloud.
4. Build command: `pip install -r requirements.txt`  
   Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

For the hackathon **local demo is enough** if judges can see the agent + graph live or on video.

---

## Submission checklist

- [x] Track 1: Agents That Act on Connected Data  
- [x] FalkorDB used for multi-hop graph tools  
- [x] Explainable paths + risk score + action (flag/freeze)  
- [x] Synthetic data only (documented above)  
- [x] Repo: https://github.com/Oko300/GraphSentinel  

---

Built for **Graph Hacks 2026**
