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
./or-pricer                  # dashboard of your watch groups
./or-pricer -t               # top 20 most-used models
./or-pricer -c               # cheapest 30 models
./or-pricer -g china         # chinese models
./or-pricer -s "claude"      # search by name
./or-pricer --free           # free models only
./or-pricer --pick           # interactive pick → opencode -m ...
```

## CLI

```
Usage: or-pricer [OPTIONS]

Without options: dashboard overview of all watch groups.

Options:
  -g, --group NAME      Show group (china, europe, dsgvo, top, free)
  -t, --trending        Top 20 most-used models
  -c, --cheapest        Cheapest 30 models
  -s, --search TERM     Search by name or description
  -i, --info ID         Detailed info for one model
  --free                Free models only (:free variants)
  --supported PARAMS    Filter by supported params (e.g. "tools,temperature")
  --pick                Interactive selection → prints opencode -m command
  --no-cache            Bypass 12h cache, fetch fresh
  -o, --output FORMAT   Table or JSON output (table|json)
  -h, --help            Show this help
```

### Examples

```bash
# China group, sorted by price
$ or-pricer -g china

=== CHINA ===

Model                               Prompt/1M  Compl/1M  Context  Cache R  Cache W
------------------------------------------------------------------------------------
qwen/qwen3.7-flash                  $0.03      $0.13     1M       $0.01    $0.04
deepseek/deepseek-v4-flash-0731     $0.09      $0.18     1M       $0.02    $-
deepseek/deepseek-v4-pro            $0.43      $0.87     1M       $0.00    $-
qwen/qwen3.7-max                    $1.48      $4.42     1M       $0.29    $1.84
qwen/qwen3.8-max                    $2.00      $6.00     1M       $0.25    $2.50
```

```bash
# Detailed model info
$ or-pricer -i deepseek/deepseek-v4-pro

Name:        deepseek/deepseek-v4-pro
Full Name:   DeepSeek: DeepSeek V4 Pro
Context:     1M
Max Output:  384000

--- Pricing (per 1M tokens) ---
  Prompt:           $0.43
  Completion:       $0.87
  Cache Read:       $0.00
  Cache Write:      $-

--- Capabilities ---
  Input:  text
  Output: text
  Params: tools, reasoning, structured_outputs, temperature, ...
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
- Supports all OpenRouter sort modes: `most-popular`, `pricing-low-to-high`, `newest`, etc.
- Provider region classification: Europe (DSGVO), USA, China, Asia

## Requirements

- Python 3.12+
- `httpx`

## License

MIT
