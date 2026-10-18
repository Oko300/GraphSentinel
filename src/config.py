import os
from dotenv import load_dotenv

load_dotenv()

# FalkorDB
FALKORDB_HOST = os.getenv("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.getenv("FALKORDB_PORT", "6380"))
FALKORDB_GRAPH = os.getenv("FALKORDB_GRAPH", "graphsentinel")
FALKORDB_USERNAME = os.getenv("FALKORDB_USERNAME", "") or None
FALKORDB_PASSWORD = os.getenv("FALKORDB_PASSWORD", "") or None

# LLM
DEFAULT_LLM = os.getenv("DEFAULT_LLM", "gemini").lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini/gemini-3.8-flash")

# Optional fallbacks
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
