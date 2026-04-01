---
layout: default
title: Workflow Guide
---

<a href="{{ site.baseurl }}/" style="font-size:14px;">← Pergamon Docs Agent</a>

# Pergamon Docs Agent — Workflow Guide

## Overview

The Pergamon Docs Agent follows a 9-step interactive workflow. It does not act autonomously — it works collaboratively with you in the terminal, pausing at 5 checkpoints for your input and approval. Nothing is published without your explicit sign-off.

---

## The 9-Step Workflow

### Step 1 — Fetch Release Notes
**What happens:** Agent reads the latest release thread from Slack #release channel, or accepts a manual paste if Slack is not configured. After fetching, the agent will prompt you interactively using the terminal — it will not stop automatically.

**Input:** Jakub's free-form release post (any format)

**Output:** Structured internal list of:
- New features
- Improvements
- Bug fixes

**Note:** The `pergamon_docs_agent` bot must be a member of the `#release` channel. If not, invite it with `/invite @pergamon_docs_agent` in Slack.

---

### Step 2 — Confirm Feature List ⛔ Checkpoint 1
**What happens:** Agent presents the parsed feature list for your review.

**You:** Confirm the list is complete and accurate, or correct any misinterpretations.

**Example:**
```
Agent: I've parsed the following from the release thread:

New Features:
1. Background export — documents and publications can be exported in background
2. Downloads panel — new panel to track export progress

Improvements:
1. Table performance improvements

Fixes:
1. Login session persistence fix

Is this list correct and complete?

Your response: Yes, correct. Also add: password lock management for user accounts.
```

---

### Step 3 — Feature Description Q&A ⛔ Checkpoint 2
**What happens:** For each feature or change, the agent asks you to describe how it works, the steps to use it, and the nature of the update.

**You:** Answer in plain language. The agent asks follow-up questions if it needs more detail.

**Example:**
```
Agent: Can you describe how the background export feature works?

Your response: Users click Export as usual but now there's a new option
"Export in background". The export starts and they can keep working.
Progress shows in the new Downloads panel in the top toolbar.

Agent: What file formats does the background export support?

Your response: All existing formats — PDF, InDesign, Word.
```

**Tip:** Use `/note` at any prompt to inject additional context without submitting your answer:
```
Your response: /note this only works for documents over 10 pages
✓ Note saved
Your response: Yes, all formats are supported
```

---

### Step 4 — Article Discovery ⛔ Checkpoint 3
**What happens:** Agent asks how you want to find impacted articles. Three options:

**Option 1 — Scan all titles**
Agent fetches all 194 article titles (metadata only, cheap) and suggests a shortlist based on the release features. You confirm before any full article is fetched.

**Option 2 — Search by section**
Agent shows the full section list. You pick which sections to search. Agent only looks within those sections.

**Option 3 — Direct article IDs or titles**
You provide the article IDs or titles directly. Agent fetches only those. Fastest and cheapest option — use this when you already know which articles are affected.

**Example:**
```
How do you want to find impacted articles?
1. Scan all article titles
2. Search by section
3. Provide article IDs or titles directly

Your choice: 3

Enter article titles or IDs: Export a Document, Export a Publication, 15563866700687
```

---

### Step 5 — Article List Review ⛔ (part of Checkpoint 3)
**What happens:** Agent presents the confirmed article list — articles to update and articles to create new.

**You:** Confirm the list, add any missed articles, or remove any that don't apply.

**Example:**
```
Articles to update:
1. Export a Document (ID: 12415851411215)
2. Export a Publication (ID: 12088831434383)

Articles to create:
3. Release Notes - Version 3.8.0 (new)

Is this list complete?

Your response: Also update: Document export and preview issues (14787331383311)
```

---

### Step 5b — Drafting + AEO Pass (automatic)
**What happens:** Agent drafts all article updates and new articles, then automatically runs an AEO pass on every draft. No user interaction needed at this step.

**AEO pass applies automatically:**
- TL;DR summary block added at article top
- FAQ section (3-5 Q&As) appended at article bottom
- Schema markup (HowTo / FAQPage) injected into HTML
- Vague headings rewritten as specific questions
- Pergamon terms defined on first use

**Also at this step:**
- Agent calls Synthesia API to create the release highlights video
- Video URL and thumbnail are embedded into the release notes draft

---

### Step 6 — Diff Review ⛔ Checkpoint 4
**What happens:** Agent shows the proposed changes for each article, one at a time. HTML is stripped and displayed as readable text.

**You:** For each article, choose:
- `approve` — accept the changes as-is
- `skip` — don't update this article
- `edit` — describe what you want changed, agent redrafts

**Example:**
```
UPDATE — Export a Document (ID: 12415851411215)
Summary: Added section on background export with Downloads panel instructions.

TL;DR: This article explains how to export documents in Pergamon...

## How to export a document in the background
1. Click File → Export
2. Select your export format
3. Click Export in background
...

Review [approve/skip/edit]: edit
Describe the changes you want: Add a note that background export only works for documents over 10 pages
```

---

### Step 7 — Publish Approval ⛔ Checkpoint 5
**What happens:** Agent presents a final summary of everything about to be published and asks for explicit confirmation.

**You:** Type `y` to publish or `n` to cancel.

**Example:**
```
Ready to Publish:
UPDATE  Export a Document
UPDATE  Export a Publication
UPDATE  Document export and preview issues
NEW     Release Notes - Version 3.8.0

Publish all approved articles to Zendesk now? [y/n]: y
```

---

### Step 8 — Publish
**What happens:** Agent publishes all approved articles to Zendesk. Each article is retried up to 3 times if a publish fails. Failed articles are saved locally to `/drafts/`.

```
→ Publishing article 12415851411215...
✓ Published: https://support.pergamon-labs.com/hc/en-us/articles/...

→ Publishing article 12088831434383...
✓ Published: https://support.pergamon-labs.com/hc/en-us/articles/...
```

---

### Step 9 — Post-Publish Report
**What happens:** Agent updates `changelog.md` and `llms.txt`, then prints a summary.

```
✓ Changelog updated
✓ llms.txt updated

Release v3.8.0 complete:
- Updated: 3 articles
- Created: 1 article (Release Notes)
- Video: https://share.synthesia.io/...
```

---

## Additional Run Modes

### Staleness Check
Run independently of the release workflow to identify outdated articles:

```bash
python3 main.py --staleness
python3 main.py --staleness --months 3
```

Outputs a table of all articles not updated within the threshold, sorted by age.

### Rollback
Restore an article to its previous version:

```bash
python3 main.py --rollback 15563866700687
```

---

## Tips for Best Results

| Situation | Recommendation |
|---|---|
| Small release (1-2 features) | Use Option 3 (direct IDs) — fastest, cheapest |
| Large release (many features) | Use Option 1 (scan titles) — agent helps identify impacted articles |
| You know the sections affected | Use Option 2 (by section) — good middle ground |
| Agent misses an article | Add it at Step 5 review — paste the title or ID |
| Agent draft needs changes | Choose `edit` at Step 6 and describe what to change in plain language |
| Need to add context mid-workflow | Use `/note` at any prompt |
