# Pergamon Docs Agent — Persistent Memory

This file is loaded on every run. It contains Pergamon-specific terminology, style overrides, and templates the agent must follow at all times.

---

## Product Overview

**Pergamon** is an AI-powered technical documentation platform that automates the creation of user manuals and compliance documentation for consumer retail hardware products — such as coffee machines, steam irons, power drills, and luminaires.

**How it works:**
1. **AI Questionnaire** — Users answer product-specific questions (e.g. "Does the milk frother use rechargeable or replaceable batteries?"). Pergamon's AI uses these answers to assemble a first draft of the product's user manual automatically.
2. **Market & Compliance Assembly** — Based on the target market (e.g. EU, UK, US), Pergamon automatically includes the relevant regulatory, compliance, and safety information required for that region.
3. **Rich Text Editor** — The assembled draft is edited in Pergamon's built-in rich text editor. AI features are available directly in the editor — users can run pre-configured prompts or upload product videos and generate content from them.
4. **Translation Workflow** — Content is translated into multiple languages within the platform to support international markets.
5. **Publication Output** — The final output is a fully compliant publication exported in formats such as booklets or leaflets, ready for print or digital distribution.

**Target customers:** Consumer hardware brands and retailers such as LIDL, Amazon, and Briloner — companies that sell physical products requiring regulatory-compliant user manuals across multiple markets.

**Core value:** Pergamon replaces manual, time-consuming documentation processes with an AI-driven workflow that ensures compliance, consistency, and speed across product lines and markets.

---

## Pergamon Terminology

Always use these exact terms. Never paraphrase or substitute.

| Term | Definition |
|---|---|
| **Content Artifact** | A reusable unit of structured content. The core building block of Pergamon. |
| **ACA Workflow** | Pergamon's authoring, review, and content approval workflow |
| **Knowledge Library** | The central repository of all content artifacts in a Pergamon workspace |
| **Publication** | A compiled output document built from content artifacts |
| **Global Content** | Content shared across multiple articles that cannot be edited locally without explicit permission |
| **Downloads Panel** | The panel where users track and download background export jobs |
| **Workspace Owner** | The admin-level user role with full permissions in a Pergamon workspace |
| **Content ID** | The unique identifier assigned to each content block in the editor |
| **InDesign export** | Pergamon's export to Adobe InDesign format |

---

## Style Guide Priority Order

1. **Stripe Documentation Style** — primary reference for tone, structure, step writing, and callouts
2. **Diataxis Framework** — https://diataxis.fr — for article type classification
3. Pergamon-specific overrides in this file (highest priority)

---

## Writing Style — Stripe Docs Standard

Model all documentation on Stripe's documentation style. Key principles:

### Tone and voice
- Write directly to the reader: "you", "your" — never "the user" or "users"
- Active voice always. Cut passive constructions.
- Present tense for UI states and actions: "Click **Save**" not "Click on **Save**"
- Be concise. Strip filler phrases: never write "Follow the steps below to…", "In order to…", "Please note that…"
- Sentence case for all headings. Never Title Case.

### Step writing rules — critical
Every step must describe exactly one physical action. Apply these rules strictly:

- **One action per step.** If a step contains "then" or "and", split it.
- **Start every step with an imperative verb:** Click, Select, Enter, Navigate, Toggle, Open, Copy, Paste. Never start with "Find", "Locate", "Go to", or "Make sure".
- **Bold every UI element name** exactly as it appears in the product: **Attributes**, **Origin**, **Assembly report**
- **Use › for navigation paths** when describing menu sequences: Select **Attributes** › **Basic attributes**
- **Combine orientation and action.** Never write a step that only orients ("Find the Origin field"). Merge it into the action step: "In the **Origin** field, click the download icon."
- **No preamble before numbered steps.** One sentence of context is the maximum before the list begins.
- Sub-steps use lettered lists (a, b, c) only when a step has genuinely parallel options — not for sequential actions.

### What good looks like — example
❌ Bad (current output):
> 3. Select Basic attributes.
> 4. Find the Origin field.
> 5. To download the QC report, click on the download icon located to the right of the Origin field.

✅ Stripe style:
> 3. Select **Basic attributes**.
> 4. In the **Origin** field, do one of the following:
>    - To download the report, click the download icon on the right.
>    - To view the report in the UI, click **Assembly report**.

### Callouts — when to use each type
- **Note** — supplementary information the reader might find useful but can skip
- **Tip** — a shortcut, best practice, or efficiency hint
- **Warning** — something that could cause data loss, unexpected behaviour, or extra work to undo
- **Danger** — an irreversible or destructive action

Use callouts sparingly. One per section maximum. Never use a callout for information that belongs in the main text.

---

## Zendesk HTML Callout Formats

Use these exact HTML blocks. Style matches Stripe docs: clean background, subtle left border, no heavy box shadows.

### Note (blue — supplementary info)
```html
<div style="background-color: #f6f9fc; border-left: 3px solid #6772e5; padding: 12px 16px; margin: 16px 0; border-radius: 0 4px 4px 0; font-size: 14px; color: #3c4257;">
  <strong style="color: #6772e5;">Note</strong><br>[content]
</div>
```

### Tip (teal — shortcut or best practice)
```html
<div style="background-color: #f4fbf8; border-left: 3px solid #09825d; padding: 12px 16px; margin: 16px 0; border-radius: 0 4px 4px 0; font-size: 14px; color: #3c4257;">
  <strong style="color: #09825d;">Tip</strong><br>[content]
</div>
```

### Warning (amber — may cause unexpected behaviour)
```html
<div style="background-color: #fcf8ee; border-left: 3px solid #c5850c; padding: 12px 16px; margin: 16px 0; border-radius: 0 4px 4px 0; font-size: 14px; color: #3c4257;">
  <strong style="color: #c5850c;">Warning</strong><br>[content]
</div>
```

### Danger (red — irreversible or destructive)
```html
<div style="background-color: #fff8f8; border-left: 3px solid #cd3d64; padding: 12px 16px; margin: 16px 0; border-radius: 0 4px 4px 0; font-size: 14px; color: #3c4257;">
  <strong style="color: #cd3d64;">Danger</strong><br>[content]
</div>
```

### Release header box (used in release notes)
```html
<div style="background-color: #eef3f8; border-left: 4px solid #1f73b7; padding: 18px 22px; margin: 20px 0; border-radius: 6px; font-family: Arial, sans-serif; line-height: 1.6; color: #1f2933;">
  <p style="margin: 0 0 10px 0; font-size: 14px; color: #4b5563;">
    <strong>Release date:</strong> [Date], [Time] HKT ([UTC time] UTC)
  </p>
  <p style="margin: 0; font-size: 15px;">
    <strong>Release highlights:</strong> [2-3 sentence summary]
  </p>
</div>
```

---

## AEO (Answer Engine Optimization) Rules

Apply to every article written or updated:

### TL;DR block (top of every article, before main content)
```html
<div style="background-color: #f0f4ff; border-left: 4px solid #4a6cf7; padding: 12px 16px; margin: 0 0 20px 0; border-radius: 4px;">
  <strong>TL;DR:</strong> [2-3 sentence plain-language summary of what this article covers and who it's for]
</div>
```

### FAQ section (bottom of every article, before any footer)
```html
<h2>Frequently asked questions</h2>

<h3>[Natural language question a user or AI would ask?]</h3>
<p>[Direct, concise answer in 1-3 sentences.]</p>

<h3>[Another natural language question?]</h3>
<p>[Answer]</p>
```
- Minimum 3 FAQs per article, maximum 5
- Questions must be phrased as a real user or AI assistant would ask them
- Answers must be self-contained — no "see above" or "as mentioned"

### Schema markup
For how-to guides and tutorials — inject after the article body:
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "[Article title]",
  "description": "[TL;DR text]",
  "step": [
    {"@type": "HowToStep", "text": "[Step 1 text]"},
    {"@type": "HowToStep", "text": "[Step 2 text]"}
  ]
}
</script>
```

For articles with FAQ sections:
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "[Question text]",
      "acceptedAnswer": {"@type": "Answer", "text": "[Answer text]"}
    }
  ]
}
</script>
```

---

## Release Notes Template

Article title format: `Release Notes - Version X.X.X`
Section ID: `15005482487055`

```html
[Release header box with date and highlights summary]

<p>🎥 Prefer a quick overview? Watch the X.X.X release highlights below.</p>
[Synthesia video link and thumbnail OR [VIDEO NEEDED] placeholder]

<h2>New features</h2>

<h3>[Feature name]</h3>
<p>[1-2 sentence description of what the feature does.]</p>
<ul>
  <li>[Specific capability or behaviour]</li>
  <li>[Specific capability or behaviour]</li>
</ul>
<p>[Benefit sentence: This improves/enables X by allowing you to Y.]</p>
[SCREENSHOT NEEDED: description of what to capture]

<h2>Improvements</h2>

<h3>[Improvement name]</h3>
<p>[Description and bullets as needed]</p>

<h2>Fixes</h2>
<ul>
  <li>[Fixed issue description]</li>
</ul>

<h2>System and backend updates</h2>
<p>Additional internal improvements and refinements to support stability and performance.</p>

<h2>Get the latest version</h2>
<p>Click <strong>Refresh</strong> when prompted to load the latest updates. Check your version from the top-right profile menu.</p>

[Need help footer — copy verbatim from previous release notes article]
```

---

## Article Templates — Stripe Structure

### How-to guide
- **Title:** "How to [verb] [object]" — e.g. "How to view and download a QC report"
- **Opening:** One sentence stating when or why you'd do this. No "In this article" or "This guide will show you".
- **Prerequisites** (if any): bullet list of what the user needs before starting
- **Steps:** Numbered list. One action per step. Bold all UI element names. Use › for navigation paths.
- **What you'll see / next steps:** One short sentence or a "What's next" link list at the end.
- No subheadings within the steps unless there are two separate procedures (e.g. "Download the report" and "View the report in the UI" as H3s with their own step lists)

### Tutorial
- **Title:** "Get started with [feature]"
- **Opening:** What the reader will build or accomplish by the end
- **Prerequisites:** bullet list
- **Steps:** Numbered, with one sentence of "why this matters" after each major step
- **Summary:** What was accomplished + 2-3 "Next steps" links

### Reference
- **Title:** "[Feature] reference" or "[Panel/Field] overview"
- No steps — structured as a definition list or table of fields, options, and behaviours
- Each field/option: **name** — description of what it does and when to use it

### Explanation (conceptual)
- **Title:** "About [concept]" or "How [feature] works"
- **Opening:** The concept in plain language — what it is and why it exists
- **Body:** Context, background, how it fits into the broader product
- No steps. Use short paragraphs and subheadings to break up sections.

---

## Screenshot embedding format

When a screenshot has been uploaded via `upload_article_image` and a CDN URL is available, embed it immediately after the step it illustrates using this exact HTML:

```html
<figure style="margin: 16px 0;">
  <img src="[CDN URL]" alt="[brief alt text describing the UI state]" style="max-width: 100%; border-radius: 4px; border: 1px solid #e0e0e0;">
  <figcaption style="font-size: 13px; color: #6b7280; margin-top: 6px;">[Descriptive present-tense caption]</figcaption>
</figure>
```

**Caption rules:**
- Descriptive present tense: "The Origin field showing the download icon and Assembly report button."
- Describe what is visible on screen — not what the user should do
- No "Screenshot of…" or "Image showing…" — start with the subject directly
- Keep captions under 15 words

**Placement:** Always after the step the screenshot illustrates, never before it and never grouped at the end.

## Screenshot placeholder format

When no screenshot has been uploaded yet, insert:

`[SCREENSHOT NEEDED: description of what screen/state to capture]`

Examples:
- `[SCREENSHOT NEEDED: Downloads panel open with an active export in progress]`
- `[SCREENSHOT NEEDED: Content Artifact editor with Global Content toggle enabled]`

Never remove existing screenshots or `<img>` tags from articles.

---

## Zendesk Section IDs (known)

| Section | ID |
|---|---|
| Release Notes | `15005482487055` |

(Add more as discovered)

## Release Notes Reference Article

When drafting a new release notes article, always fetch article `15563866700687` (Release Notes - Version 3.7.0) to copy the following sections verbatim:
- **"Get the latest version"** section (H2)
- **"Need help?"** footer block

Use `get_zendesk_article` with ID `15563866700687` to retrieve it. Do NOT use the section ID `15005482487055` as an article ID — it is a section ID only.

---

## Changelog

See `changelog.md` in this directory for the full audit trail.
