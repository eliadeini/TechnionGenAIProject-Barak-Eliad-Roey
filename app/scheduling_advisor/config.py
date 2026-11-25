"""Paths, model and settings of the Scheduling Advisor."""
import os
from pathlib import Path

from dotenv import load_dotenv

### the folder of the advisor, and the project folder
FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[1]
DB_FILE = FOLDER / "tech.db"

### load the variables of the .env file (the API key is never written in the code)
load_dotenv(ROOT / ".env")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-2024-11-20")

### the position whose slots we search and book
POSITION = "Python Dev"


def check_api_key():
    """A clear message instead of a long error"""
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing. Put it in the .env file of the project.")


def load_prompt(name):
    """Read a prompt file (Identity, Instructions, Examples, Context)"""
    with open(FOLDER / f"{name}.txt", "r", encoding="utf-8") as f:
        return f.read()
