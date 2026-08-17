# or-pricer

OpenRouter model pricing at your fingertips — CLI tool + MCP server.

No API key needed. No browser. Just prices.

## Install

```bash
git clone https://github.com/viperdriver2000/or-pricer.git
cd or-pricer
pip install httpx    # only dependency
```

Or with uv:
```bash
uv tool install --from git+https://github.com/viperdriver2000/or-pricer.git
```

## Quick Start

```bash
./or-pricer                  # dashboard of all watch groups (provider + opencode cmd per row)
./or-pricer -t               # top 20 most-used models
./or-pricer -c               # cheapest 30 models
./or-pricer -g china         # chinese models
./or-pricer -g us            # google / openai / anthropic / meta / xai
./or-pricer -g privacy       # zero-retention, no-training providers
./or-pricer -s "claude"      # search by name
./or-pricer -p deepseek/deepseek-v4-pro   # hosting providers + privacy flags
./or-pricer --free           # free models only
./or-pricer --pick           # interactive pick → opencode -m ...
```

## CLI

```
Usage: or-pricer [OPTIONS]

Without options: dashboard overview of all watch groups.

Options:
  -g, --group NAME      Show group (china, europe, us, top, free, programming, privacy)
  -t, --trending        Top 20 most-used models
  -c, --cheapest        Cheapest 30 models
  -s, --search TERM     Search by name or description
  -i, --info ID         Detailed info for one model (+ hosting providers)
  -p, --providers ID    Hosting providers for one model with privacy flags
  --free                Free models only (:free variants)
  --supported PARAMS    Filter by supported params (e.g. "tools,temperature")
  --opencode            Print ready-to-use opencode -m commands
  --pick                Interactive selection → prints opencode -m command
  --no-cache            Bypass 12h cache, fetch fresh
  -o, --output FORMAT   Table or JSON output (table|json)
  -h, --help            Show this help
```

### Examples

```bash
# China group, sorted by price (shows provider + opencode command)
$ or-pricer -g china

=== CHINA ===

Provider    Model                               Prompt/1M  Compl/1M  Context  Cache R  Cache W
-----------------------------------------------------------------------------------------------
qwen        qwen/qwen3.7-flash                  $0.03      $0.13     1M       $0.01    $0.04
deepseek    deepseek/deepseek-v4-flash-0731     $0.14      $0.28     1M       $0.02    $-
deepseek    deepseek/deepseek-v4-pro            $1.32      $3.96     1M       $0.04    $-
qwen        qwen/qwen3.7-max                    $1.48      $4.42     1M       $0.29    $1.84

In opencode auswählen: opencode -m openrouter/<model-id>
```

```bash
# Hosting providers with privacy flags
$ or-pricer -p deepseek/deepseek-v4-pro

=== Hoster fuer deepseek/deepseek-v4-pro ===

Provider         Train   Retains   HQ
------------------------------------------
DeepInfra        nein    nein      US
CoreWeave        nein    nein      US
Novita           nein    nein      US
...
DeepSeek         ja      ja        CN   ← trains on inputs

Privacy-freundlich (kein Training, kein Retention): Azure, BaseTen, DeepInfra, Fireworks, ...
Trainiert mit Inputs: DeepSeek
```

```bash
# Ready-to-run opencode commands for all US models
$ or-pricer -g us --opencode
# US
opencode -m openrouter/google/gemma-4-31b-it
opencode -m openrouter/openai/gpt-5-nano
opencode -m openrouter/anthropic/claude-sonnet-5
...
```

## MCP Server

Integrates with [opencode](https://github.com/anomalyco/opencode), Claude Code, and other MCP-compatible tools.

```jsonc
// ~/.config/opencode/opencode.json
{
  "mcp": {
    "or-pricer": {
      "type": "local",
      "command": ["python3", "~/workspace/or-pricer/mcp_server.py"]
    }
  }
}
```

Available tools: `or_show_group`, `or_trending`, `or_cheapest`, `or_search`, `or_model_info`, `or_find_cheapest_for`, `or_refresh`

## Config

Edit `config.json` to customize watch groups:

```json
{
  "groups": {
    "china": [
      "deepseek/deepseek-v4-pro",
      "qwen/qwen3.8-max"
    ],
    "europe": [
      "mistralai/mistral-small-3.1-24b-instruct"
    ],
    "my-models": [
      "openai/gpt-4o",
      "anthropic/claude-sonnet-5"
    ]
  },
  "cache_ttl_hours": 12
}
```

## How It Works

- Queries the **free** OpenRouter API at `/api/v1/models` (no auth required)
- Caches results locally for 12 hours (`~/.cache/or-pricer/cache.json`)
- Hosting providers + privacy flags per model from the OpenRouter model page (`~/.cache/or-pricer/providers.json`)
- Privacy classification: providers with zero data retention and no training on inputs
- Provider region classification: Europe, USA, China, Asia

## Tests

```bash
python3 tests/test_matching.py
```

## Requirements

- Python 3.12+
- `httpx` (CLI), `mcp` (optional, for MCP server: `pip install ".[mcp]"`)

## License

MIT
