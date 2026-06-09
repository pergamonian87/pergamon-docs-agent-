---
layout: default
title: Pergamon Docs Agent
---

# Pergamon Docs Agent

An AI-powered documentation agent that automates Zendesk help center publishing for Pergamon Labs. It handles release documentation, article rewrites, ad-hoc article creation, ticket-driven docs, and Slack thread refreshes — all from the terminal, with human approval at every step.

---

## Workflows

| Command | What it does |
|---|---|
| `python3 main.py` | Release workflow — fetch latest Slack release thread and update KB |
| `python3 main.py --manual` | Release workflow — paste release notes manually |
| `python3 main.py --version 3.9.0` | Target a specific release version on Slack |
| `python3 main.py --refresh --version 3.9.0` | Re-parse a thread for new comments since last run |
| `python3 main.py --ticket 12345` | Create a new article from a Zendesk support ticket |
| `python3 main.py --new "Article title"` | Create a new article ad-hoc |
| `python3 main.py --rewrite "Article title"` | Rewrite an existing article (by title or ID) |
| `python3 main.py --staleness` | Audit articles not updated in 6+ months |
| `python3 main.py --rollback 12345678` | Rollback a specific article by Zendesk ID |
| `python3 main.py --audit` | AEO audit — scan all articles for missing TL;DR, FAQ, and schema markup |
| `python3 main.py --lint "Article title"` | Style lint — review an article against Stripe docs conventions |
| `python3 main.py --aeo-retrofit` | AEO retrofit — bulk-add TL;DR, FAQ, and schema to articles that need it |

---

## Documentation

- [Architecture](architecture) — System design, workflows, components, and data flow
- [Setup Guide](setup) — Installation, configuration, and credentials
- [Workflow Guide](workflow) — All workflows and human checkpoints explained
