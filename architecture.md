# Pergamon Docs Agent — Architecture

```mermaid
flowchart TD
    %% Entry Point
    SLACK["📢 Slack #release channel\nJakub posts release notes\n(free-form text)"]

    %% Core Engine
    CLAUDE["🧠 Claude Opus 4.6\nAnthropic API\nInference Engine"]

    %% Memory Layer
    subgraph MEMORY["💾 Persistent Memory"]
        CM["CLAUDE.md\nStyle guide, Diataxis rules\nPergamon terminology"]
        ENV[".env\nAPI credentials"]
        CL["changelog.md\nVersion history log"]
        SKILLS["~/.claude/commands/\nSkill files per doc type"]
    end

    %% Tools
    subgraph TOOLS["🔧 Tools"]
        SLACK_TOOL["Slack API\nRead #release channel"]
        ZD_READ["Zendesk API (Read)\nFetch all articles"]
        ZD_WRITE["Zendesk API (Write)\nUpdate / Create / Publish\nRollback"]
        ZD_VER["Zendesk Version History\nRollback support"]
    end

    %% Human in the Loop
    subgraph HUMAN["👤 Human in the Loop (Terminal)"]
        H1["Step 1: Confirm\nrelease feature list"]
        H2["Step 2: Describe\nfeatures interactively"]
        H3["Step 3: Review\narticle list"]
        H4["Step 4: Review\ndiff & changelog"]
        H5["Step 5: Final\napproval to publish"]
    end

    %% Output
    subgraph OUTPUT["📤 Output"]
        UP["Updated Articles\n(live on Zendesk)"]
        NEW["New Articles\n(live on Zendesk)"]
        REPORT["Post-publish Report\n+ changelog.md entry"]
        PLACEHOLDERS["Screenshot Placeholders\nfor team to fill in"]
        STALE["Staleness Report\n(periodic check)"]
        MULTI["Multi-language Flags\nTranslations needing review"]
    end

    %% Flow
    SLACK --> SLACK_TOOL
    SLACK_TOOL --> CLAUDE
    CM --> CLAUDE
    ENV --> CLAUDE
    SKILLS --> CLAUDE

    CLAUDE <-->|"Step 1: Parse & confirm\nrelease items"| H1
    H1 <-->|"Step 2: Feature\ndescription Q&A"| H2
    H2 --> CLAUDE

    CLAUDE --> ZD_READ
    ZD_READ -->|"All articles"| CLAUDE

    CLAUDE <-->|"Step 3: Article\nlist review"| H3
    H3 --> CLAUDE

    CLAUDE <-->|"Step 4: Diff\nreview per article"| H4
    H4 <-->|"Step 5: Approve\nto publish"| H5

    H5 --> ZD_WRITE
    ZD_WRITE --> UP
    ZD_WRITE --> NEW
    ZD_WRITE --> REPORT
    REPORT --> CL

    CLAUDE --> PLACEHOLDERS
    CLAUDE --> MULTI
    ZD_VER -.->|"Rollback on request"| ZD_WRITE

    STALE -.->|"Periodic check\n(independent run)"| CLAUDE
```

---

## Layer Breakdown

### 🧠 Inference — Claude Opus 4.6
The brain. Reads inputs, reasons about what needs updating, drafts content, manages the conversation flow with the user.

### 💾 Memory — Persistent Files
| File | Purpose |
|---|---|
| `CLAUDE.md` | Always-on style guide, Diataxis rules, Pergamon terminology |
| `.env` | API credentials — Slack, Zendesk, Anthropic |
| `changelog.md` | Running log of all releases and doc changes |
| `~/.claude/commands/` | Skill files per Diataxis doc type |

### 🔧 Tools — External APIs
| Tool | Action |
|---|---|
| Slack API | Read #release channel threads |
| Zendesk API (Read) | Fetch all articles and version history |
| Zendesk API (Write) | Update, create, publish, rollback articles |

### 👤 Human in the Loop — Terminal
5 checkpoints where the user must confirm before the agent proceeds. Nothing is published without explicit approval.

### 📤 Output
- Updated articles live on Zendesk
- New articles live on Zendesk
- Post-publish report in terminal
- Changelog entry logged to file
- Screenshot placeholders for the team
- Multi-language flags for translation team
- Staleness reports (periodic, independent)
```
