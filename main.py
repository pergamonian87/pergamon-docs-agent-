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
import json
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
)
from tools.slack import fetch_slack_release_thread
from tools.synthesia import create_release_video

load_dotenv()
console = Console()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
PROJECT_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# System prompt — loads CLAUDE.md as persistent memory
# ---------------------------------------------------------------------------

def _load_system_prompt() -> str:
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
            "Fetch the most recent release thread from Slack #release channel. "
            "Returns the release message and thread replies. "
            "If Slack is not configured, returns instructions for manual paste."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
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
            "If the user chooses 'all_new', skip discovery entirely and proceed straight to drafting new articles."
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
# Note injection — type /note <message> at any prompt
# ---------------------------------------------------------------------------

_injected_notes: list[str] = []

def _prompt_with_notes(prompt_text: str = "Your response") -> str:
    """
    Prompt the user for input. If they type /note <message>, store the note
    and re-prompt. Notes are prepended to the next response sent to the agent.
    """
    while True:
        response = Prompt.ask(f"\n[bold cyan]{prompt_text}[/bold cyan] [dim](or /note <message>)[/dim]")
        if response.strip().lower().startswith("/note "):
            note = response.strip()[6:].strip()
            _injected_notes.append(note)
            console.print(f"[green]✓ Note saved — will be included in next agent response[/green]")
        else:
            if _injected_notes:
                notes_text = "\n".join(f"- {n}" for n in _injected_notes)
                _injected_notes.clear()
                return f"{response}\n\n[Additional context from user]\n{notes_text}"
            return response


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

def _execute_tool(name: str, inp: dict) -> str:
    # Slack
    if name == "fetch_slack_release_thread":
        result = fetch_slack_release_thread()
        console.print("[green]✓ Slack release thread fetched[/green]")
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
            return json.dumps({"method": "all_new"})

    # Human checkpoints
    elif name == "ask_user":
        console.print()
        if inp.get("context"):
            console.print(Panel(inp["context"], style="dim"))
        console.print(Markdown(inp["message"]))
        response = _prompt_with_notes()
        return response

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

        console.print("[dim]Type /note <message> to inject a note to the agent before choosing.[/dim]")
        while True:
            choice = Prompt.ask(
                "[bold cyan]Review[/bold cyan]",
                choices=["approve", "skip", "edit"],
                default="approve",
            )
            if choice == "edit":
                feedback = _prompt_with_notes("Describe the changes you want")
                return f"edit: {feedback}"
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
# Agent loop
# ---------------------------------------------------------------------------

def run_agent(manual_mode: bool = False) -> None:
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
        console.print(Panel(
            "Starting documentation update workflow.\n"
            "Fetching release from Slack #release channel.",
            title="Pergamon Docs Agent",
            border_style="blue",
        ))
        user_msg = (
            "Start the documentation update workflow. "
            "First, fetch the latest release thread from Slack using fetch_slack_release_thread. "
            "If Slack is not configured, ask me to paste the release notes."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]
    console.print("\n[bold blue]Agent starting...[/bold blue]")
    console.print("[dim]Tip: At any prompt type /note <message> to inject context to the agent.[/dim]\n")

    import time
    while True:
        # Retry with backoff on rate limit errors
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

        # Print any text output from the agent
        if message.content and message.content.strip():
            console.print(f"\n[dim]{message.content.strip()}[/dim]\n")

        # Append assistant message to history
        messages.append({"role": "assistant", "content": message.content, "tool_calls": message.tool_calls})

        if choice.finish_reason == "stop":
            console.print(Panel(
                "Documentation update workflow complete.",
                title="[bold green]Done[/bold green]",
                border_style="green",
            ))
            break

        if choice.finish_reason == "tool_calls":
            tool_results = []
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                inp = json.loads(tool_call.function.arguments)
                console.print(f"[cyan]→ {name}[/cyan]")
                result = _execute_tool(name, inp)
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })
            messages.extend(tool_results)


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
    args = parser.parse_args()

    if args.staleness:
        run_staleness_check(months=args.months)
        return

    if args.rollback:
        result = rollback_zendesk_article(args.rollback)
        console.print(result)
        return

    run_agent(manual_mode=args.manual)


if __name__ == "__main__":
    main()
