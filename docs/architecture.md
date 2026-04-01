---
layout: default
title: Architecture
---

# Pergamon Docs Agent — Architecture

## Overview

The Pergamon Docs Agent is an AI-powered documentation automation system that monitors Slack for product release announcements and automatically updates, creates, and publishes Zendesk help articles — maintaining Pergamon's documentation standards, AEO compliance, and release notes format throughout.

It is built as a Python application running locally on a Mac, using the OpenAI GPT-4o model for intelligence and calling external APIs (Zendesk, Slack, Synthesia) as tools.

---

## System Diagram

<div class="mermaid">
%%{init: {"theme": "base", "themeVariables": {"primaryColor": "#eef3f8", "primaryBorderColor": "#1f73b7", "primaryTextColor": "#1f2933", "lineColor": "#4b5563", "secondaryColor": "#f0f4ff", "tertiaryColor": "#e8f5e9"}, "flowchart": {"curve": "basis"}} }%%
flowchart TD
    classDef input     fill:#dbeafe,stroke:#1d4ed8,color:#1e3a5f,rx:8
    classDef agent     fill:#1f73b7,stroke:#155e8e,color:#ffffff,font-weight:bold,rx:8
    classDef tool      fill:#ede9fe,stroke:#7c3aed,color:#3b1e6e,rx:8
    classDef human     fill:#fef3c7,stroke:#d97706,color:#78350f,rx:8
    classDef memory    fill:#fce7f3,stroke:#be185d,color:#831843,rx:8
    classDef output    fill:#d1fae5,stroke:#059669,color:#064e3b,rx:8

    SLACK["📢 Slack\n#release"]:::input
    MANUAL["📋 Manual paste\nfallback"]:::input

    subgraph AGENT["  🤖  Pergamon Docs Agent — main.py  "]
        LOOP["GPT-4o\nAgent Loop"]:::agent
    end

    subgraph MEM["  💾  Persistent Memory  "]
        CLAUDE_MD["CLAUDE.md\nStyle · Terminology · AEO"]:::memory
        CHANGELOG["changelog.md\nAudit trail"]:::memory
        LLMS["llms.txt\nAI crawler index"]:::memory
    end

    subgraph TOOLS["  🔧  Tools  "]
        SLACK_TOOL["Slack API\nfetch release thread"]:::tool
        ZD_READ["Zendesk Read\nlist · get · sections"]:::tool
        ZD_WRITE["Zendesk Write\nupdate · create · publish"]:::tool
        SYN["Synthesia API\ncreate release video"]:::tool
    end

    subgraph CP["  🛑  Human Checkpoints  "]
        direction LR
        CP1["① Feature list"]:::human
        CP2["② Feature Q&A"]:::human
        CP3["③ Article discovery"]:::human
        CP4["④ Diff review"]:::human
        CP5["⑤ Publish approval"]:::human
    end

    subgraph OUT["  ✅  Output  "]
        ZD_OUT["Zendesk Help Center\nLive articles"]:::output
        VIDEO["Synthesia\nRelease video"]:::output
        REPORT["Terminal\nPost-publish report"]:::output
    end

    SLACK --> SLACK_TOOL --> LOOP
    MANUAL --> LOOP
    CLAUDE_MD -->|loaded at startup| LOOP
    LOOP --> ZD_READ -->|article content| LOOP
    LOOP --> ZD_WRITE --> ZD_OUT
    LOOP --> SYN --> VIDEO
    LOOP <-->|interactive prompts| CP
    LOOP -->|after publish| CHANGELOG
    LOOP -->|after publish| LLMS
    LOOP --> REPORT
</div>

<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({ startOnLoad: true, securityLevel: 'loose' });</script>

---

## Two-Agent Architecture

The Pergamon system consists of two separate but connected agents:

| Agent | Location | Role |
|---|---|---|
| **Pergamon Docs Agent** | `/pergdocsagent/` | Orchestrator — handles articles, release notes, AEO, changelog, llms.txt |
| **Synthesia Video Agent** | `/synthesi/` | Specialist — called by Docs Agent via API, returns video URL |

The Docs Agent calls the Synthesia API directly using the key in `.env`. No separate process or script needs to be run.

---

## Component Breakdown

### 1. Intelligence Layer — GPT-4o (OpenAI)
The brain of the agent. Responsible for:
- Parsing free-form Slack release notes into structured feature lists
- Deciding which Zendesk articles are affected by a release
- Drafting article updates following Diataxis framework and Pergamon style
- Running AEO pass — TL;DR blocks, FAQ sections, schema markup
- Drafting release notes in Pergamon's standard format
- Managing the conversation flow with the user

**Model:** `gpt-4o`
**Provider:** OpenAI API
**Key:** `OPENAI_API_KEY` in `.env`

---

### 2. Tools Layer — External APIs

| Tool | File | What it does |
|---|---|---|
| `fetch_slack_release_thread` | `tools/slack.py` | Reads latest release thread from #release channel |
| `list_zendesk_articles` | `tools/zendesk.py` | Fetches all 194 article titles and metadata |
| `get_zendesk_article` | `tools/zendesk.py` | Fetches full HTML body of a specific article |
| `get_sections` | `tools/zendesk.py` | Lists all Zendesk sections with IDs |
| `update_zendesk_article` | `tools/zendesk.py` | Saves updated article as draft |
| `create_zendesk_article` | `tools/zendesk.py` | Creates a new article in a specified section |
| `publish_zendesk_article` | `tools/zendesk.py` | Publishes article live (draft: false) |
| `rollback_zendesk_article` | `tools/zendesk.py` | Flags article for rollback |
| `create_release_video` | `tools/synthesia.py` | Calls Synthesia API to create release video |
| `select_article_discovery_method` | `main.py` | Human checkpoint — user chooses how to find impacted articles |
| `ask_user` | `main.py` | Human checkpoint — agent asks user a question |
| `show_diff` | `main.py` | Human checkpoint — shows article changes for review |
| `request_publish_approval` | `main.py` | Human checkpoint — final gate before publishing |
| `save_changelog_entry` | `main.py` | Appends entry to changelog.md |
| `update_llms_txt` | `main.py` | Regenerates llms.txt after publish |

---

### 3. Memory Layer — Persistent Files

| File | Purpose | Updated by |
|---|---|---|
| `CLAUDE.md` | Product knowledge, Pergamon terminology, style guides, AEO rules, callout formats, release notes template, Diataxis templates | Manually by docs team |
| `.env` | API credentials for all integrations | Manually by admin |
| `changelog.md` | Full audit trail of every release processed | Agent after each publish |
| `llms.txt` | AI crawler index — tells GPTBot, ClaudeBot, Perplexity what Pergamon is and where docs live | Agent after each publish |
| `drafts/` | Local backup of articles that failed to publish | Agent on publish failure |

---

### 4. Human in the Loop — 5 Checkpoints

Nothing is published without explicit user approval. The agent pauses at five points:

| Checkpoint | Step | What the user does |
|---|---|---|
| Feature list confirmation | Step 2 | Confirms the parsed feature list is correct |
| Feature description Q&A | Step 3 | Describes how each feature works in plain language |
| Article discovery | Step 4 | Chooses how to find impacted articles (scan / section / direct IDs) |
| Diff review | Step 6 | Reviews proposed changes article by article (approve / skip / edit) |
| Publish approval | Step 7 | Final sign-off before anything goes live |

---

### 5. AEO Layer — AI Readability

Every article the agent writes or updates automatically receives:

| Enhancement | What it adds |
|---|---|
| TL;DR block | 2-3 sentence summary at the top — most likely part AI models cite |
| FAQ section | 3-5 natural language Q&A pairs at the bottom |
| Schema markup | `HowTo` or `FAQPage` JSON-LD injected into article HTML |
| Question-based headings | Vague headings rewritten as specific questions |
| Term definitions | Pergamon-specific terms defined on first use |

---

## Data Flow

```
1. Release notes (Slack or manual paste)
            ↓
2. GPT-4o parses → structured feature list
            ↓
3. User confirms feature list + describes each feature
            ↓
4. User chooses article discovery method
            ↓
5. Agent fetches only confirmed articles (not all 194)
            ↓
6. GPT-4o drafts updates + AEO pass + release notes
            ↓
7. Synthesia API → release video created
            ↓
8. User reviews diffs article by article
            ↓
9. User gives final approval
            ↓
10. Agent publishes to Zendesk (with retry logic)
            ↓
11. changelog.md + llms.txt updated
            ↓
12. Post-publish report in terminal
```

---

## Token Efficiency Design

The agent is designed to minimise API token consumption:

| Design decision | Why |
|---|---|
| Metadata-only scan for article discovery | Fetches titles only (~3K tokens) not full bodies |
| User confirms shortlist before full fetch | Full article bodies (~3K each) only fetched for confirmed articles |
| Three discovery modes | User can skip scanning entirely by providing article IDs directly |
| Sequential article processing | One article at a time — keeps context window manageable |
| CLAUDE.md is the only always-loaded context | No full knowledge base loaded on every run |

---

## Error Handling

| Error | Behaviour |
|---|---|
| Zendesk publish fails | Retries up to 3 times, saves draft locally to `/drafts/` if all fail |
| OpenAI rate limit (429) | Waits 60s per attempt, retries up to 5 times |
| OpenAI overloaded (529) | Waits 30s per attempt, retries up to 5 times |
| Synthesia video fails | Inserts `[VIDEO NEEDED]` placeholder, continues workflow |
| Slack not configured | Falls back to manual paste in terminal |
| Article not found | Agent warns user and skips |
