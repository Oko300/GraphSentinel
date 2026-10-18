import os
from dotenv import load_dotenv

load_dotenv()

# FalkorDB
FALKORDB_HOST = os.getenv("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.getenv("FALKORDB_PORT", 6380))  # Changed to 6380 to avoid local Redis conflict
FALKORDB_GRAPH = os.getenv("FALKORDB_GRAPH", "graphsentinel")

# LLM — gemini-2.0-flash is retired; use 3.8-flash
DEFAULT_LLM = os.getenv("DEFAULT_LLM", "gemini").lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini/gemini-3.8-flash")

# Legacy keys (kept for optional fallback)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
