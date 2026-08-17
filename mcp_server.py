#!/usr/bin/env python3
"""
OpenRouter Pricer — MCP Server

Stellt die or-pricer Funktionalität als MCP-Tools für opencode bereit.
"""

import json
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR))

from mcp.server.fastmcp import FastMCP
from or_pricer.models import OpenRouterClient
from or_pricer.config import load_config, get_groups, get_cache_ttl
from or_pricer.display import format_table, format_model_detail

mcp = FastMCP("OpenRouter Pricer")
client = OpenRouterClient(cache_ttl_hours=get_cache_ttl(load_config()))


@mcp.tool()
def or_list_groups() -> str:
    """Alle Watch-Gruppen aus der Config auflisten."""
    config = load_config()
    groups = get_groups(config)
    result = {}
    for name, ids in groups.items():
        result[name] = {"count": len(ids), "models": ids}
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def or_show_group(group: str, refresh: bool = False) -> str:
    """Modelle einer Watch-Gruppe mit Preisen anzeigen.

    Args:
        group: Gruppenname (z.B. 'china', 'europe', 'google', 'free', 'top', 'programming', 'privacy')
        refresh: Cache ignorieren und frisch von API laden
    """
    config = load_config()
    groups = get_groups(config)
    if group not in groups:
        return json.dumps({"error": f"Unbekannte Gruppe '{group}'. Verfügbar: {', '.join(sorted(groups.keys()))}"})
    
    model_ids = groups[group]
    all_models = client.fetch_models(force_refresh=refresh)
    model_map = {m["id"]: m for m in all_models}
    
    models = []
    for mid in model_ids:
        m = model_map.get(mid) or model_map.get(f"~{mid}")
        if m is None:
            base = mid.split(":")[0].lstrip("~")
            m = model_map.get(base) or model_map.get(f"~{base}")
        if m is None:
            for mm in all_models:
                if mm["id"].startswith(base):
                    m = mm
                    break
        if m:
            models.append(m)
    
    models.sort(key=lambda m: (float((m.get("pricing", {}) or {}).get("prompt", 0) or 0) +
                                float((m.get("pricing", {}) or {}).get("completion", 0) or 0)) / 2)
    
    return f"=== {group.upper()} ===\n\n{format_table(models)}"


@mcp.tool()
def or_trending(limit: int = 20, refresh: bool = False) -> str:
    """Top meistgenutzte Modelle auf OpenRouter.

    Args:
        limit: Anzahl Modelle (default 20)
        refresh: Cache ignorieren
    """
    models = client.sort_by("most-popular", limit=limit, force_refresh=refresh)
    return f"=== Top {limit} Meistgenutzte ===\n\n{format_table(models)}"


@mcp.tool()
def or_cheapest(limit: int = 30, refresh: bool = False) -> str:
    """Günstigste Modelle auf OpenRouter.

    Args:
        limit: Anzahl Modelle (default 30)
        refresh: Cache ignorieren
    """
    models = client.sort_by("pricing-low-to-high", limit=limit, force_refresh=refresh)
    return f"=== Günstigste {limit} Modelle ===\n\n{format_table(models)}"


@mcp.tool()
def or_search(term: str, refresh: bool = False) -> str:
    """Suche nach Modellen auf OpenRouter.

    Args:
        term: Suchbegriff (Name, ID oder Beschreibung)
        refresh: Cache ignorieren
    """
    models = client.search(term, force_refresh=refresh)
    models.sort(key=lambda m: (float((m.get("pricing", {}) or {}).get("prompt", 0) or 0) +
                                float((m.get("pricing", {}) or {}).get("completion", 0) or 0)) / 2)
    return f"=== Suche: '{term}' ({len(models)} Treffer) ===\n\n{format_table(models)}"


@mcp.tool()
def or_model_info(model_id: str, refresh: bool = False) -> str:
    """Detail-Informationen zu einem Modell.

    Args:
        model_id: Modell-ID (z.B. 'deepseek/deepseek-v4-pro')
        refresh: Cache ignorieren
    """
    model = client.get_model(model_id, force_refresh=refresh)
    if model is None:
        return f"Modell '{model_id}' nicht gefunden."
    return format_model_detail(model)


@mcp.tool()
def or_find_cheapest_for(
    min_context: int = 128000,
    require_tools: bool = False,
    require_reasoning: bool = False,
    limit: int = 10,
    refresh: bool = False,
) -> str:
    """Finde das günstigste Modell mit bestimmten Anforderungen.

    Args:
        min_context: Minimaler Context in Tokens (default 128K)
        require_tools: Tool/Function-Calling erforderlich
        require_reasoning: Reasoning/Thinking erforderlich
        limit: Anzahl Ergebnisse
        refresh: Cache ignorieren
    """
    models = client.fetch_models(force_refresh=refresh)
    
    filtered = []
    for m in models:
        ctx = m.get("context_length", 0) or 0
        if ctx < min_context:
            continue
        
        params = m.get("supported_parameters", []) or []
        if require_tools and "tools" not in params:
            continue
        if require_reasoning and "reasoning" not in params:
            continue
        
        p = m.get("pricing", {}) or {}
        price = (float(p.get("prompt", 0) or 0) + float(p.get("completion", 0) or 0)) / 2
        filtered.append((price, m))
    
    filtered.sort(key=lambda x: x[0])
    result = [m for _, m in filtered[:limit]]
    
    return f"=== Günstigste Modelle (ctx>={min_context//1000}K, tools={require_tools}, reasoning={require_reasoning}) ===\n\n{format_table(result)}"


@mcp.tool()
def or_refresh() -> str:
    """Cache leeren und Modell-Daten neu von OpenRouter laden."""
    client.clear_cache()
    models = client.fetch_models(force_refresh=True)
    return f"Cache geleert. {len(models)} Modelle neu geladen."


if __name__ == "__main__":
    mcp.run()
