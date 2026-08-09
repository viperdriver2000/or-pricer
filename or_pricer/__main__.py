#!/usr/bin/env python3
import argparse
import shutil
import sys

from .config import load_config, get_groups, get_cache_ttl
from .display import format_table, format_model_detail, format_summary, to_json
from .models import OpenRouterClient


def main() -> None:
    config = load_config()

    parser = argparse.ArgumentParser(
        prog="or-pricer",
        description="OpenRouter Model Pricing — Preise checken und Modelle vergleichen.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  or-pricer                           Dashboard-Uebersicht aller Watch-Gruppen
  or-pricer -g china                  China-Modelle mit Preisen
  or-pricer -g europe                 EU-Modelle
  or-pricer -t                        Top 20 meistgenutzte
  or-pricer -c                        Guenstigste 30 Modelle
  or-pricer -s "gemini"               Suche nach Namen
  or-pricer -i deepseek/deepseek-v4-pro  Detail-Ansicht
  or-pricer --free                    Nur :free-Modelle
  or-pricer --pick                    Interaktive Auswahl -> opencode -m ...
  or-pricer --no-cache                Cache ignorieren
  or-pricer -o json -g china          JSON-Ausgabe
        """,
    )

    parser.add_argument(
        "-g", "--group",
        help="Zeige Watch-Gruppe (Name aus config.json)",
    )
    parser.add_argument(
        "-t", "--trending",
        action="store_true",
        help="Top 20 meistgenutzte Modelle",
    )
    parser.add_argument(
        "-c", "--cheapest",
        action="store_true",
        help="Guenstigste 30 Modelle",
    )
    parser.add_argument(
        "-s", "--search",
        metavar="TERM",
        help="Suche nach Modellname oder Beschreibung",
    )
    parser.add_argument(
        "-i", "--info",
        metavar="ID",
        help="Detail-Ansicht eines Modells",
    )
    parser.add_argument(
        "--free",
        action="store_true",
        help="Nur :free-Modelle",
    )
    parser.add_argument(
        "--supported",
        metavar="PARAMS",
        help="Nur Modelle mit bestimmten Parametern (z.B. 'tools,temperature')",
    )
    parser.add_argument(
        "--pick",
        action="store_true",
        help="Interaktive Auswahl -> zeigt opencode -m Befehl",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        dest="no_cache",
        help="Cache ignorieren, frisch von API laden",
    )
    parser.add_argument(
        "-o", "--output",
        choices=["table", "json"],
        default="table",
        help="Ausgabeformat (table|json)",
    )

    args = parser.parse_args()
    ttl = get_cache_ttl(config)
    client = OpenRouterClient(cache_ttl_hours=ttl)
    force_refresh = args.no_cache

    if args.info:
        model = client.get_model(args.info, force_refresh)
        if model:
            if args.output == "json":
                print(to_json(model))
            else:
                print(format_model_detail(model))
        else:
            print(f"Modell '{args.info}' nicht gefunden.", file=sys.stderr)
            sys.exit(1)
        return

    if args.free:
        models = client.filter_free(force_refresh)
        models.sort(key=_sort_key)
        if args.output == "json":
            print(to_json(models))
        else:
            print(format_table(models))
        return

    if args.supported:
        params = [p.strip() for p in args.supported.split(",")]
        models = client.filter_by_parameters(params, force_refresh)
        models.sort(key=_sort_key)
        if args.output == "json":
            print(to_json(models))
        else:
            print(format_table(models))
        return

    if args.trending:
        models = client.sort_by("most-popular", limit=20, force_refresh=force_refresh)
        if args.output == "json":
            print(to_json(models))
        else:
            print(f"=== Top 20 Meistgenutzte ===\n")
            print(format_table(models))
        return

    if args.cheapest:
        models = client.sort_by("pricing-low-to-high", limit=30, force_refresh=force_refresh)
        if args.output == "json":
            print(to_json(models))
        else:
            print(f"=== Guenstigste 30 Modelle ===\n")
            print(format_table(models))
        return

    if args.group:
        groups = get_groups(config)
        if args.group not in groups:
            names = ", ".join(sorted(groups.keys()))
            print(f"Unbekannte Gruppe '{args.group}'. Verfuegbar: {names}", file=sys.stderr)
            sys.exit(1)
        model_ids = groups[args.group]
        all_models = client.fetch_models(force_refresh)
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
        models.sort(key=_sort_key)

        if args.output == "json":
            print(to_json(models))
        else:
            print(f"=== {args.group.upper()} ===\n")
            print(format_table(models))
        return

    if args.search:
        models = client.search(args.search, force_refresh)
        models.sort(key=_sort_key)
        if args.output == "json":
            print(to_json(models))
        else:
            print(f"=== Suche: '{args.search}' ({len(models)} Treffer) ===\n")
            print(format_table(models))
        return

    if args.pick:
        _interactive_pick(client, force_refresh)
        return

    groups = get_groups(config)
    if groups:
        models = client.fetch_models(force_refresh)
        if args.output == "json":
            result = {}
            for gname, mids in groups.items():
                model_map = {m["id"]: m for m in models}
                result[gname] = [model_map[mid] for mid in mids if mid in model_map]
            print(to_json(result))
        else:
            print(format_summary(groups, models))
    else:
        print("Keine Watch-Gruppen in config.json definiert.")
        print("Verfuegbare Optionen: --trending, --cheapest, --search, --free\n")


def _sort_key(m: dict) -> float:
    p = m.get("pricing", {}) or {}
    prompt = float(p.get("prompt", 0) or 0)
    completion = float(p.get("completion", 0) or 0)
    return (prompt + completion) / 2


def _interactive_pick(client: OpenRouterClient, force_refresh: bool) -> None:
    models = client.fetch_models(force_refresh)
    models.sort(key=_sort_key)

    term_width = shutil.get_terminal_size().columns
    max_id = max(40, term_width - 40)

    print("Verfuegbare Modelle (sortiert nach Preis):\n")
    for i, m in enumerate(models):
        p = m.get("pricing", {}) or {}
        prompt = float(p.get("prompt", 0) or 0) * 1_000_000
        compl = float(p.get("completion", 0) or 0) * 1_000_000
        ctx = m.get("context_length", 0) or 0
        if ctx >= 1_000_000:
            ctx_s = f"{ctx // 1_000_000}M"
        elif ctx >= 1_000:
            ctx_s = f"{ctx // 1_000}K"
        else:
            ctx_s = str(ctx)
        mid = m["id"][:max_id]
        print(f"  {i:>3}: {mid:<{max_id + 2}} ${prompt:.2f}/${compl:.2f}  {ctx_s} ctx")

    print(f"\n0-{len(models) - 1} zum Auswaehlen, oder 'q' zum Abbrechen, oder Modell-ID eingeben:")
    choice = input("> ").strip()

    if choice.lower() == "q":
        print("Abgebrochen.")
        return

    selected = None
    if choice.isdigit():
        idx = int(choice)
        if 0 <= idx < len(models):
            selected = models[idx]
    else:
        for m in models:
            if m["id"] == choice:
                selected = m
                break

    if selected:
        print(f"\nopencode -m openrouter/{selected['id']}")
    else:
        print("Kein gueltiges Modell.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
