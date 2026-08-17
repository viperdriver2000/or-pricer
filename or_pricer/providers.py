import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

CACHE_DIR = Path.home() / ".cache" / "or-pricer"
CACHE_FILE = CACHE_DIR / "providers.json"


def fetch_model_providers(model_id: str, force_refresh: bool = False) -> dict[str, Any] | None:
    """Fetch hosting providers for one model from its OpenRouter page.

    Returns dict with 'model', 'providers' (list of {name, training, retains, hq}),
    and '_fetched_at'. None on failure.
    """
    cache = _load_cache()
    if not force_refresh and cache and model_id in cache:
        return cache[model_id]

    author, slug = _split_model_id(model_id)
    url = f"https://openrouter.ai/{author}/{slug}"
    try:
        resp = httpx.get(url, timeout=45, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        html = resp.text
    except Exception as exc:
        return {"model": model_id, "providers": [], "error": str(exc)}

    providers = _extract_providers(html)

    result = {
        "model": model_id,
        "providers": providers,
        "_fetched_at": time.time(),
    }
    _save_cache(model_id, result)
    return result


def _split_model_id(model_id: str) -> tuple[str, str]:
    model_id = model_id.lstrip("~")
    if "/" in model_id:
        author, slug = model_id.split("/", 1)
    else:
        author, slug = model_id, ""
    slug = slug.split(":")[0] if ":" in slug else slug
    return author, slug


def _extract_providers(html: str) -> list[dict[str, Any]]:
    providers: dict[str, dict[str, Any]] = {}
    pat = re.compile(r'provider_name\\":\\"([^\\"]+)\\",\\"provider_info\\":\{(.*?)\}\}', re.S)
    for m in pat.finditer(html):
        name = m.group(1)
        info = m.group(2)
        if name in providers:
            continue
        t = re.search(r'\\"training\\":(true|false)', info)
        r = re.search(r'\\"retainsPrompts\\":(true|false)', info)
        hq = re.search(r'\\"headquarters\\":\\"([^\\"]+)', info)
        providers[name] = {
            "name": name,
            "training": t.group(1) if t else None,
            "retains": r.group(1) if r else None,
            "hq": hq.group(1) if hq else "?",
        }
    return list(providers.values())


def _load_cache() -> dict[str, Any]:
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(model_id: str, data: dict[str, Any]) -> None:
    cache = _load_cache()
    cache[model_id] = data
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


def format_providers_table(data: dict[str, Any]) -> str:
    providers = data.get("providers", [])
    if not providers:
        err = data.get("error")
        return f"Keine Provider-Daten fuer {data.get('model')}." + (f" ({err})" if err else "")

    lines = [f"=== Hoster fuer {data.get('model')} ===", ""]
    lines.append(f"{'Provider':<16} {'Train':<7} {'Retains':<9} {'HQ':<4}")
    lines.append("-" * 42)

    for p in providers:
        train = "nein" if p["training"] == "false" else ("ja" if p["training"] == "true" else "?")
        retains = "nein" if p["retains"] == "false" else ("ja" if p["retains"] == "true" else "?")
        hq = p.get("hq", "?")
        lines.append(f"{p['name']:<16} {train:<7} {retains:<9} {hq:<4}")

    priv = [p["name"] for p in providers if p["training"] == "false" and p["retains"] == "false"]
    if priv:
        lines.append("")
        lines.append("Privacy-freundlich (kein Training, kein Retention): " + ", ".join(sorted(priv)))

    train_y = [p["name"] for p in providers if p["training"] == "true"]
    if train_y:
        lines.append("")
        lines.append("Trainiert mit Inputs: " + ", ".join(sorted(train_y)))

    return "\n".join(lines)
