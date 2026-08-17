import json
import time
from pathlib import Path

import httpx

from .config import get_cache_ttl

CACHE_DIR = Path.home() / ".cache" / "or-pricer"
CACHE_FILE = CACHE_DIR / "cache.json"
API_URL = "https://openrouter.ai/api/v1/models"


def find_best_model_match(model_id: str, models: list[dict]) -> dict | None:
    """Find a model by exact id, alias, base slug, then fuzzy prefix match."""
    for m in models:
        if m["id"] == model_id:
            return m
    alias_id = f"~{model_id}" if not model_id.startswith("~") else model_id
    for m in models:
        if m["id"] == alias_id:
            return m
    clean = model_id.lstrip("~")
    for m in models:
        if m["id"] == clean:
            return m
    base = model_id.split(":")[0].lstrip("~")
    for m in models:
        if m["id"] == base or m["id"] == f"~{base}":
            return m
    for m in models:
        mid = m["id"]
        if "/" in mid:
            if mid.startswith(base) and ":" not in mid.split("/", 1)[1]:
                return m
        else:
            if mid.startswith(base):
                return m
    for m in models:
        if m["id"].startswith(base):
            return m
    return None


class OpenRouterClient:
    def __init__(self, cache_ttl_hours: int = 12):
        self.cache_ttl = cache_ttl_hours * 3600
        self._models: list[dict] | None = None

    def fetch_models(self, force_refresh: bool = False) -> list[dict]:
        if not force_refresh and self._models is not None:
            return self._models

        cached = self._load_cache()
        if not force_refresh and cached is not None:
            self._models = cached
            return cached

        data = self._api_fetch()
        self._save_cache(data)
        self._models = data
        return data

    def search(self, term: str, force_refresh: bool = False) -> list[dict]:
        models = self.fetch_models(force_refresh)
        term_lower = term.lower()
        return [
            m
            for m in models
            if term_lower in m.get("id", "").lower()
            or term_lower in m.get("name", "").lower()
            or term_lower in m.get("description", "").lower()
        ]

    def get_model(self, model_id: str, force_refresh: bool = False) -> dict | None:
        models = self.fetch_models(force_refresh)
        model = self._find_exact(model_id, models)
        if model is not None:
            return model
        alias_id = f"~{model_id}" if not model_id.startswith("~") else model_id
        model = self._find_exact(alias_id, models)
        if model is not None:
            return model
        clean_id = model_id.lstrip("~")
        model = self._find_exact(clean_id, models)
        if model is not None:
            return model
        return self._find_best_fuzzy(model_id, models)

    @staticmethod
    def _find_exact(model_id: str, models: list[dict]) -> dict | None:
        for m in models:
            if m["id"] == model_id:
                return m
        return None

    @staticmethod
    def _find_best_fuzzy(model_id: str, models: list[dict]) -> dict | None:
        return find_best_model_match(model_id, models)

    def filter_free(self, force_refresh: bool = False) -> list[dict]:
        models = self.fetch_models(force_refresh)
        return [m for m in models if ":free" in m["id"]]

    def filter_by_parameters(self, params: list[str], force_refresh: bool = False) -> list[dict]:
        models = self.fetch_models(force_refresh)
        result = []
        for m in models:
            supported = m.get("supported_parameters", []) or []
            if all(p in supported for p in params):
                result.append(m)
        return result

    def sort_by(self, sort_key: str, limit: int = 30, force_refresh: bool = False) -> list[dict]:
        valid_sorts = {
            "pricing-low-to-high",
            "pricing-high-to-low",
            "context-high-to-low",
            "throughput-high-to-low",
            "latency-low-to-high",
            "most-popular",
            "top-weekly",
            "newest",
        }
        if sort_key not in valid_sorts:
            sort_key = "pricing-low-to-high"

        try:
            resp = httpx.get(
                API_URL,
                params={"sort": sort_key, "limit": limit},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except Exception:
            models = self.fetch_models(force_refresh)
            return self._sort_locally(models, sort_key)[:limit]

    def _api_fetch(self) -> list[dict]:
        resp = httpx.get(API_URL, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])

    def _load_cache(self) -> list[dict] | None:
        if not CACHE_FILE.exists():
            return None
        try:
            with open(CACHE_FILE) as f:
                cached = json.load(f)
            age = time.time() - cached.get("_fetched_at", 0)
            if age < self.cache_ttl:
                return cached.get("data", [])
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    def _save_cache(self, models: list[dict]) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump({"_fetched_at": time.time(), "data": models}, f)

    def clear_cache(self) -> None:
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
        self._models = None

    def _sort_locally(self, models: list[dict], sort_key: str) -> list[dict]:
        def pricing_weight(m: dict) -> float:
            p = m.get("pricing", {})
            prompt = float(p.get("prompt", 0) or 0)
            completion = float(p.get("completion", 0) or 0)
            return (prompt + completion) / 2

        key_funcs = {
            "pricing-low-to-high": lambda m: pricing_weight(m),
            "pricing-high-to-low": lambda m: -pricing_weight(m),
            "context-high-to-low": lambda m: -(m.get("context_length", 0) or 0),
            "newest": lambda m: -(m.get("created", 0) or 0),
        }

        fn = key_funcs.get(sort_key, lambda m: pricing_weight(m))
        return sorted(models, key=fn)
