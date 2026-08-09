import json
import shutil
from typing import Any


def format_price(price_str: str | float | None, per_million: bool = True) -> str:
    if price_str is None or price_str == "":
        return "$-"
    try:
        val = float(price_str)
    except (ValueError, TypeError):
        return "$-"
    if val == 0:
        return "$0"
    if per_million:
        val *= 1_000_000
    if val < 0.01:
        return f"${val:.4f}"
    if val < 1:
        return f"${val:.2f}"
    return f"${val:.2f}"


def format_context(ctx: int | None) -> str:
    if ctx is None:
        return "-"
    if ctx >= 1_000_000:
        return f"{ctx / 1_000_000:.0f}M"
    if ctx >= 1_000:
        return f"{ctx / 1_000:.0f}K"
    return str(ctx)


def format_table(
    models: list[dict],
    columns: list[str] | None = None,
    max_width_id: int = 45,
) -> str:
    if not models:
        return "Keine Modelle gefunden."

    if columns is None:
        columns = ["id", "prompt", "completion", "context", "cache_read", "cache_write"]

    headers = {
        "id": "Model",
        "prompt": "Prompt/1M",
        "completion": "Compl/1M",
        "context": "Context",
        "cache_read": "Cache R",
        "cache_write": "Cache W",
        "provider": "Provider",
        "region": "Region",
    }

    header_names = [headers.get(c, c) for c in columns]

    col_widths = {}
    for c in columns:
        col_widths[c] = len(headers.get(c, c))

    rows = []
    for m in models:
        p = m.get("pricing", {}) or {}
        row = {
            "id": m["id"],
            "prompt": format_price(p.get("prompt")),
            "completion": format_price(p.get("completion")),
            "context": format_context(m.get("context_length")),
            "cache_read": format_price(p.get("input_cache_read")),
            "cache_write": format_price(p.get("input_cache_write")),
            "provider": m["id"].split("/")[0].lstrip("~") if "/" in m["id"] else "-",
            "region": _region_label(m["id"]),
        }
        for c in columns:
            width = len(str(row[c]))
            if c == "id":
                width = min(width, max_width_id)
            if width > col_widths.get(c, 0):
                col_widths[c] = width
        rows.append(row)

    col_widths["id"] = min(col_widths["id"], max_width_id)

    def format_row(row: dict) -> str:
        parts = []
        for c in columns:
            val = str(row[c])
            if c == "id":
                val = val[:max_width_id]
            parts.append(val.ljust(col_widths[c] + 2))
        return "".join(parts)

    header_line = format_row({c: header_names[i] for i, c in enumerate(columns)})

    lines = [header_line, "-" * len(header_line)]
    for row in rows:
        lines.append(format_row(row))

    return "\n".join(lines)


def format_model_detail(model: dict) -> str:
    p = model.get("pricing", {}) or {}
    arch = model.get("architecture", {}) or {}
    tp = model.get("top_provider", {}) or {}

    parts = [
        f"Name:        {model['id']}",
        f"Full Name:   {model.get('name', '-')}",
        f"Created:     {model.get('created', '-')}",
        f"Context:     {format_context(model.get('context_length'))}",
        f"Max Output:  {tp.get('max_completion_tokens', '-')}",
        f"Moderated:   {tp.get('is_moderated', '-')}",
        f"",
        f"--- Pricing (per 1M tokens) ---",
        f"  Prompt:           {format_price(p.get('prompt'))}",
        f"  Completion:       {format_price(p.get('completion'))}",
        f"  Request:          {format_price(p.get('request'))}",
        f"  Image:            {format_price(p.get('image'))}",
        f"  Web Search:       {format_price(p.get('web_search'))}",
        f"  Internal Reason.: {format_price(p.get('internal_reasoning'))}",
        f"  Cache Read:       {format_price(p.get('input_cache_read'))}",
        f"  Cache Write:      {format_price(p.get('input_cache_write'))}",
        f"",
        f"--- Capabilities ---",
        f"  Input:  {', '.join(arch.get('input_modalities', ['-']))}",
        f"  Output: {', '.join(arch.get('output_modalities', ['-']))}",
        f"  Tokenizer: {arch.get('tokenizer', '-')}",
        f"  Params:   {', '.join(model.get('supported_parameters', []) or [])}",
        f"",
        f"--- Description ---",
        f"  {model.get('description', '-')[:300]}",
    ]

    overrides = p.get("overrides", [])
    if overrides:
        parts.append("")
        parts.append("--- Pricing Overrides ---")
        for i, ov in enumerate(overrides):
            parts.append(f"  Override #{i + 1}:")
            if "min_prompt_tokens" in ov:
                parts.append(f"    Min Prompt Tokens: {ov['min_prompt_tokens']}")
            if "utc_start" in ov:
                parts.append(f"    Time: {ov['utc_start']:04d}-{ov['utc_end']:04d} UTC")
            for k, v in ov.items():
                if k not in ("min_prompt_tokens", "utc_start", "utc_end"):
                    parts.append(f"    {k}: {format_price(v)}")

    return "\n".join(parts)


def format_summary(groups: dict[str, list[str]], models: list[dict]) -> str:
    model_map = {m["id"]: m for m in models}

    lines = []
    for group_name, model_ids in groups.items():
        lines.append(f"=== {group_name.upper()} ===")
        found = []
        for mid in model_ids:
            m = model_map.get(mid)
            if m is None:
                m = _find_best_match(mid, models)
            if m:
                found.append(m)

        if found:
            found.sort(key=_pricing_sort_key)
            for m in found:
                p = m.get("pricing", {}) or {}
                prompt = format_price(p.get("prompt"))
                compl = format_price(p.get("completion"))
                ctx = format_context(m.get("context_length"))
                lines.append(f"  {m['id']:<48} {prompt:>8}/{compl:<8} {ctx:>6} ctx")
        else:
            lines.append("  (keine Modelle)")
        lines.append("")

    return "\n".join(lines)


def _pricing_sort_key(m: dict) -> float:
    p = m.get("pricing", {}) or {}
    prompt = float(p.get("prompt", 0) or 0)
    completion = float(p.get("completion", 0) or 0)
    return (prompt + completion) / 2


def _find_best_match(model_id: str, models: list[dict]) -> dict | None:
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
        if m["id"].startswith(base) and ":" not in m["id"].split("/", 1)[1] if "/" in m["id"] else True:
            return m
    for m in models:
        if m["id"].startswith(base):
            return m
    return None


def _region_label(model_id: str) -> str:
    from .config import get_provider_region

    r = get_provider_region(model_id)
    labels = {"europe": "EU", "usa": "US", "china": "CN", "asia": "AS", "other": "--"}
    return labels.get(r, "--")


def to_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)
