"""Central configuration for The Agentic Orchestra."""

import os
from pathlib import Path

from dotenv import load_dotenv


ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(ENV_PATH)

OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("MODEL")

_missing = [
    name
    for name, value in (
        ("OPENAI_ENDPOINT", OPENAI_ENDPOINT),
        ("OPENAI_API_KEY", OPENAI_API_KEY),
        ("MODEL", MODEL),
    )
    if not value
]
if _missing:
    raise RuntimeError(
        "Missing required LLM configuration: "
        + ", ".join(_missing)
        + f". Add the missing value(s) to {ENV_PATH}."
    )


def moodle_subprocess_env() -> dict[str, str]:
    """Return the inherited environment with UTF-8 forced for moodle-cli."""

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env
