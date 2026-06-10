---
layout: default
title: Setup Guide
---

<a href="{{ site.baseurl }}/" style="font-size:14px;">← Pergamon Docs Agent</a>

# Pergamon Docs Agent — Setup Guide

## Prerequisites

- **Mac** with Python 3.9+
- Active accounts with:
  - OpenAI (API access)
  - Zendesk (admin access to pergamonlabshelp)
  - Slack (bot token for #release channel)
  - Synthesia (API access)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/pergamonian87/pergamon-docs-agent-.git
cd pergamon-docs-agent-
```

### 2. Install dependencies

```bash
pip3 install -r requirements.txt
```

| Package | Purpose |
|---|---|
| `openai` | GPT-4o inference engine |
| `python-dotenv` | Loads `.env` credentials |
| `requests` | HTTP calls to Zendesk, Slack, Synthesia |
| `rich` | Terminal UI — panels, prompts, tables |
| `beautifulsoup4` | HTML parsing |
| `html2text` | HTML to readable text for diff display |
| `pypdf` | Parse PDF files dropped via `/doc` |
| `python-docx` | Parse DOCX files dropped via `/doc` |
| `ddgs` | DuckDuckGo search — used by `--new` and `--rewrite` for pre-draft research (no API key required) |

---

## Configuration

All credentials live in `.env` in the project root. Never commit this file.

### `.env` file

```
ZENDESK_SUBDOMAIN=pergamonlabshelp
ZENDESK_EMAIL=rakesh.ghatvisave@pergamon-labs.com
ZENDESK_API_TOKEN=your_zendesk_token

OPENAI_API_KEY=your_openai_key

SYNTHESIA_API_KEY=your_synthesia_key

SLACK_BOT_TOKEN=xoxb-your-token
SLACK_RELEASE_CHANNEL_ID=C089EBK20G0
```

### Where to get each credential

| Credential | Where to get it |
|---|---|
| `ZENDESK_API_TOKEN` | Zendesk Admin → Apps & Integrations → APIs → Zendesk API → Add API token |
| `OPENAI_API_KEY` | platform.openai.com → API Keys |
| `SYNTHESIA_API_KEY` | Synthesia dashboard → API settings |
| `SLACK_BOT_TOKEN` | api.slack.com/apps → your app → OAuth & Permissions → Bot Token |
| `SLACK_RELEASE_CHANNEL_ID` | Slack → right-click #release channel → View channel details → Channel ID |

---

## Slack Bot Setup

1. Go to **api.slack.com/apps**
2. Click **Create New App** → From scratch
3. Name: `Pergamon Docs Agent`, select your Pergamon workspace
4. Go to **OAuth & Permissions** → Bot Token Scopes → add `channels:history` and `channels:read`
5. Click **Install to Workspace**
6. Copy the **Bot OAuth Token** (`xoxb-...`) into `.env`
7. Invite the bot to #release: `/invite @pergamon_docs_agent`

---

## CLI Reference

### Release workflows

```bash
# Fetch latest release thread from Slack
python3 main.py

# Skip Slack — paste release notes manually
python3 main.py --manual

# Target a specific release version
python3 main.py --version 3.9.0

# Re-parse a thread for new comments since last run
python3 main.py --refresh --version 3.9.0
```

### Article creation

```bash
# Create a new article from a Zendesk support ticket
python3 main.py --ticket 12345

# Create a new article ad-hoc
python3 main.py --new "How to export a publication in the background"
```

### Article editing

```bash
# Rewrite an existing article by title
python3 main.py --rewrite "How to export a publication"

# Rewrite an existing article by Zendesk article ID
python3 main.py --rewrite 12345678
```

### Maintenance

```bash
# Audit articles not updated in 6+ months
python3 main.py --staleness

# Customise staleness threshold
python3 main.py --staleness --months 3

# Rollback a specific article
python3 main.py --rollback 12345678
```

### Quality skills

```bash
# AEO audit — scan all articles, report missing TL;DR / FAQ / schema
python3 main.py --audit

# Limit audit to the N most recently updated articles
python3 main.py --audit --audit-limit 20

# Style lint — review a single article against Stripe docs conventions
python3 main.py --lint "How to export a publication"
python3 main.py --lint 16413268283023

# AEO retrofit — bulk-add TL;DR, FAQ, and schema to articles flagged by audit
python3 main.py --aeo-retrofit
python3 main.py --aeo-retrofit 16413268283023,16413268283024
```

---

## Context Injection

At any `Your response:` prompt during a run, you can inject additional context inline:

| Command | What it does |
|---|---|
| `/img path/to/screen.png` | Loads screenshot as GPT-4o vision input. Agent analyzes the UI and uses it for step content. Image is uploaded to Zendesk and embedded in the article. |
| `/doc path/to/doc.md` | Loads an engineering doc (MD, TXT, RST, PDF, DOCX). Agent translates to end-user language — never exposes technical internals. |
| `/note your message` | Injects a side note into the next agent response without submitting your main answer. |

Multiple `/img` and `/doc` commands can appear in a single input. Backslash-escaped paths (`path\ with\ spaces`) are handled automatically.

**Example:**
```
Your response: /img ~/Screenshots/assembly-report.png /doc ~/eng-docs/qc-feature.md
Analyze these and write the article steps from what you can see.
```

---

## Project Structure

```
pergdocsagent/
├── main.py                  # Agent entry point — all workflows
├── CLAUDE.md                # Persistent memory — product knowledge, Stripe style guide, AEO rules
├── .env                     # API credentials (never commit)
├── changelog.md             # Auto-generated audit trail
├── llms.txt                 # Auto-generated AI crawler index
├── requirements.txt         # Python dependencies
├── tools/
│   ├── zendesk.py           # Zendesk Help Center + Support API
│   ├── slack.py             # Slack API + thread state management
│   └── synthesia.py         # Synthesia video generation
├── drafts/
│   ├── slack_state.json     # Last-parsed timestamp per version (enables --refresh)
│   └── article_*.json       # Local backup of articles that failed to publish
└── docs/                    # This GitHub Pages site
```
