import json
import os
from pathlib import Path
from typing import Any

CONFIG_DIR = Path(os.environ.get("OR_PRICER_CONFIG_DIR", Path(__file__).parent.parent))
CONFIG_PATH = CONFIG_DIR / "config.json"

PROVIDER_REGIONS: dict[str, str] = {
    "mistralai": "europe",
    "aleph-alpha": "europe",
    "lighton": "europe",
    "poolside": "europe",
    "openai": "usa",
    "anthropic": "usa",
    "google": "usa",
    "meta-llama": "usa",
    "meta": "usa",
    "amazon": "usa",
    "cohere": "usa",
    "perplexity": "usa",
    "x-ai": "usa",
    "nvidia": "usa",
    "microsoft": "usa",
    "ibm-granite": "usa",
    "writer": "usa",
    "allenai": "usa",
    "nousresearch": "usa",
    "ai21": "usa",
    "deepseek": "china",
    "qwen": "china",
    "bytedance": "china",
    "bytedance-seed": "china",
    "baidu": "china",
    "minimax": "china",
    "moonshotai": "china",
    "z-ai": "china",
    "stepfun": "china",
    "tencent": "china",
    "xiaomi": "china",
    "meituan": "china",
    "kwaipilot": "china",
    "inclusionai": "china",
    "deepcogito": "china",
    "upstage": "asia",
    "sakana": "asia",
    "aion-labs": "asia",
    "rekaai": "asia",
}


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return _default_config()


def get_cache_ttl(config: dict) -> int:
    return config.get("cache_ttl_hours", 12)


def get_groups(config: dict) -> dict[str, list[str]]:
    return config.get("groups", {})


def get_provider_region(model_id: str) -> str:
    prefix = model_id.split("/")[0] if "/" in model_id else model_id.split(":")[0]
    prefix = prefix.lstrip("~")
    return PROVIDER_REGIONS.get(prefix, "other")


def is_dsgvo(model_id: str) -> bool:
    return get_provider_region(model_id) == "europe"


def _default_config() -> dict:
    return {
        "groups": {},
        "cache_ttl_hours": 12,
        "display": {"unit": "1M tokens", "currency": "USD"},
    }
