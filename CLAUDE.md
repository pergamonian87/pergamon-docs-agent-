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

1. **Microsoft Writing Style Guide** — https://learn.microsoft.com/en-us/style-guide/welcome/
2. **Google Developer Documentation Style Guide** — https://developers.google.com/style
3. **Diataxis Framework** — https://diataxis.fr
4. Pergamon-specific overrides in this file (highest priority)

---

## Pergamon Writing Conventions

- Use **second person** ("you", "your") — never "the user" or "users"
- Use **active voice** always
- Use **sentence case** for headings (not Title Case)
- Use **present tense** for describing UI states ("Click **Save**", not "Click on **Save**")
- Bold all **UI element names** on first use per article
- Steps use numbered lists. Sub-steps use lettered lists (a, b, c).
- Each step starts with an action verb: "Click", "Select", "Enter", "Navigate"
- End each feature description with a benefit sentence: "This [improves/enables/allows] you to [outcome]."

---

## Zendesk HTML Callout Formats

Use these exact HTML blocks for callouts:

### Note (blue)
```html
<div style="background-color: #eef3f8; border-left: 4px solid #1f73b7; padding: 12px 16px; margin: 16px 0; border-radius: 4px;">
  <strong>Note:</strong> [content]
</div>
```

### Warning (yellow)
```html
<div style="background-color: #fff8e1; border-left: 4px solid #f9a825; padding: 12px 16px; margin: 16px 0; border-radius: 4px;">
  <strong>Warning:</strong> [content]
</div>
```

### Tip (green)
```html
<div style="background-color: #e8f5e9; border-left: 4px solid #2e7d32; padding: 12px 16px; margin: 16px 0; border-radius: 4px;">
  <strong>Tip:</strong> [content]
</div>
```

### Danger (red)
```html
<div style="background-color: #ffebee; border-left: 4px solid #c62828; padding: 12px 16px; margin: 16px 0; border-radius: 4px;">
  <strong>Danger:</strong> [content]
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

## Diataxis Article Templates

### How-to guide
- Title: "How to [verb] [object]" (e.g. "How to export a publication in the background")
- Starts with: 1-2 sentence context (when/why you'd do this)
- Body: numbered steps
- Ends with: what success looks like

### Tutorial
- Title: "Getting started with [feature/concept]"
- Starts with: what the reader will learn and accomplish
- Body: guided steps with explanation of why each step matters
- Ends with: summary of what was learned + next steps

### Reference
- Title: "[Feature/Element] reference" or "About [feature]"
- Structured factual information: fields, options, behaviours
- No step-by-step — just descriptions

### Explanation
- Title: "Understanding [concept]" or "About [concept]"
- Starts with: the concept and why it matters
- Body: context, background, how it fits into the bigger picture
- No steps — conceptual only

---

## Screenshot Placeholder Format

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

---

## Changelog

See `changelog.md` in this directory for the full audit trail.
