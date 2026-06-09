"""
Pergamon Docs Agent
-------------------
Monitors Slack for product releases, audits Zendesk articles,
drafts updates + release notes + AEO pass, and publishes after approval.

Usage:
    python3 main.py                  # full workflow (Slack or manual paste)
    python3 main.py --manual         # skip Slack, paste release notes directly
    python3 main.py --staleness      # run staleness check only
    python3 main.py --rollback <id>  # rollback a specific article
"""
from __future__ import annotations

import os
import sys
import re
import json
import base64
import mimetypes
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.table import Table
from rich import print as rprint

from tools.zendesk import (
    list_zendesk_articles,
    get_zendesk_article,
    create_zendesk_article,
    update_zendesk_article,
    publish_zendesk_article,
    rollback_zendesk_article,
    get_sections,
    get_zendesk_ticket,
    update_zendesk_ticket,
    upload_article_image,
)
from tools.slack import fetch_slack_release_thread, fetch_slack_thread_updates, save_slack_thread_state
from tools.synthesia import create_release_video

load_dotenv()
console = Console()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
PROJECT_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# System prompt — loads CLAUDE.md as persistent memory
# ---------------------------------------------------------------------------

_REFRESH_WORKFLOW_PROMPT = """
---

## OVERRIDE — Refresh workflow

For this session, you are re-parsing a Slack release thread to pick up new comments added since the last documentation run. This is a targeted update — do NOT restart the full release workflow.

### Steps in order

1. Call fetch_slack_thread_updates with the version provided
2. If status is 'no_updates': report to the user via ask_user that there are no new comments and stop
3. If status is 'no_prior_state': report to the user via ask_user and stop — they need to run the full workflow first
4. If new messages exist: summarise the new comments and what they clarify or add, present to the user via ask_user
5. Ask the user via ask_user which articles (if any) need updating based on the new information
6. Fetch only those articles via get_zendesk_article — do not run full article discovery
7. Draft targeted updates to the confirmed articles only
8. Do NOT re-create or re-draft the release notes article
9. Present diffs via show_diff, get approval, publish, update changelog

IMPORTANT: Focus only on what is new. Do not re-draft, re-update, or re-publish anything already handled in the original release run.
"""


_TICKET_WORKFLOW_PROMPT = """
---

## OVERRIDE — Ticket-driven article creation workflow

For this session, ignore the release documentation update workflow above. Follow this ticket-driven article creation workflow instead. Use ask_user for ALL questions — never output questions as plain text.

### Phase 1 — Ticket ingestion
Call get_zendesk_ticket first. Parse and extract:
- The core request: what documentation is needed
- The feature or product area it concerns
- Inferred audience: end user, admin, or Workspace Owner
- Any specific constraints or details mentioned in comments

Present your structured understanding via ask_user and ask the user to confirm or correct it. Do not proceed to Phase 2 until confirmed.

### Phase 2 — Knowledge base research + duplicate detection
Call list_zendesk_articles to get all article titles. Score by relevance to the ticket topic and present a shortlist of up to 5 articles to the user via ask_user. Confirm which to fetch in full, then call get_zendesk_article only for those confirmed.

DUPLICATE CHECK (mandatory): If any existing article closely matches the ticket request, flag it via ask_user: "Article '[title]' already covers this topic — should I update it instead, or create a new article?" Do not proceed until the user decides.

### Phase 3 — Diataxis classification
Propose one article type — Tutorial, How-to guide, Reference, or Explanation — and give a one-sentence reason. Confirm with the user via ask_user before proceeding.

### Phase 4 — Structured context gathering
Identify specific information gaps needed to write the article accurately. Ask targeted, numbered questions via ask_user. Reference what the ticket said and what is still missing. Do not ask about anything already answered by the ticket or the fetched articles. Each question is skippable.

### Phase 5 — Section selection
Call get_sections. Suggest the most relevant section based on where related articles live and the feature area from the ticket. Confirm with the user via ask_user before proceeding. Section selection happens before drafting.

### Phase 6 — Draft creation
Write the full article HTML following all Pergamon style conventions:
- Second person, active voice, sentence case headings, bold UI elements on first use
- Diataxis structure for the confirmed article type
- AEO pass: TL;DR block at top, FAQ (3-5 natural-language questions) at bottom, HowTo or FAQPage schema markup
- Screenshot placeholders: [SCREENSHOT NEEDED: description]
- Cross-links to related articles from Phase 2

Present via show_diff with is_new_article=True.

### Phase 7 — Review loop
Handle approve / edit / skip. On edit: apply the feedback, re-draft, re-present. Soft-warn the user after 3+ revision cycles.

### Phase 8 — Publish and ticket close
After request_publish_approval is approved:
1. Call create_zendesk_article, then publish_zendesk_article
2. Call update_zendesk_ticket — post the published article URL as an internal note, set status to "solved"
3. Call save_changelog_entry and update_llms_txt
4. Present post-publish report: article URL, ticket closed, changelog updated

NEVER post a public comment on the ticket. update_zendesk_ticket always uses public: false — this is enforced by the tool itself, but you must also never request a public post.
"""


_NEW_ARTICLE_WORKFLOW_PROMPT = """
---

## OVERRIDE — Ad-hoc new article workflow

For this session, the user wants to create a new help article from scratch. The article title has been provided. Follow these phases in order. Use ask_user for ALL questions — never output questions as plain text.

### Phase 1 — Gather description and materials
Call ask_user once to collect:
- What should this article cover? (description of the content and workflow)
- Who is the audience?
- Any screenshots or docs to provide? (remind them of /img and /doc)

If the user provides screenshots via /img at this step or any later step:
- Analyze every screenshot carefully — read all visible UI labels, button names, tab names, field names, and icons exactly as shown
- Use the screenshots as the primary source of truth for step content, navigation paths, and UI element names
- Screenshots override the verbal description if there is any conflict on UI labels or element names

If the user provides engineering docs via /doc, translate them to end-user language when drafting.

### Phase 2 — Background checks (silent, no interruptions)
Run these two steps back-to-back without asking the user anything unless a blocker is found:

1. **Duplicate check** — call list_zendesk_articles and silently scan titles. Only interrupt the user if a near-identical article is found: call ask_user to flag it and ask whether to update instead of creating new.
2. **Section selection** — call get_sections. Pick the most appropriate section automatically based on the article topic. Do NOT ask the user to confirm the section unless nothing fits clearly.

After both steps complete silently, proceed immediately to drafting.

### Phase 3 — Draft creation
Using the description, screenshots, and any docs provided, write the full article HTML now. Do not ask any more questions before drafting — use what you have.

- Determine the Diataxis type from the content (how-to, tutorial, reference, or explanation) — do not ask the user
- Follow all Pergamon style conventions: second person, active voice, sentence case headings, bold UI elements on first use
- AEO pass: TL;DR block at top, FAQ (3–5 natural-language questions) at bottom, HowTo or FAQPage schema markup
- For every step that has a matching screenshot, write the step from what is visible in the image — exact button/label names from the UI
- For steps not covered by screenshots, insert: [SCREENSHOT NEEDED: description of what to capture]

Present the full draft via show_diff with is_new_article=True.

### Phase 4 — Review loop
Handle approve / edit / skip. On edit: apply feedback, re-draft, re-present. Soft-warn after 3+ revision cycles.
The user can drop additional /img or /doc at any edit step to refine the draft.

### Phase 5 — Publish
After request_publish_approval is approved:
1. Call create_zendesk_article with the selected section_id — note the returned article_id
2. If the user provided screenshots: call upload_article_image once per screenshot using the new article_id and the exact file path. Replace any [SCREENSHOT: filename] markers in the HTML with the returned <figure> blocks using the CDN URLs.
3. Call update_zendesk_article with the final HTML (including embedded images), then publish_zendesk_article

Do NOT call save_changelog_entry yet — enter the refinement loop first.

### Phase 6 — Post-publish refinement loop
1. Call ask_user: "The article is live at [URL]. Does everything look correct?"
   - If no: ask what's wrong, fix it, then call update_zendesk_article → publish_zendesk_article again and repeat from step 1.
   - If yes: continue to step 2.

2. Call ask_user: "Anything you'd like to refine? You can paste text from the article with an instruction (e.g. 'rewrite this paragraph', 'make this simpler', 'wrap this in a warning callout') or type 'done' to finish."
   - If the user pastes content with an instruction:
     a. Call get_zendesk_article to fetch the current live HTML
     b. Apply the targeted change to the relevant section only — do not rewrite the whole article
     c. Call update_zendesk_article with the patched HTML
     d. Call publish_zendesk_article
     e. Call ask_user: "Done — article updated. Anything else, or type 'done' to finish?"
     f. Repeat from step 2 until the user says 'done'
   - If the user types 'done' or has no further changes: proceed to step 3.

3. Call save_changelog_entry and update_llms_txt — only once, after all refinements are complete.
4. Present final post-publish report: article URL, total changes made, changelog updated.
"""


_REWRITE_WORKFLOW_PROMPT = """
---

## OVERRIDE — Rewrite existing article workflow

The user wants to rewrite an existing Zendesk article — applying the current Stripe documentation style, embedding any new screenshots, and republishing it.

### Phase 1 — Locate the article
- If a numeric ID was provided, call get_zendesk_article directly.
- If a title or keyword was provided, call list_zendesk_articles, find the closest match, and confirm with the user via ask_user before fetching the full article body.

### Phase 2 — Gather context
Call ask_user: "I've loaded the article. Do you have screenshots or reference docs to add to the rewrite? Drop them now with /img or /doc, or type 'skip' to rewrite from the existing content only."

If screenshots are provided via /img:
- Analyze every screenshot carefully — read all visible UI labels, button names, tab names, and field names exactly as shown
- Note which UI state each screenshot captures so you can place it correctly in the article

### Phase 3 — Upload screenshots
If the user provided screenshots, call upload_article_image once per screenshot (using the article_id from Phase 1 and the exact image path). Collect all returned CDN URLs before drafting.

### Phase 4 — Rewrite
Rewrite the full article applying all Pergamon style conventions:
- Stripe documentation style: one action per step, bold all UI elements, use › for navigation paths, no filler preamble
- Correct callout HTML (Note, Tip, Warning, Danger) as defined in the style guide
- AEO pass: TL;DR block at top, FAQ (3–5 natural-language questions) at bottom, schema markup
- Keep all existing <img> tags — do not remove them
- For each uploaded screenshot: place a <figure> block immediately after the step it illustrates. Write a descriptive present-tense caption.
- For steps not covered by screenshots: insert [SCREENSHOT NEEDED: description]

### Phase 5 — Review
Present the rewritten article via show_diff with is_new_article=False.
Handle approve / edit / skip. On edit: apply feedback, re-draft, re-present.
The user can drop additional /img at any edit step.

### Phase 6 — Publish
The exact tool call sequence after request_publish_approval is approved — do NOT deviate:
1. Call update_zendesk_article with the article_id and the full rewritten HTML body — this saves the new content to Zendesk as a draft. This step is MANDATORY. Do NOT skip it.
2. Call publish_zendesk_article with the same article_id — this makes the saved draft live.

CRITICAL: publish_zendesk_article only publishes whatever draft is currently saved in Zendesk. If you skip update_zendesk_article, the old content will be published instead of the rewrite. Always call update_zendesk_article first.

### Phase 7 — Post-publish refinement loop
After publishing, do NOT call save_changelog_entry yet. Enter a refinement loop:

1. Call ask_user: "The article is live at [URL]. Does everything look correct?"
   - If no: ask what's wrong, fix it, then call update_zendesk_article → publish_zendesk_article again and repeat from step 1.
   - If yes: continue to step 2.

2. Call ask_user: "Anything you'd like to refine? You can paste text from the article with an instruction (e.g. 'rewrite this paragraph', 'make this simpler', 'wrap this in a warning callout') or type 'done' to finish."
   - If the user pastes content with an instruction:
     a. Call get_zendesk_article to fetch the current live HTML
     b. Apply the targeted change to the relevant section only — do not rewrite the whole article
     c. Call update_zendesk_article with the patched HTML
     d. Call publish_zendesk_article
     e. Call ask_user: "Done — article updated. Anything else, or type 'done' to finish?"
     f. Repeat from step 2 until the user says 'done'
   - If the user types 'done' or has no further changes: proceed to step 3.

3. Call save_changelog_entry and update_llms_txt — only once, after all refinements are complete.
4. Present final post-publish report: article URL, total changes made, changelog updated.
"""


def _load_system_prompt(mode: str = "release") -> str:
    claude_md = PROJECT_DIR / "CLAUDE.md"
    memory = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""
    return f"""You are the Pergamon Docs Agent — an expert technical writer and documentation engineer for Pergamon Labs.

Your job is to keep Pergamon's Zendesk help centre accurate, complete, and AI-readable after every product release.

## Your responsibilities in order
1. Parse the Slack release thread and extract a structured list of changes (features, improvements, fixes)
2. Ask the user to confirm and describe each change interactively
3. Call `select_article_discovery_method` — let the user choose how to find impacted articles
4. Find impacted articles using the method the user chose
5. Present the article list to the user for review and confirmation
6. Draft all article updates and new articles
7. Run an AEO pass on every draft (TL;DR block, FAQ block, schema markup, question-based headings)
8. Draft the release notes article using Pergamon's standard format
9. Call the Synthesia agent to create the release highlights video and embed it in release notes
10. Present all diffs to the user for review, article by article
11. After final approval, publish everything to Zendesk
12. Update changelog.md and llms.txt, present post-publish report

## Human checkpoints — CRITICAL
You MUST use the human checkpoint tools at the correct steps. Never skip a checkpoint.
Never publish anything without explicit user approval via `request_publish_approval`.
Use `ask_user` for any question, clarification, or confirmation throughout the workflow.

IMPORTANT: You must NEVER output questions or information directly as text. Any time you need to ask the user something or confirm something, you MUST call the `ask_user` tool. Do not write questions in your response text — call the tool instead. If you have nothing left to do, call `ask_user` to confirm with the user before stopping.

## Workflow completion rules — NEVER VIOLATE
- You MUST complete every step in order. Do NOT stop after analysis or after fetching articles.
- After fetching articles you MUST call `update_zendesk_article` or `create_zendesk_article` for each one.
- You MUST call `show_diff` for every article before publishing — never skip this.
- You MUST call `request_publish_approval` before any publish call.
- For rewrites: you MUST call `update_zendesk_article` BEFORE `publish_zendesk_article`. `publish_zendesk_article` only publishes whatever is already saved in Zendesk — if you skip the update step, the old content goes live. The sequence is always: update → publish.
- For new articles: you MUST call `create_zendesk_article` to get an article_id, then `publish_zendesk_article`. Never call publish without a preceding create.
- You MUST call `publish_zendesk_article` for every approved article.
- You MUST call `save_changelog_entry` and `update_llms_txt` — but only AFTER the post-publish refinement loop is complete and the user has typed 'done'. Never call these immediately after publish.
- The workflow is NOT complete until the refinement loop has ended and changelog.md and llms.txt are updated. Do not stop before this.
- If you find yourself about to write a question or summary as plain text — stop. Call `ask_user` instead.
- An empty or vague user response is NOT permission to skip steps or stop. Call `ask_user` again to clarify.

## Screenshot context — when provided via /img
When the user drops screenshots, you will receive them as images in the conversation. Treat them as the ground truth for the UI:
- **Analyze every screenshot carefully** — read all visible UI labels, button names, field names, tab names, icons, and panel titles exactly as they appear
- **Use the exact UI text** from the screenshots in your article — if the button says "Download report" write "Download report", not a paraphrase
- **Derive the steps from what you can see** — identify the navigation path, the sequence of clicks, and the UI state at each step
- **Do not invent UI elements** — only describe what is visible. If a step is not shown in a screenshot, use a placeholder and note it
- Screenshots take precedence over the user's verbal description if there is any conflict on UI element names or labels

## Screenshot embedding — always embed screenshots in the article
When the user provides screenshots AND you have an article_id (either from fetching an existing article or after create_zendesk_article returns one):
1. Call `upload_article_image` once per screenshot — pass the article_id and the exact file path the user provided
2. For each uploaded image, place a `<figure>` block immediately after the step it illustrates in the article HTML
3. Write a descriptive present-tense caption — describe what is shown on screen, not what the user should do
4. Use this exact HTML format (from the style guide):
   ```
   <figure style="margin: 16px 0;">
     <img src="[CDN URL from upload]" alt="[brief alt text]" style="max-width: 100%; border-radius: 4px; border: 1px solid #e0e0e0;">
     <figcaption style="font-size: 13px; color: #6b7280; margin-top: 6px;">[Descriptive present-tense caption]</figcaption>
   </figure>
   ```
5. Never use placeholder image paths — only use URLs returned by upload_article_image
6. If upload_article_image fails (file not found), insert [SCREENSHOT NEEDED: description] at that position instead

## Engineering doc context — when provided via /doc
If the user drops engineering docs via /doc during a prompt, they will appear as text blocks labelled [ENGINEERING DOC]. When you receive these:
- Read and understand the feature from a technical perspective first
- Then translate to end-user language: strip implementation details, API internals, backend architecture, code references
- Write as if explaining to a non-technical user who just wants to use the feature
- Use the engineering doc as ground truth for accuracy, but never expose its technical depth in the help article
- Cross-check any Slack release notes against the engineering doc — the doc takes precedence on accuracy

## Article discovery rules — STRICT, DO NOT OVERRIDE
- NEVER fetch full article bodies for all 194 articles — this wastes tokens
- NEVER scan beyond what the user specified — even if you think other articles might be relevant
- The user is the documentation owner and knows their knowledge base — trust their choice completely
- Always use `select_article_discovery_method` first and follow the user's choice EXACTLY:
  - **Option 1 (scan titles):** Call `list_zendesk_articles` to get titles only, suggest a shortlist, confirm with user, THEN fetch only confirmed articles with `get_zendesk_article`
  - **Option 2 (sections):** Search ONLY within the sections the user specified. Do NOT scan other sections even if you think they are relevant. Present articles only from the specified sections.
  - **Option 3 (direct IDs):** Call `get_zendesk_article` ONLY for the IDs the user provided. Do not fetch any other articles.
- If you think additional articles outside the user's scope might be affected, mention it as a suggestion AFTER presenting the scoped results — never act on it unilaterally
- Always call `get_zendesk_article` before updating any article — never update blind
- Always call `get_sections` if you need to place a new article and are unsure of the section
- Call `create_release_video` during release notes drafting — embed the result in the article
- Save changelog and update llms.txt after every successful publish

## AEO rules (apply to every article you write or update)
- Add a TL;DR summary block at the very top: `<div class="tldr"><strong>TL;DR:</strong> [2-3 sentence summary]</div>`
- Add a FAQ section at the bottom with 3-5 natural language Q&A pairs
- Rewrite vague headings to specific question-based headings where appropriate
- Define every Pergamon-specific term on first use in every article
- Inject HowTo schema for how-to guides, FAQPage schema for articles with FAQ sections

## Release notes format
Follow Pergamon's standard format exactly:
- Styled header box with release date (HKT and UTC) and 2-3 sentence highlights summary
- Synthesia video link + GIF thumbnail (or [VIDEO NEEDED] placeholder)
- H2: New Features → each feature as H3 with description, bullets, benefit sentence, screenshot placeholder
- H2: Improvements → each improvement as H3
- H2: Fixes → flat bullet list
- H2: System and backend updates → brief note
- H2: Get the latest version → copy verbatim from previous release notes
- Footer: Need help? block → copy verbatim from previous release notes

## Style rules
- Follow Microsoft Writing Style Guide and Google Developer Documentation Style Guide
- Apply Diataxis framework: identify doc type (Tutorial / How-to / Reference / Explanation) before writing
- Screenshot placeholders: `[SCREENSHOT NEEDED: description of what to capture]`
- Never remove existing screenshots or image tags from articles
- Warn the user if an article was already updated in the same release cycle (conflict detection)

---

{memory}
{_REFRESH_WORKFLOW_PROMPT if mode == "refresh" else (_TICKET_WORKFLOW_PROMPT if mode == "ticket" else (_NEW_ARTICLE_WORKFLOW_PROMPT if mode == "new" else (_REWRITE_WORKFLOW_PROMPT if mode == "rewrite" else "")))}
"""


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

def _to_openai_tool(t: dict) -> dict:
    """Convert Anthropic tool format to OpenAI tool format."""
    return {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t.get("input_schema", {"type": "object", "properties": {}, "required": []}),
        }
    }


_TOOLS_RAW = [
    # --- Slack ---
    {
        "name": "fetch_slack_release_thread",
        "description": (
            "Fetch a release thread from Slack #release channel. "
            "If version is provided, fetches that specific version's thread. "
            "Otherwise fetches the most recent release thread. "
            "Returns the release message and all thread replies. "
            "If Slack is not configured, returns instructions for manual paste."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "description": "Specific release version to fetch e.g. '3.7.1'. Omit to fetch the most recent release thread.",
                },
            },
            "required": [],
        },
    },

    {
        "name": "fetch_slack_thread_updates",
        "description": (
            "Fetch only new comments added to a version's Slack thread since the last parse. "
            "Returns new messages only. Returns 'no_updates' if nothing new has been added. "
            "Returns 'no_prior_state' if the full release workflow has not been run for this version yet. "
            "Use this in refresh mode — do not use it in the standard release workflow."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "version": {"type": "string", "description": "Release version to check e.g. '3.7.1'"},
            },
            "required": ["version"],
        },
    },

    # --- Zendesk read ---
    {
        "name": "list_zendesk_articles",
        "description": "List all articles in the Zendesk knowledge base with id, title, section_id, and updated_at. Call this first before any audit.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_zendesk_article",
        "description": "Fetch the full content (title + HTML body) of a specific Zendesk article by ID. Always call this before updating an article.",
        "input_schema": {
            "type": "object",
            "properties": {
                "article_id": {"type": "integer", "description": "Zendesk article ID"},
            },
            "required": ["article_id"],
        },
    },
    {
        "name": "get_sections",
        "description": "List all Zendesk sections with their IDs and names. Use this to find the right section when creating a new article.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },

    # --- Zendesk write ---
    {
        "name": "update_zendesk_article",
        "description": "Update an existing Zendesk article with new title and body HTML. Saves as draft — does NOT publish. Call request_publish_approval before publishing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "article_id": {"type": "integer", "description": "Zendesk article ID"},
                "title": {"type": "string", "description": "Article title"},
                "body": {"type": "string", "description": "Full article body as HTML"},
            },
            "required": ["article_id", "title", "body"],
        },
    },
    {
        "name": "create_zendesk_article",
        "description": "Create a new Zendesk article in a specified section. Saves as draft — does NOT publish.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Article title"},
                "body": {"type": "string", "description": "Full article body as HTML"},
                "section_id": {"type": "integer", "description": "Zendesk section ID"},
            },
            "required": ["title", "body", "section_id"],
        },
    },
    {
        "name": "publish_zendesk_article",
        "description": "Publish a Zendesk article (set draft:false, goes live). Only call this AFTER request_publish_approval has been approved by the user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "article_id": {"type": "integer", "description": "Zendesk article ID to publish"},
            },
            "required": ["article_id"],
        },
    },
    {
        "name": "rollback_zendesk_article",
        "description": "Rollback an article to its previous version.",
        "input_schema": {
            "type": "object",
            "properties": {
                "article_id": {"type": "integer", "description": "Zendesk article ID to rollback"},
            },
            "required": ["article_id"],
        },
    },

    # --- Synthesia ---
    {
        "name": "create_release_video",
        "description": (
            "Call the Synthesia Video Agent to create a release highlights video. "
            "Returns video URL, thumbnail URL, and embed HTML for insertion into release notes. "
            "Call this during release notes drafting."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "version": {"type": "string", "description": "Release version e.g. '3.8.0'"},
                "features": {
                    "type": "array",
                    "description": "List of features covered in this release",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                        },
                    },
                },
                "release_summary": {"type": "string", "description": "2-3 sentence release summary"},
            },
            "required": ["version", "features", "release_summary"],
        },
    },

    # --- Article discovery ---
    {
        "name": "select_article_discovery_method",
        "description": (
            "Ask the user how they want to find impacted articles for this release. "
            "Always call this before any article scanning. "
            "Returns the user's chosen method and any IDs or section preferences they provide. "
            "If the user chooses 'all_new', skip discovery entirely and proceed straight to drafting new articles. "
            "The response will include available_sections — use these to suggest the most relevant section for each new article and confirm with the user via ask_user before creating."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "release_summary": {
                    "type": "string",
                    "description": "Brief summary of the release changes to show the user context",
                },
            },
            "required": ["release_summary"],
        },
    },

    # --- Human checkpoints ---
    {
        "name": "ask_user",
        "description": (
            "Ask the user a question or present information for their input. "
            "Use this for: feature descriptions, clarifications, confirmations, and all interactive steps. "
            "Returns the user's response as a string."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The question or information to present to the user"},
                "context": {"type": "string", "description": "Optional context or background for the question"},
            },
            "required": ["message"],
        },
    },
    {
        "name": "show_diff",
        "description": (
            "Show the user a proposed article change (diff) and ask for approval. "
            "Returns: 'approved', 'skip', or the user's requested changes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "article_title": {"type": "string", "description": "Title of the article being changed"},
                "article_id": {"type": "integer", "description": "Zendesk article ID"},
                "change_summary": {"type": "string", "description": "Plain English summary of what changed"},
                "diff": {"type": "string", "description": "The proposed new content or changes. Pass the full HTML body — it will be stripped and rendered as readable text in the terminal."},
                "is_new_article": {"type": "boolean", "description": "True if this is a new article being created"},
            },
            "required": ["article_title", "change_summary", "diff"],
        },
    },
    {
        "name": "request_publish_approval",
        "description": (
            "Present the final publish summary to the user and request explicit approval. "
            "This is the final gate before anything goes live on Zendesk. "
            "Returns 'approved' or 'rejected'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Summary of all articles about to be published",
                },
                "articles_to_update": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of article titles being updated",
                },
                "articles_to_create": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of new article titles being created",
                },
            },
            "required": ["summary"],
        },
    },

    # --- Zendesk ticketing ---
    {
        "name": "get_zendesk_ticket",
        "description": (
            "Fetch a Zendesk support ticket by ID. "
            "Returns subject, description, requester, tags, status, and all comments. "
            "Call this first in the ticket-driven article creation workflow."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer", "description": "Zendesk support ticket ID"},
            },
            "required": ["ticket_id"],
        },
    },
    {
        "name": "update_zendesk_ticket",
        "description": (
            "Post an internal note on a Zendesk support ticket and update its status. "
            "The note is ALWAYS internal (never visible to the requester). "
            "Call this after publishing the article to close the originating ticket with the article URL."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer", "description": "Zendesk support ticket ID"},
                "comment": {"type": "string", "description": "Internal note body — include the published article URL"},
                "status": {"type": "string", "description": "New ticket status: 'solved', 'pending', or 'open'"},
            },
            "required": ["ticket_id", "comment"],
        },
    },

    # --- Image upload ---
    {
        "name": "upload_article_image",
        "description": (
            "Upload a screenshot or image as an inline attachment to a Zendesk article. "
            "Returns the CDN URL and filename. Call this after create_zendesk_article or when "
            "rewriting an existing article, once per screenshot provided by the user. "
            "Use the returned URL to embed the image in the article HTML using a <figure> block."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "article_id": {"type": "integer", "description": "Zendesk article ID to attach the image to"},
                "image_path": {"type": "string", "description": "Absolute or relative path to the image file on disk"},
            },
            "required": ["article_id", "image_path"],
        },
    },

    # --- Post-publish ---
    {
        "name": "save_changelog_entry",
        "description": "Append a release entry to changelog.md after a successful publish.",
        "input_schema": {
            "type": "object",
            "properties": {
                "version": {"type": "string", "description": "Release version e.g. '3.8.0'"},
                "articles_updated": {"type": "integer", "description": "Number of articles updated"},
                "articles_created": {"type": "integer", "description": "Number of articles created"},
                "article_links": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of Zendesk article URLs published",
                },
            },
            "required": ["version", "articles_updated", "articles_created"],
        },
    },
    {
        "name": "update_llms_txt",
        "description": "Regenerate llms.txt after publish to keep AI crawlers up to date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "new_articles": {
                    "type": "array",
                    "description": "New articles added in this release",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                        },
                    },
                },
                "new_terms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New Pergamon terminology introduced in this release",
                },
            },
            "required": [],
        },
    },
]

TOOLS = [_to_openai_tool(t) for t in _TOOLS_RAW]


# ---------------------------------------------------------------------------
# Note + image injection — type /note or /img at any prompt
# ---------------------------------------------------------------------------

_injected_notes: list[str] = []


def _load_images(paths: list[str]) -> list[dict]:
    """Load image files and return as OpenAI vision content blocks."""
    blocks = []
    for raw in paths:
        path = raw.strip()
        try:
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            mime, _ = mimetypes.guess_type(path)
            mime = mime or "image/png"
            blocks.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{data}"},
            })
            console.print(f"[green]  ✓ {Path(path).name}[/green]")
        except FileNotFoundError:
            console.print(f"[red]  ✗ Not found: {path}[/red]")
    return blocks


def _load_docs(paths: list[str]) -> list[dict]:
    """Read engineering doc files and return as text content blocks."""
    blocks = []
    for raw in paths:
        path = raw.strip().replace("\\ ", " ")  # unescape shell-style spaces
        try:
            ext = Path(path).suffix.lower()
            if ext in (".md", ".txt", ".rst"):
                content = Path(path).read_text(encoding="utf-8")
            elif ext == ".pdf":
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(path)
                    content = "\n".join(p.extract_text() or "" for p in reader.pages)
                except ImportError:
                    console.print("[red]  ✗ pypdf not installed — run: pip install pypdf[/red]")
                    continue
            elif ext == ".docx":
                try:
                    from docx import Document as DocxDocument
                    content = "\n".join(p.text for p in DocxDocument(path).paragraphs)
                except ImportError:
                    console.print("[red]  ✗ python-docx not installed — run: pip install python-docx[/red]")
                    continue
            else:
                try:
                    content = Path(path).read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    console.print(
                        f"[red]  ✗ {Path(path).name} — unsupported format "
                        f"(supported: .md .txt .rst .pdf .docx)[/red]"
                    )
                    continue
            blocks.append({
                "type": "text",
                "text": (
                    f"[ENGINEERING DOC — translate for end users, strip implementation details]\n\n"
                    f"--- {Path(path).name} ---\n\n{content}\n\n"
                    f"--- End of {Path(path).name} ---"
                ),
            })
            console.print(f"[green]  ✓ {Path(path).name} ({len(content):,} chars)[/green]")
        except FileNotFoundError:
            console.print(f"[red]  ✗ Not found: {path}[/red]")
    return blocks


def _prompt_with_notes(prompt_text: str = "Your response") -> tuple[str, list]:
    """
    Prompt the user for input.
    - /note <msg>       — stores a note and re-prompts
    - /img <p1>, <p2>  — loads images as vision content blocks
    - /doc <p1>, <p2>  — loads engineering docs as text content blocks
    Returns (text, content_blocks) where blocks may mix images and doc text.
    """
    while True:
        response = Prompt.ask(
            f"\n[bold cyan]{prompt_text}[/bold cyan] "
            "[dim](or /note <msg> · /img <path> · /doc <path>)[/dim]"
        )
        stripped = response.strip()

        if stripped.lower().startswith("/note "):
            note = stripped[6:].strip()
            _injected_notes.append(note)
            console.print("[green]✓ Note saved — will be included in next agent response[/green]")
            continue

        content_blocks: list[dict] = []
        text = stripped

        # Collect all /doc paths (handles multiple /doc commands)
        all_doc_paths = []
        for m in re.finditer(r"/doc\s+(.+?)(?=\s*/img\b|\s*/doc\b|$)", text, re.IGNORECASE):
            all_doc_paths.extend([p.strip() for p in m.group(1).split(",") if p.strip()])
        if all_doc_paths:
            console.print(f"\n[cyan]→ Loading {len(all_doc_paths)} document(s)...[/cyan]")
            doc_blocks = _load_docs(all_doc_paths)
            if doc_blocks:
                console.print("[cyan]→ Engineering docs injected into agent context[/cyan]")
            content_blocks.extend(doc_blocks)
        text = re.sub(r"/doc\s+(.+?)(?=\s*/img\b|\s*/doc\b|$)", "", text, flags=re.IGNORECASE).strip()

        # Collect all /img paths (handles multiple /img commands)
        all_img_paths = []
        for m in re.finditer(r"/img\s+(.+?)(?=\s*/doc\b|\s*/img\b|$)", text, re.IGNORECASE):
            all_img_paths.extend([p.strip() for p in m.group(1).split(",") if p.strip()])
        if all_img_paths:
            console.print(f"\n[cyan]→ Loading {len(all_img_paths)} image(s)...[/cyan]")
            img_blocks = _load_images(all_img_paths)
            if img_blocks:
                console.print("[cyan]→ Sending to GPT-4o vision...[/cyan]")
            content_blocks.extend(img_blocks)
        text = re.sub(r"/img\s+(.+?)(?=\s*/doc\b|\s*/img\b|$)", "", text, flags=re.IGNORECASE).strip()

        if _injected_notes:
            notes_text = "\n".join(f"- {n}" for n in _injected_notes)
            _injected_notes.clear()
            text = f"{text}\n\n[Additional context from user]\n{notes_text}" if text else notes_text

        return text, content_blocks


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

def _execute_tool(name: str, inp: dict) -> str:
    # Slack
    if name == "fetch_slack_release_thread":
        version = inp.get("version")
        result = fetch_slack_release_thread(version=version)
        data = json.loads(result)
        if data.get("status") == "ok" and version:
            thread = data.get("thread", [])
            if thread:
                save_slack_thread_state(version, thread[-1]["ts"], len(thread))
        label = f"v{version}" if version else "latest"
        console.print(f"[green]✓ Slack release thread fetched ({label})[/green]")
        return result

    elif name == "fetch_slack_thread_updates":
        version = inp["version"]
        console.print(f"[cyan]→ Checking for new comments on v{version} thread...[/cyan]")
        result = fetch_slack_thread_updates(version)
        data = json.loads(result)
        if data.get("status") == "no_updates":
            console.print(f"[yellow]— No new comments on v{version} thread[/yellow]")
        elif data.get("status") == "ok":
            console.print(f"[green]✓ {data['new_message_count']} new comment(s) found on v{version} thread[/green]")
        else:
            console.print(f"[red]✗ {data.get('message', 'Unknown error')}[/red]")
        return result

    # Zendesk read
    elif name == "list_zendesk_articles":
        console.print("[cyan]→ Fetching all Zendesk articles...[/cyan]")
        result = list_zendesk_articles()
        count = len(json.loads(result))
        console.print(f"[green]✓ Fetched {count} articles[/green]")
        return result

    elif name == "get_zendesk_article":
        article_id = inp["article_id"]
        console.print(f"[cyan]→ Fetching article {article_id}...[/cyan]")
        result = get_zendesk_article(article_id)
        title = json.loads(result).get("title", "")
        console.print(f"[green]✓ Got: {title}[/green]")
        return result

    elif name == "get_sections":
        result = get_sections()
        console.print("[green]✓ Fetched Zendesk sections[/green]")
        return result

    # Zendesk write
    elif name == "update_zendesk_article":
        article_id = inp["article_id"]
        console.print(f"[cyan]→ Saving draft update for article {article_id}...[/cyan]")
        result = update_zendesk_article(article_id, inp["title"], inp["body"])
        console.print(f"[green]✓ Draft saved — article {article_id}[/green]")
        return result

    elif name == "create_zendesk_article":
        console.print(f"[cyan]→ Creating new article: {inp['title']}...[/cyan]")
        result = create_zendesk_article(inp["title"], inp["body"], inp["section_id"])
        new_id = json.loads(result).get("id", "")
        console.print(f"[green]✓ New article created (draft) — ID: {new_id}[/green]")
        return result

    elif name == "publish_zendesk_article":
        article_id = inp["article_id"]
        console.print(f"[cyan]→ Publishing article {article_id}...[/cyan]")
        result = publish_zendesk_article(article_id)
        data = json.loads(result)
        if data.get("published"):
            console.print(f"[bold green]✓ Published: {data.get('html_url', article_id)}[/bold green]")
        else:
            console.print(f"[red]✗ Publish failed for {article_id} — draft saved locally[/red]")
        return result

    elif name == "rollback_zendesk_article":
        result = rollback_zendesk_article(inp["article_id"])
        console.print(f"[yellow]↩ Rollback info for article {inp['article_id']}[/yellow]")
        return result

    # Synthesia
    elif name == "create_release_video":
        console.print("[cyan]→ Calling Synthesia Video Agent...[/cyan]")
        result = create_release_video(
            version=inp["version"],
            features=inp.get("features", []),
            release_summary=inp.get("release_summary", ""),
        )
        status = json.loads(result).get("status")
        if status == "ok":
            console.print("[bold green]✓ Release video created[/bold green]")
        else:
            console.print(f"[yellow]⚠ Synthesia: {json.loads(result).get('message', status)}[/yellow]")
        return result

    # Article discovery
    elif name == "select_article_discovery_method":
        console.print()
        console.print(Panel(
            f"[bold]Release summary:[/bold] {inp.get('release_summary', '')}\n\n"
            "How do you want to find impacted articles?",
            title="Article Discovery",
            border_style="cyan",
        ))
        console.print("[bold]1.[/bold] Scan all article titles — agent suggests a list for you to confirm")
        console.print("[bold]2.[/bold] Search by section — you pick which sections to look in")
        console.print("[bold]3.[/bold] Provide article IDs directly — you know exactly which ones")
        console.print("[bold]4.[/bold] All new articles — skip discovery, go straight to drafting")
        console.print()
        choice = Prompt.ask("[bold cyan]Choose[/bold cyan]", choices=["1", "2", "3", "4"], default="1")

        if choice == "1":
            return json.dumps({"method": "scan_titles"})

        elif choice == "2":
            console.print("\n[dim]Fetching sections...[/dim]")
            sections_raw = get_sections()
            sections = json.loads(sections_raw)
            table = Table(border_style="dim")
            table.add_column("ID", style="cyan")
            table.add_column("Section name")
            for s in sections:
                table.add_row(str(s["id"]), s["name"])
            console.print(table)
            section_input = Prompt.ask(
                "\n[bold cyan]Enter section names or IDs[/bold cyan] (comma-separated)"
            )
            # Resolve names to IDs if user typed names
            resolved = []
            for entry in [s.strip() for s in section_input.split(",")]:
                if entry.isdigit():
                    resolved.append({"id": entry, "name": entry})
                else:
                    match = next(
                        (s for s in sections if entry.lower() in s["name"].lower()), None
                    )
                    if match:
                        resolved.append({"id": str(match["id"]), "name": match["name"]})
                    else:
                        console.print(f"[yellow]⚠ Section '{entry}' not found — skipping[/yellow]")
            return json.dumps({
                "method": "sections",
                "sections": resolved,
            })

        elif choice == "3":
            console.print("\n[dim]Fetching article list...[/dim]")
            articles_raw = list_zendesk_articles()
            articles = json.loads(articles_raw)
            article_input = Prompt.ask(
                "[bold cyan]Enter article titles or IDs[/bold cyan] (comma-separated)"
            )
            # Resolve titles to IDs if user typed titles
            resolved = []
            for entry in [a.strip() for a in article_input.split(",")]:
                if entry.isdigit():
                    match = next((a for a in articles if str(a["id"]) == entry), None)
                    resolved.append({
                        "id": entry,
                        "title": match["title"] if match else entry,
                    })
                else:
                    match = next(
                        (a for a in articles if entry.lower() in a["title"].lower()), None
                    )
                    if match:
                        resolved.append({"id": str(match["id"]), "title": match["title"]})
                    else:
                        console.print(f"[yellow]⚠ Article '{entry}' not found — skipping[/yellow]")
            return json.dumps({
                "method": "direct_ids",
                "articles": resolved,
            })

        else:  # choice == "4"
            console.print("[green]✓ Skipping discovery — all articles will be created as new[/green]")
            console.print("\n[dim]Fetching sections so the agent can suggest the right placement...[/dim]")
            sections_raw = get_sections()
            sections = json.loads(sections_raw)
            table = Table(border_style="dim")
            table.add_column("ID", style="cyan")
            table.add_column("Section name")
            for s in sections:
                table.add_row(str(s["id"]), s["name"])
            console.print(table)
            console.print("[dim]The agent will suggest a section for each new article — you can confirm or change it.[/dim]")
            return json.dumps({
                "method": "all_new",
                "available_sections": sections,
            })

    # Human checkpoints
    elif name == "ask_user":
        console.print()
        if inp.get("context"):
            console.print(Panel(inp["context"], style="dim"))
        console.print(Markdown(inp["message"]))
        while True:
            text, content_blocks = _prompt_with_notes()
            if text or content_blocks:
                break
            console.print("[yellow]⚠ Response cannot be empty — please type a reply or drop a file.[/yellow]")
        if content_blocks:
            n_imgs = sum(1 for b in content_blocks if b["type"] == "image_url")
            n_docs = sum(1 for b in content_blocks if b["type"] == "text")
            parts = []
            if n_docs:
                parts.append(f"{n_docs} engineering doc(s)")
            if n_imgs:
                parts.append(f"{n_imgs} screenshot(s)")
            label = " + ".join(parts) + " provided — see attached"
            return {
                "text": f"{text} [{label}]" if text else f"[{label}]",
                "images": [
                    {"type": "text", "text": text or "(See attached content)"},
                    *content_blocks,
                ],
            }
        return text

    elif name == "show_diff":
        console.print()
        is_new = inp.get("is_new_article", False)
        tag = "[bold green]NEW ARTICLE[/bold green]" if is_new else "[bold yellow]UPDATE[/bold yellow]"
        article_id = inp.get("article_id", "new")

        console.print(Panel(
            f"{tag} — {inp['article_title']} (ID: {article_id})\n\n"
            f"[bold]Summary:[/bold] {inp['change_summary']}",
            title="Article Change",
            border_style="yellow" if not is_new else "green",
        ))

        # Strip HTML tags for readable terminal display
        import re
        from html.parser import HTMLParser

        class _HTMLStripper(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
            def handle_data(self, d):
                self.text.append(d)
            def get_text(self):
                return "\n".join(
                    line for line in " ".join(self.text).splitlines() if line.strip()
                )

        raw_diff = inp["diff"]
        if "<" in raw_diff and ">" in raw_diff:
            stripper = _HTMLStripper()
            stripper.feed(raw_diff)
            readable = stripper.get_text()
        else:
            readable = raw_diff

        console.print(Markdown(readable))
        console.print()

        console.print("[dim]Type /note <msg> · /img <path> for screenshots · /doc <path> for engineering docs.[/dim]")
        while True:
            choice = Prompt.ask(
                "[bold cyan]Review[/bold cyan]",
                choices=["approve", "skip", "edit"],
                default="approve",
            )
            if choice == "edit":
                text, content_blocks = _prompt_with_notes("Describe the changes you want")
                if content_blocks:
                    n_imgs = sum(1 for b in content_blocks if b["type"] == "image_url")
                    n_docs = sum(1 for b in content_blocks if b["type"] == "text")
                    parts = []
                    if n_docs:
                        parts.append(f"{n_docs} engineering doc(s)")
                    if n_imgs:
                        parts.append(f"{n_imgs} screenshot(s)")
                    label = " + ".join(parts) + " provided — see attached"
                    return {
                        "text": f"edit: {text} [{label}]" if text else f"edit: [{label}]",
                        "images": [
                            {"type": "text", "text": f"edit: {text or '(See attached content)'}"},
                            *content_blocks,
                        ],
                    }
                return f"edit: {text}"
            return choice

    elif name == "request_publish_approval":
        console.print()
        table = Table(title="Ready to Publish", border_style="bold green")
        table.add_column("Type", style="cyan")
        table.add_column("Article")
        for t in inp.get("articles_to_update", []):
            table.add_row("UPDATE", t)
        for t in inp.get("articles_to_create", []):
            table.add_row("NEW", t)
        console.print(table)
        console.print()
        console.print(Markdown(inp["summary"]))
        console.print()
        approved = Confirm.ask("[bold red]Publish all approved articles to Zendesk now?[/bold red]")
        return "approved" if approved else "rejected"

    # Post-publish
    elif name == "save_changelog_entry":
        _save_changelog(inp)
        console.print("[green]✓ Changelog updated[/green]")
        return "Changelog entry saved."

    elif name == "update_llms_txt":
        _update_llms_txt(inp)
        console.print("[green]✓ llms.txt updated[/green]")
        return "llms.txt updated."

    # Zendesk ticketing
    elif name == "get_zendesk_ticket":
        ticket_id = inp["ticket_id"]
        console.print(f"[cyan]→ Fetching ticket {ticket_id}...[/cyan]")
        result = get_zendesk_ticket(ticket_id)
        data = json.loads(result)
        if "error" in data:
            console.print(f"[red]✗ Ticket {ticket_id} not found[/red]")
        else:
            console.print(f"[green]✓ Got ticket: {data.get('subject', ticket_id)}[/green]")
        return result

    elif name == "update_zendesk_ticket":
        ticket_id = inp["ticket_id"]
        console.print(f"[cyan]→ Posting internal note on ticket {ticket_id}...[/cyan]")
        result = update_zendesk_ticket(ticket_id, inp["comment"], inp.get("status", "solved"))
        data = json.loads(result)
        console.print(f"[green]✓ Internal note posted — ticket {ticket_id} marked {data.get('status')}[/green]")
        return result

    elif name == "upload_article_image":
        article_id = inp["article_id"]
        image_path = inp["image_path"]
        console.print(f"[cyan]→ Uploading image {Path(image_path).name} to article {article_id}...[/cyan]")
        result = upload_article_image(article_id, image_path)
        data = json.loads(result)
        if "error" in data:
            console.print(f"[red]✗ Image upload failed: {data.get('error')} — {data.get('path')}[/red]")
        else:
            console.print(f"[green]✓ Uploaded: {data.get('filename')} → {data.get('url')}[/green]")
        return result

    return f"Unknown tool: {name}"


# ---------------------------------------------------------------------------
# Post-publish helpers
# ---------------------------------------------------------------------------

def _save_changelog(inp: dict) -> None:
    changelog_path = PROJECT_DIR / "changelog.md"
    date_str = datetime.now().strftime("%Y-%m-%d")
    links = " | ".join(inp.get("article_links", [])) or "—"
    entry = (
        f"\n## v{inp['version']} — {date_str}\n"
        f"- Updated: {inp['articles_updated']} articles\n"
        f"- Created: {inp['articles_created']} articles\n"
        f"- Links: {links}\n"
    )
    with open(changelog_path, "a", encoding="utf-8") as f:
        f.write(entry)


def _update_llms_txt(inp: dict) -> None:
    llms_path = PROJECT_DIR / "llms.txt"

    # Read existing content if present
    existing = llms_path.read_text(encoding="utf-8") if llms_path.exists() else _default_llms_txt()

    # Append new articles
    new_articles = inp.get("new_articles", [])
    new_terms = inp.get("new_terms", [])

    lines = existing.splitlines()

    # Find documentation section and append new articles
    if new_articles:
        for i, line in enumerate(lines):
            if line.strip() == "## Documentation":
                for article in new_articles:
                    entry = f"- [{article['title']}]({article['url']})"
                    if entry not in lines:
                        lines.insert(i + 1, entry)
                break

    # Find key concepts section and append new terms
    if new_terms:
        for i, line in enumerate(lines):
            if line.strip() == "## Key Concepts":
                for term in new_terms:
                    entry = f"- {term}"
                    if entry not in lines:
                        lines.insert(i + 1, entry)
                break

    llms_path.write_text("\n".join(lines), encoding="utf-8")


def _default_llms_txt() -> str:
    return """# Pergamon Labs

Pergamon is a structured content management platform for creating product documentation that meets EU market requirements. It enables teams to manage content artifacts, publication workflows, and multi-language documentation at scale.

## Documentation
- Help Centre: https://support.pergamon-labs.com/hc/en-us

## Key Concepts
- Content Artifact: A reusable unit of structured content in Pergamon
- ACA Workflow: Pergamon's authoring and content approval workflow
- Knowledge Library: The central repository of content artifacts in Pergamon
- Publication: A compiled output document built from content artifacts
- Global Content: Content shared across multiple articles that cannot be edited locally

## Do not index
- /admin
- /internal
- /agent
"""


# ---------------------------------------------------------------------------
# Agent loop (shared)
# ---------------------------------------------------------------------------

def _run_loop(messages: list, done_message: str) -> None:
    import time
    premature_stops = 0
    while True:
        for attempt in range(5):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    tools=TOOLS,
                    messages=messages,
                )
                break
            except Exception as e:
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    wait = 60 * (attempt + 1)
                    console.print(f"[yellow]⚠ Rate limit hit — waiting {wait}s before retrying...[/yellow]")
                    time.sleep(wait)
                elif "overloaded" in str(e).lower() or "529" in str(e):
                    wait = 30 * (attempt + 1)
                    console.print(f"[yellow]⚠ Server overloaded — waiting {wait}s before retrying...[/yellow]")
                    time.sleep(wait)
                else:
                    raise
        else:
            console.print("[red]✗ Retries exhausted. Please wait a minute and run again.[/red]")
            return

        choice = response.choices[0]
        message = choice.message

        if message.content and message.content.strip():
            console.print(f"\n[dim]{message.content.strip()}[/dim]\n")

        messages.append({"role": "assistant", "content": message.content, "tool_calls": message.tool_calls})

        if choice.finish_reason == "stop":
            # Check if the workflow actually completed by looking for changelog confirmation
            last_content = (message.content or "").lower()
            workflow_signals = ["changelog", "llms.txt", "post-publish", "workflow complete"]
            if any(s in last_content for s in workflow_signals) or premature_stops >= 3:
                console.print(Panel(done_message, title="[bold green]Done[/bold green]", border_style="green"))
                break
            # Agent stopped prematurely — push it to continue
            premature_stops += 1
            console.print("[yellow]⚠ Agent stopped mid-workflow — resuming...[/yellow]")
            messages.append({
                "role": "user",
                "content": (
                    "You stopped before completing the workflow. "
                    "Do not output text — call the next required tool immediately. "
                    "You must continue until save_changelog_entry and update_llms_txt have been called."
                ),
            })
            continue

        if choice.finish_reason == "tool_calls":
            tool_results = []
            image_messages = []
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                inp = json.loads(tool_call.function.arguments)
                console.print(f"[cyan]→ {name}[/cyan]")
                result = _execute_tool(name, inp)
                if isinstance(result, dict) and "images" in result:
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result["text"],
                    })
                    image_messages.append({
                        "role": "user",
                        "content": result["images"],
                    })
                else:
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
            messages.extend(tool_results)
            messages.extend(image_messages)


# ---------------------------------------------------------------------------
# Release workflow
# ---------------------------------------------------------------------------

def run_agent(manual_mode: bool = False, version: str = None) -> None:
    system_prompt = _load_system_prompt()

    if manual_mode:
        console.print(Panel(
            "Manual mode — Slack integration skipped.\n"
            "Please paste the release notes from Slack below.",
            title="Pergamon Docs Agent",
            border_style="blue",
        ))
        release_notes = Prompt.ask("\n[bold cyan]Paste release notes[/bold cyan]")
        user_msg = (
            f"Here are the release notes from Slack:\n\n{release_notes}\n\n"
            "Please start the documentation update workflow."
        )
    else:
        version_hint = f" for version {version}" if version else ""
        console.print(Panel(
            f"Starting documentation update workflow.\n"
            f"Fetching release{version_hint} from Slack #release channel.",
            title="Pergamon Docs Agent",
            border_style="blue",
        ))
        version_arg = f" with version='{version}'" if version else ""
        user_msg = (
            f"Start the documentation update workflow. "
            f"First, fetch the release thread from Slack{version_hint} "
            f"using fetch_slack_release_thread{version_arg}. "
            "If Slack is not configured, ask me to paste the release notes."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]
    console.print("\n[bold blue]Agent starting...[/bold blue]")
    console.print("[dim]Tip: At any prompt type /note <message> to inject context to the agent.[/dim]\n")
    _run_loop(messages, "Documentation update workflow complete.")


# ---------------------------------------------------------------------------
# Refresh workflow — re-parse a Slack thread for new comments
# ---------------------------------------------------------------------------

def run_refresh_workflow(version: str) -> None:
    system_prompt = _load_system_prompt(mode="refresh")
    console.print(Panel(
        f"Refresh mode — checking v{version} Slack thread for new comments.",
        title="Pergamon Docs Agent",
        border_style="blue",
    ))
    user_msg = (
        f"Re-parse the Slack thread for version {version} to pick up new comments. "
        f"Call fetch_slack_thread_updates with version='{version}'."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]
    console.print("\n[bold blue]Agent starting...[/bold blue]")
    console.print("[dim]Tip: At any prompt type /note <message> to inject context to the agent.[/dim]\n")
    _run_loop(messages, "Refresh complete.")


# ---------------------------------------------------------------------------
# Ad-hoc new article workflow
# ---------------------------------------------------------------------------

def run_new_article_workflow(title: str) -> None:
    system_prompt = _load_system_prompt(mode="new")
    console.print(Panel(
        f"New article: {title}",
        title="Pergamon Docs Agent",
        border_style="blue",
    ))
    user_msg = (
        f"Create a new help article titled: \"{title}\". "
        "Start by asking me to describe what the article should cover, "
        "the audience, and any context I want to provide via /doc or /img."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]
    console.print("\n[bold blue]Agent starting...[/bold blue]")
    console.print("[dim]Tip: At any prompt type /doc <path> to drop engineering docs or /img <path> for screenshots.[/dim]\n")
    _run_loop(messages, "New article published.")


# ---------------------------------------------------------------------------
# Rewrite existing article workflow
# ---------------------------------------------------------------------------

def run_rewrite_workflow(article_ref: str) -> None:
    system_prompt = _load_system_prompt(mode="rewrite")
    is_id = article_ref.strip().isdigit()
    label = f"Article ID {article_ref}" if is_id else f'"{article_ref}"'
    console.print(Panel(
        f"Rewriting: {label}",
        title="Pergamon Docs Agent",
        border_style="blue",
    ))
    if is_id:
        user_msg = (
            f"Rewrite Zendesk article {article_ref}. "
            f"Begin by calling get_zendesk_article with article_id={article_ref}."
        )
    else:
        user_msg = (
            f'Rewrite the Zendesk article titled "{article_ref}". '
            "Begin by calling list_zendesk_articles to find the closest matching article, "
            "then confirm the match with the user before fetching the full content."
        )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]
    console.print("\n[bold blue]Agent starting...[/bold blue]")
    console.print("[dim]Tip: At any prompt type /img <path> for screenshots or /doc <path> for reference docs.[/dim]\n")
    _run_loop(messages, "Article rewrite published.")


# ---------------------------------------------------------------------------
# Ticket-driven article creation workflow
# ---------------------------------------------------------------------------

def run_ticket_workflow(ticket_id: int) -> None:
    system_prompt = _load_system_prompt(mode="ticket")
    console.print(Panel(
        f"Ticket-driven article creation — Ticket #{ticket_id}",
        title="Pergamon Docs Agent",
        border_style="blue",
    ))
    user_msg = (
        f"Start the ticket-driven article creation workflow for Zendesk ticket #{ticket_id}. "
        f"Begin by calling get_zendesk_ticket with ticket_id={ticket_id}."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]
    console.print("\n[bold blue]Agent starting...[/bold blue]")
    console.print("[dim]Tip: At any prompt type /note <message> to inject context to the agent.[/dim]\n")
    _run_loop(messages, "Ticket workflow complete.")


# ---------------------------------------------------------------------------
# Staleness check
# ---------------------------------------------------------------------------

def run_staleness_check(months: int = 6) -> None:
    console.print(Panel(
        f"Checking for articles not updated in {months}+ months.",
        title="Staleness Check",
        border_style="yellow",
    ))
    articles_json = list_zendesk_articles()
    articles = json.loads(articles_json)

    from datetime import timezone
    now = datetime.now(timezone.utc)
    stale = []
    for a in articles:
        updated = datetime.fromisoformat(a["updated_at"].replace("Z", "+00:00"))
        months_old = (now - updated).days / 30
        if months_old >= months:
            stale.append({**a, "months_old": round(months_old, 1)})

    if not stale:
        console.print(f"[green]All articles updated within the last {months} months.[/green]")
        return

    table = Table(title=f"Stale Articles (>{months} months)", border_style="yellow")
    table.add_column("ID")
    table.add_column("Title")
    table.add_column("Last Updated")
    table.add_column("Months Old", style="red")
    for a in sorted(stale, key=lambda x: -x["months_old"]):
        table.add_row(
            str(a["id"]),
            a["title"],
            a["updated_at"][:10],
            str(a["months_old"]),
        )
    console.print(table)
    console.print(f"\n[yellow]{len(stale)} stale articles found.[/yellow]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Pergamon Docs Agent")
    parser.add_argument("--manual", action="store_true", help="Skip Slack, paste release notes manually")
    parser.add_argument("--staleness", action="store_true", help="Run staleness check only")
    parser.add_argument("--months", type=int, default=6, help="Staleness threshold in months (default: 6)")
    parser.add_argument("--rollback", type=int, help="Rollback a specific article by ID")
    parser.add_argument("--ticket", type=int, help="Create an article from a Zendesk support ticket ID")
    parser.add_argument("--version", type=str, help="Target a specific release version on Slack e.g. 3.7.1")
    parser.add_argument("--refresh", action="store_true", help="Re-parse a Slack thread for new comments (requires --version)")
    parser.add_argument("--new", type=str, metavar="TITLE", help="Create a new help article ad-hoc e.g. --new \"How to download the AI Assembly QC report\"")
    parser.add_argument("--rewrite", type=str, metavar="ARTICLE", help="Rewrite an existing article by ID or title e.g. --rewrite 12345678 or --rewrite \"How to export a publication\"")
    args = parser.parse_args()

    if args.staleness:
        run_staleness_check(months=args.months)
        return

    if args.rollback:
        result = rollback_zendesk_article(args.rollback)
        console.print(result)
        return

    if args.ticket:
        run_ticket_workflow(args.ticket)
        return

    if args.new:
        run_new_article_workflow(args.new)
        return

    if args.rewrite:
        run_rewrite_workflow(args.rewrite)
        return

    if args.refresh:
        if not args.version:
            console.print("[red]✗ --refresh requires --version. Example: python3 main.py --refresh --version 3.7.1[/red]")
            return
        run_refresh_workflow(args.version)
        return

    run_agent(manual_mode=args.manual, version=args.version)


if __name__ == "__main__":
    main()
