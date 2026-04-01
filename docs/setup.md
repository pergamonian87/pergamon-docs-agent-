# Pergamon Docs Agent — Setup Guide

## Prerequisites

- **Mac** with Python 3.9+
- **Claude Code CLI** installed (for development and maintenance)
- Active accounts with:
  - OpenAI (API access)
  - Zendesk (admin access to pergamonlabshelp)
  - Slack (bot token for #release channel)
  - Synthesia (API access)

---

## Installation

### 1. Navigate to the project directory

```bash
cd /Users/rakesh/Documents/pergdocsagent
```

### 2. Install dependencies

```bash
pip3 install -r requirements.txt
```

Dependencies installed:
- `anthropic` — Anthropic SDK (kept for future use)
- `openai` — OpenAI SDK (active model)
- `python-dotenv` — loads `.env` credentials
- `requests` — HTTP calls to Zendesk, Slack, Synthesia
- `rich` — terminal UI (panels, prompts, tables)
- `beautifulsoup4` — HTML parsing
- `html2text` — HTML to readable text conversion

---

## Configuration

All credentials live in `.env` in the project root. Never commit this file to git (`.gitignore` is already configured).

### `.env` file

```
ZENDESK_SUBDOMAIN=pergamonlabshelp
ZENDESK_EMAIL=rakesh.ghatvisave@pergamon-labs.com
ZENDESK_API_TOKEN=your_zendesk_token

OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key   # kept for fallback

SYNTHESIA_API_KEY=your_synthesia_key

SLACK_BOT_TOKEN=xoxb-your-token
SLACK_RELEASE_CHANNEL_ID=C089EBK20G0
```

### Where to get each credential

| Credential | Where to get it |
|---|---|
| `ZENDESK_API_TOKEN` | Zendesk Admin → Apps & Integrations → APIs → Zendesk API → Add API token |
| `OPENAI_API_KEY` | platform.openai.com → API Keys |
| `ANTHROPIC_API_KEY` | platform.anthropic.com → API Keys |
| `SYNTHESIA_API_KEY` | Synthesia dashboard → API settings |
| `SLACK_BOT_TOKEN` | api.slack.com/apps → your app → OAuth & Permissions → Bot Token |
| `SLACK_RELEASE_CHANNEL_ID` | Slack → #release channel URL → last path segment starting with `C` |

---

## Slack Bot Setup

1. Go to **api.slack.com/apps**
2. Click **Create New App** → From scratch
3. Name: `Pergamon Docs Agent`
4. Select your Pergamon workspace
5. Go to **OAuth & Permissions** → Bot Token Scopes → add:
   - `channels:history`
   - `channels:read`
6. Click **Install to Workspace**
7. Copy the **Bot OAuth Token** (`xoxb-...`) into `.env`
8. Invite the bot to #release channel: `/invite @Pergamon Docs Agent`

---

## Switching AI Models

The agent currently uses **GPT-4o** (OpenAI). To switch back to Claude:

1. Open `main.py`
2. Change the import:
```python
# OpenAI (current)
from openai import OpenAI
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Anthropic (original — use main_anthropic.py as reference)
import anthropic
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
```
3. Change the model in the agent loop:
```python
# OpenAI
model="gpt-4o"

# Anthropic
model="claude-sonnet-4-6"
```

The original Anthropic version is backed up as `main_anthropic.py`.

---

## Running the Agent

### Full workflow — with Slack
```bash
python3 main.py
```
Fetches the latest release thread from #release channel automatically.

### Manual mode — paste release notes
```bash
python3 main.py --manual
```
Skips Slack. Paste release notes directly into the terminal when prompted.

### Staleness check
```bash
python3 main.py --staleness
```
Scans all 194 Zendesk articles and reports any not updated in 6+ months.

```bash
python3 main.py --staleness --months 3
```
Customise the staleness threshold (default: 6 months).

### Rollback an article
```bash
python3 main.py --rollback 15563866700687
```
Fetches rollback information for the specified article ID.

---

## Tip: Injecting Notes Mid-Workflow

At any `Your response:` prompt during a run, type `/note` followed by your message to inject additional context to the agent without submitting your main answer:

```
Your response: /note the downloads panel is in the top toolbar not the sidebar
✓ Note saved — will be included in next agent response
Your response: Yes, proceed with the update
```

---

## Project Structure

```
pergdocsagent/
├── main.py                  # Main agent — OpenAI version (active)
├── main_anthropic.py        # Backup — original Anthropic/Claude version
├── CLAUDE.md                # Persistent memory — product knowledge + style rules
├── .env                     # API credentials (never commit to git)
├── .gitignore               # Excludes .env and other sensitive files
├── changelog.md             # Auto-generated audit trail of all releases
├── llms.txt                 # Auto-generated AI crawler index
├── requirements.txt         # Python dependencies
├── tools/
│   ├── zendesk.py           # Zendesk API — read, write, publish, rollback
│   ├── slack.py             # Slack API — fetch #release channel thread
│   └── synthesia.py        # Synthesia API — create release highlight videos
├── drafts/                  # Local backup of failed publish attempts
├── docs/
│   ├── architecture.md      # System design and component breakdown (this area)
│   ├── setup.md             # Installation and configuration guide
│   └── workflow.md          # 9-step workflow and human checkpoints
└── architecture.md          # Mermaid diagram (original)
```
