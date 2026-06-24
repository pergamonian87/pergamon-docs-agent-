---
layout: default
title: Workflow Guide
---

<a href="{{ site.baseurl }}/" style="font-size:14px;">← Pergamon Docs Agent</a>

# Pergamon Docs Agent — Workflow Guide

The agent never publishes autonomously. Every workflow pauses at human checkpoints and requires explicit approval before anything goes live on Zendesk.

---

## Workflow 1 — Release documentation update

Triggered after a product release. Reads the Slack #release thread, identifies impacted articles, drafts updates and release notes, and publishes after approval.

```bash
python3 main.py                       # fetch latest Slack thread
python3 main.py --manual              # paste release notes manually
python3 main.py --version 3.9.0      # target a release by version number
python3 main.py --version 15.06.2026 # target a release by date-based thread title
```

### Steps

**Step 1 — Fetch release notes**
Agent reads the latest thread from Slack #release, or accepts a manual paste. Falls back to manual if Slack credentials are not configured.

**Step 2 — Confirm feature list** ⛔ Checkpoint
Agent presents the parsed feature list. You confirm it's complete and correct, or add/remove items.

**Step 3 — Feature description Q&A** ⛔ Checkpoint
For each feature, the agent asks you to describe how it works. Answer in plain language. Use `/doc` to drop engineering specs or `/img` to drop screenshots at this step.

**Step 3b — Web research** (automatic, silent)
Before asking about article discovery, the agent runs 3–5 web searches to research the topic: how leading documentation sites explain it, industry terminology, and common user questions. Results inform structure, analogies, and FAQs — not copied directly into the article.

**Step 4 — Article discovery** ⛔ Checkpoint
Agent asks how to find impacted articles. Three options:
- **Option 1** — Scan all article titles, agent suggests a shortlist
- **Option 2** — Search within specific sections you name
- **Option 3** — Provide article IDs or titles directly (fastest)
- **Option 4** — Skip discovery, create all new articles

**Step 5 — Article list review** ⛔ Checkpoint
Agent presents the confirmed shortlist. You add any missed articles or remove any that don't apply.

**Step 6 — Draft + AEO pass** (automatic)
Agent drafts all updates and new articles. Automatically applies AEO pass to every draft: TL;DR block, FAQ section, schema markup. Calls Synthesia to generate the release highlights video.

**Step 7 — Diff review** ⛔ Checkpoint
Agent shows proposed changes article by article. For each, choose:
- `approve` — accept as-is
- `skip` — don't update this article
- `edit` — describe what to change, agent redrafts

Use `/img` or `/doc` at any diff step to inject additional context.

**Step 8 — Publish approval** ⛔ Checkpoint
Agent presents the final publish summary. Type `y` to publish or `n` to cancel.

**Step 9 — Publish + post-publish refinement**
Agent publishes all approved articles. After publishing, enters a refinement loop:
- "Does everything look correct?"
- "Anything to refine?" — paste text from the article with an instruction (e.g. "make this simpler", "wrap in a warning callout")
- Agent patches and republishes. Repeat until you type "done".
- Changelog and llms.txt saved once at the end.

---

## Workflow 2 — Slack thread refresh

Re-parses a release thread for new comments added since the last run — stakeholder clarifications, corrections, or additions.

```bash
python3 main.py --refresh --version 3.9.0
```

Requires `--version` to be provided. The agent reads `drafts/slack_state.json` to find the last-parsed timestamp and fetches only newer messages. Reports "no new comments" and stops if nothing has changed.

### Steps

1. Agent fetches new comments since last parse
2. You confirm which articles to update ⛔
3. Agent drafts targeted updates, presents diffs ⛔
4. Publish approval ⛔ → publish → changelog updated

---

## Workflow 3 — Ticket-driven article creation

Creates a new help article from a Zendesk support ticket. Reads the ticket, checks for duplicate articles, drafts a compliant article, publishes it, and closes the ticket with an internal note.

```bash
python3 main.py --ticket 12345
```

### Steps

1. Agent fetches ticket: subject, description, comments, tags
2. You confirm the parsed request ⛔
3. Agent scans KB for related articles and flags duplicates ⛔
4. You confirm article type (Diataxis) + section ⛔
5. Agent asks targeted gap questions ⛔ — use `/doc` or `/img` here
6. Agent drafts article, presents diff ⛔
7. Publish approval ⛔ → publish → ticket closed with internal note linking to article

---

## Workflow 4 — Ad-hoc new article

Creates a new help article from scratch with just a title as the starting point. No Slack release and no support ticket required.

```bash
python3 main.py --new "How to view and download a QC report"
```

### Steps

1. Agent asks for description, audience, and reference materials — drop `/img` or `/doc` here ⛔
2. Agent runs 3–5 web searches (silent): how leading docs sites explain the topic, industry terminology, common user questions. This informs structure and FAQs — not copied verbatim.
3. Duplicate detection runs silently. Section selected automatically. Agent only interrupts if a near-identical article is found.
4. Agent drafts the full article from scratch — synthesising research, source docs, and screenshots. Source docs are reference material only; no content is copied from them.
5. Claude (claude-opus-4-7) reviews the draft automatically — up to 3 rounds. Each round returns specific issues ([STYLE], [AEO], [TERMINOLOGY], [CONTENT]) for GPT-4o to fix. GPT-4o revises and resubmits until Claude returns "APPROVED" or 3 rounds are exhausted.
6. Diff review ⛔ → publish approval ⛔
6. Screenshots uploaded to Zendesk CDN, embedded in article with captions
7. Post-publish refinement loop → changelog + llms.txt saved on "done"

---

## Workflow 5 — Rewrite existing article

Rewrites an existing article to apply current style standards (Stripe docs), embed new screenshots, and republish.

```bash
python3 main.py --rewrite "How to view and download a QC report"
python3 main.py --rewrite 16413268283023   # by article ID
```

### Steps

1. Agent locates the article by ID or title search ⛔ (confirms match before fetching)
2. You drop screenshots `/img` or docs `/doc` — or skip ⛔
3. Agent runs 3–5 web searches (silent): how leading docs sites cover this topic, current best practices, real user questions. Used to identify gaps and outdated sections in the existing article.
4. Screenshots uploaded to Zendesk CDN immediately (article ID already known)
5. Agent rewrites — incorporating research findings, applying Stripe docs style, embedding screenshots after the steps they illustrate. Not a restyle: gaps are filled, outdated content is updated, FAQs are improved.
6. Claude reviews the rewrite automatically — up to 3 rounds of critique and revision before the diff is shown to you.
7. Diff review ⛔ → publish approval ⛔
8. `save_and_publish_article` saves and publishes atomically
9. Post-publish refinement loop → changelog + llms.txt saved on "done"

---

## Quality skills

Three skills run independently of the release workflow. Run them in sequence — audit first, then lint to inspect individual articles, then retrofit to fix them in bulk.

---

### Skill 1 — AEO audit (`--audit`)

```bash
python3 main.py --audit
python3 main.py --audit --audit-limit 20
```

Scans every article (or the most recently updated N) and checks for the three AEO elements: TL;DR block, FAQ section, and JSON-LD schema markup. No LLM — pure string matching. Results are saved to `drafts/audit_results.json` and printed as a table.

**Output columns:** Article ID, title, has TL;DR, has FAQ, has schema, last updated.

The audit output is the input for `--aeo-retrofit` — run audit first so retrofit knows which articles to fix.

---

### Skill 2 — Style lint (`--lint`)

```bash
python3 main.py --lint "How to export a publication"
python3 main.py --lint 16413268283023
```

Agent-based workflow. Fetches the article, checks it against Stripe docs conventions (step structure, callout usage, heading case, bold UI elements, benefit sentences), and presents a prioritised list of issues with suggested rewrites. No automatic publishing — review output only.

---

### Skill 3 — AEO retrofit (`--aeo-retrofit`)

```bash
python3 main.py --aeo-retrofit
python3 main.py --aeo-retrofit 16413268283023,16413268283024
```

Bulk-adds missing AEO elements to articles. Without arguments, reads `drafts/audit_results.json` and processes all flagged articles. With a comma-separated ID list, processes only those articles.

For each article, the agent adds only the missing elements (e.g. if FAQ exists but TL;DR and schema are missing, only those two are added). Human approval required before each publish.

**Recommended sequence:**

```
1. python3 main.py --audit              # identify gaps
2. python3 main.py --lint "Article"     # inspect individual articles
3. python3 main.py --aeo-retrofit       # fix all flagged articles
```

---

## Maintenance modes

### Staleness audit

```bash
python3 main.py --staleness
python3 main.py --staleness --months 3
```

Scans all articles and reports any not updated within the threshold (default: 6 months). Outputs a sorted table — no publishing involved.

### Rollback

```bash
python3 main.py --rollback 16413268283023
```

Fetches rollback information for the specified article ID. Zendesk does not expose historical versions via API — use Zendesk Guide's Article Versions UI for the actual restore, or retrieve a local draft from `/drafts/` if one was saved.

---

## Context injection — at any prompt

| Command | What it does |
|---|---|
| `/modes` | Print all CLI modes at a glance. Workflow continues uninterrupted after. |
| `/img path/to/screen.png` | Screenshot sent to GPT-4o vision. Agent reads UI labels verbatim and uses them for step content. Image uploaded to Zendesk and embedded in the article with a caption. |
| `/doc path/to/file.md` | Engineering doc (MD, TXT, RST, PDF, DOCX). Agent extracts end-user content only — strips component names, TypeScript interfaces, internal APIs, rendering pipeline details, and framework internals. |
| `/doc path/to/folder/` | Loads all supported doc files from a directory as a batch. Useful for dropping a full engineering spec folder at once. |
| `/note your message` | Side note injected into the next agent message. Does not submit your main answer. |

Multiple `/img` and `/doc` commands can appear in one input. Paths with spaces can be backslash-escaped.

---

## Post-publish refinement loop

After every publish (all workflows), the agent enters a refinement loop before saving the changelog:

```
Agent: The article is live at [URL]. Does everything look correct?
You:   yes

Agent: Anything to refine? Paste text with an instruction, or type 'done'.
You:   "Once the AI Assembly completes..." → make this opening sentence shorter

Agent: Done — article updated. Anything else, or type 'done'?
You:   done

✓ Changelog updated
✓ llms.txt updated
```

Supported instructions: "rewrite this", "make this simpler", "wrap in a warning callout", "split this into two steps", "add a note about X".

The changelog and llms.txt are saved only once — after the refinement loop ends.
