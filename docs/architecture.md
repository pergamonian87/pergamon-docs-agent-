---
layout: default
title: Architecture
---

<a href="{{ site.baseurl }}/" style="font-size:14px;">← Pergamon Docs Agent</a>

# Pergamon Docs Agent — Architecture

## Overview

The Pergamon Docs Agent is a Python CLI that automates Zendesk help center publishing for Pergamon Labs. It runs locally on a Mac, uses GPT-4o for inference, and calls external APIs as tools. Five independent workflows share the same agent loop, tool layer, and human checkpoint pattern.

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

    SLACK["📢 Slack #release"]:::input
    MANUAL["📋 Manual paste"]:::input
    TICKET["🎫 Zendesk ticket"]:::input
    NEW["✏️ --new title"]:::input
    REWRITE["🔄 --rewrite article"]:::input

    subgraph AGENT["  🤖  Pergamon Docs Agent — main.py  "]
        LOOP["GPT-4o\nAgent Loop"]:::agent
    end

    subgraph MEM["  💾  Persistent Memory  "]
        CLAUDE_MD["CLAUDE.md\nStripe style · Terminology · AEO"]:::memory
        CHANGELOG["changelog.md"]:::memory
        LLMS["llms.txt"]:::memory
        STATE["drafts/slack_state.json\nRefresh timestamps"]:::memory
    end

    subgraph TOOLS["  🔧  Tools  "]
        SLACK_TOOL["Slack API\nfetch thread · fetch updates"]:::tool
        ZD_READ["Zendesk Read\nlist · get · sections"]:::tool
        ZD_WRITE["Zendesk Write\nupdate · create · publish"]:::tool
        ZD_IMG["Zendesk Attachments\nupload screenshots → CDN URL"]:::tool
        ZD_TICKET["Zendesk Support\nread ticket · post internal note"]:::tool
        SYN["Synthesia API\ncreate release video"]:::tool
        SEARCH["DuckDuckGo Search\npre-draft research (--new · --rewrite)"]:::tool
    end

    subgraph CP["  🛑  Human Checkpoints  "]
        direction LR
        CP1["① Confirm\nfeatures / goal"]:::human
        CP2["② Describe\nfeatures"]:::human
        CP3["③ Article\ndiscovery"]:::human
        CP4["④ Diff\nreview"]:::human
        CP5["⑤ Publish\napproval"]:::human
        CP6["⑥ Post-publish\nrefinement"]:::human
    end

    INJECT["💉 Context injection\n/img screenshots\n/doc engineering docs"]:::input

    subgraph OUT["  ✅  Output  "]
        ZD_OUT["Zendesk Help Center\nLive articles with embedded screenshots"]:::output
        VIDEO["Synthesia\nRelease video"]:::output
        REPORT["Terminal\nPost-publish report"]:::output
    end

    SLACK --> SLACK_TOOL --> LOOP
    MANUAL & TICKET & NEW & REWRITE --> LOOP
    CLAUDE_MD -->|loaded at startup| LOOP
    INJECT -->|grounded context| LOOP
    LOOP --> ZD_READ -->|article content| LOOP
    LOOP --> ZD_WRITE --> ZD_OUT
    LOOP --> ZD_IMG --> ZD_OUT
    LOOP --> ZD_TICKET
    LOOP --> SYN --> VIDEO
    LOOP --> SEARCH
    LOOP <-->|interactive prompts| CP
    STATE <-->|read / write| LOOP
    LOOP -->|after refinement loop| CHANGELOG
    LOOP -->|after refinement loop| LLMS
    LOOP --> REPORT
</div>

<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({ startOnLoad: true, securityLevel: 'loose' });</script>

---

## Workflows

| Trigger | Command | What it does |
|---|---|---|
| Release workflow | `python3 main.py` | Reads Slack, updates KB articles + release notes |
| Manual release | `python3 main.py --manual` | Same, but paste notes in terminal |
| Version target | `python3 main.py --version 3.9.0` | Target a specific release on Slack |
| Refresh | `python3 main.py --refresh --version 3.9.0` | Re-parse thread for new comments since last run |
| Ticket | `python3 main.py --ticket 12345` | Create article from support ticket |
| New article | `python3 main.py --new "Title"` | Ad-hoc article creation from scratch |
| Rewrite | `python3 main.py --rewrite "Title"` | Rewrite existing article in Stripe docs style |
| Staleness | `python3 main.py --staleness` | Flag articles not updated in 6+ months |
| Rollback | `python3 main.py --rollback 12345678` | Rollback article by ID |
| AEO audit | `python3 main.py --audit` | Scan all articles for missing TL;DR, FAQ, and schema markup |
| Style lint | `python3 main.py --lint "Title"` | Agent-based Stripe docs style review of a single article |
| AEO retrofit | `python3 main.py --aeo-retrofit` | Bulk-add AEO elements to articles flagged by audit |

---

## Component Breakdown

### Intelligence Layer — GPT-4o

The inference engine. Reads inputs, reasons about what to write, drafts HTML, manages conversation flow across all checkpoints. Vision-capable — screenshots dropped via `/img` are passed as image content blocks and analyzed directly.

**Model:** `gpt-4o` **Provider:** OpenAI API **Key:** `OPENAI_API_KEY`

---

### Tools Layer — External APIs

| Tool | File | What it does |
|---|---|---|
| `fetch_slack_release_thread` | `tools/slack.py` | Reads release thread from #release — by latest, semantic version (3.9.0), date (15.06.2026), or any text in the thread title |
| `fetch_slack_thread_updates` | `tools/slack.py` | Fetches only messages newer than last-parsed timestamp |
| `list_zendesk_articles` | `tools/zendesk.py` | Fetches all article titles + metadata (no bodies) |
| `get_zendesk_article` | `tools/zendesk.py` | Fetches full HTML body of a specific article |
| `get_sections` | `tools/zendesk.py` | Lists all Zendesk sections with IDs |
| `create_zendesk_article` | `tools/zendesk.py` | Creates a new article in a specified section |
| `update_zendesk_article` | `tools/zendesk.py` | Saves updated HTML as draft |
| `publish_zendesk_article` | `tools/zendesk.py` | Sets draft:false — makes article live |
| `upload_article_image` | `tools/zendesk.py` | Uploads screenshot to Zendesk CDN, returns URL for embedding |
| `rollback_zendesk_article` | `tools/zendesk.py` | Flags article for rollback |
| `get_zendesk_ticket` | `tools/zendesk.py` | Fetches support ticket: subject, description, comments, tags |
| `update_zendesk_ticket` | `tools/zendesk.py` | Posts internal note on ticket, marks solved (never public) |
| `create_release_video` | `tools/synthesia.py` | Calls Synthesia API to generate release highlights video |
| `ask_user` | `main.py` | Human checkpoint — presents a question in terminal |
| `show_diff` | `main.py` | Human checkpoint — renders article diff for review |
| `request_publish_approval` | `main.py` | Human checkpoint — final gate before publishing |
| `select_article_discovery_method` | `main.py` | Human checkpoint — user chooses article discovery mode |
| `save_changelog_entry` | `main.py` | Appends entry to changelog.md |
| `update_llms_txt` | `main.py` | Regenerates llms.txt after publish |
| `save_and_publish_article` | `main.py` | Atomic update + publish (replaces separate update/publish calls) |
| `complete_publish` | `main.py` | Saves changelog and regenerates llms.txt — called once at end of refinement loop |
| `run_aeo_audit` | `main.py` | Python-native AEO scan — string-match only, no LLM, saves `drafts/audit_results.json` |
| `web_search` | `main.py` (via `ddgs`) | DuckDuckGo search — pre-draft research in `--new` and `--rewrite` modes. No API key required. |

---

### Memory Layer — Persistent Files

| File | Purpose | Updated by |
|---|---|---|
| `CLAUDE.md` | Product knowledge, Stripe docs style guide, Diataxis templates, AEO rules, callout HTML, Pergamon terminology | Manually by docs team |
| `.env` | API credentials for all integrations | Manually by admin |
| `changelog.md` | Full audit trail of every publish | Agent after refinement loop ends |
| `llms.txt` | AI crawler index for GPTBot, ClaudeBot, Perplexity | Agent after refinement loop ends |
| `drafts/slack_state.json` | Last-parsed thread timestamp per version — enables `--refresh` | Agent after each Slack fetch |
| `drafts/article_*.json` | Local backup of articles that failed to publish | Agent on publish failure |
| `drafts/audit_results.json` | AEO audit output — article IDs + which elements are missing | `run_aeo_audit` (`--audit`) |

---

### Human Checkpoints — 6 gates

Nothing is published without explicit user approval. The agent pauses at six points across all workflows:

| Checkpoint | When | What the user does |
|---|---|---|
| ① Feature / goal | After parsing release or title | Confirms the feature list or article goal is correct |
| ② Feature description | Release workflow | Describes each feature in plain language; drops `/img` or `/doc` for context |
| ③ Article discovery | Release workflow | Chooses how to find impacted articles (scan / section / direct IDs) |
| ④ Diff review | All workflows | Reviews proposed HTML changes — approve / skip / edit |
| ⑤ Publish approval | All workflows | Final sign-off before anything goes live |
| ⑥ Post-publish refinement | All workflows | Verifies article looks correct; pastes inline edits until "done" |

---

### Context Injection

At any checkpoint, the user can inject grounded context:

| Command | What happens |
|---|---|
| `/img path` | Image loaded as GPT-4o vision content block. Agent reads UI labels verbatim, derives steps from visible elements. Image uploaded to Zendesk CDN and embedded in article HTML as `<figure>` with descriptive caption. |
| `/doc path` | Engineering doc (MD, TXT, RST, PDF, DOCX) loaded as text. Agent translates to end-user language — implementation details stripped before drafting. |
| `/note message` | Side note injected into next agent message without submitting the main answer. |

---

### Screenshot Embedding

When screenshots are provided via `/img`:

1. Agent analyzes each image with GPT-4o vision — reads UI labels, button names, navigation paths exactly as shown
2. After `create_zendesk_article` (new) or at context gather step (rewrite), agent calls `upload_article_image` per screenshot → Zendesk returns a CDN URL
3. Agent places a `<figure>` block immediately after the step the screenshot illustrates
4. Caption written in descriptive present tense: *"The Origin field showing the download icon and Assembly report button."*

---

### AEO Layer — AI Readability

Every article written or updated receives an automatic AEO pass:

| Enhancement | What it adds |
|---|---|
| TL;DR block | 2-3 sentence plain-language summary at the top |
| FAQ section | 3-5 natural language Q&A pairs at the bottom |
| Schema markup | `HowTo` or `FAQPage` JSON-LD injected into article HTML |
| Stripe docs style | One action per step, bold UI elements, `›` navigation paths, no filler preamble |

---

### Style Engine — CLAUDE.md

`CLAUDE.md` is loaded into the system prompt on every run. It governs:

- **Stripe docs style** — primary style reference: step structure, callout usage, heading conventions
- **Diataxis framework** — article type classification (How-to, Tutorial, Reference, Explanation)
- **Callout HTML** — Note, Tip, Warning, Danger in Stripe's visual language
- **AEO rules** — TL;DR, FAQ, schema markup applied to every article
- **Pergamon terminology** — exact product terms (Content Artifact, ACA Workflow, Knowledge Library, etc.)
- **Screenshot embedding** — `<figure>` template with caption rules

---

## Token Efficiency

| Design decision | Why |
|---|---|
| Metadata-only scan for discovery | Fetches titles only (~3K tokens), not full article bodies |
| User confirms shortlist before full fetch | Full bodies (~3K each) fetched only for confirmed articles |
| Four discovery modes | User can skip scanning by providing article IDs directly |
| Sequential article processing | One article at a time — keeps context window manageable |
| CLAUDE.md as sole always-loaded context | No full knowledge base loaded on every run |

---

## Error Handling

| Error | Behaviour |
|---|---|
| Zendesk publish fails | Retries up to 3×, saves draft locally to `/drafts/` if all fail |
| Zendesk article not found (404) | Returns structured error — agent warns user and skips |
| Image upload fails (file not found) | Inserts `[SCREENSHOT NEEDED: description]` at that position |
| OpenAI rate limit (429) | Waits 60s, retries up to 5× |
| OpenAI overloaded (529) | Waits 30s, retries up to 5× |
| Synthesia video fails | Inserts `[VIDEO NEEDED]` placeholder, continues workflow |
| Slack not configured | Falls back to manual paste in terminal |
| Agent stops mid-workflow | Loop detects premature stop, injects continuation message (capped at 3 retries) |
| `--refresh` with no prior state | Reports error — full workflow must run first to establish baseline |
