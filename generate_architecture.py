"""
Generates a detailed architecture diagram for the Pergamon Docs Agent
and exports it as a PNG file.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe

# ── Canvas ──────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(24, 18))
ax.set_xlim(0, 24)
ax.set_ylim(0, 18)
ax.axis("off")
fig.patch.set_facecolor("#0f1117")
ax.set_facecolor("#0f1117")

# ── Colour palette ───────────────────────────────────────────────────────────
C = {
    "slack":    "#4a154b",
    "claude":   "#c05c1c",
    "memory":   "#1a3a5c",
    "tools":    "#1a4a2e",
    "human":    "#3a2a1a",
    "output":   "#1a1a4a",
    "border":   "#ffffff",
    "text":     "#ffffff",
    "subtext":  "#cccccc",
    "arrow":    "#aaaaaa",
    "highlight":"#f0a500",
    "bg":       "#0f1117",
}

# ── Helper functions ─────────────────────────────────────────────────────────
def box(ax, x, y, w, h, color, alpha=0.85, radius=0.3, zorder=2):
    rect = FancyBboxPatch((x, y), w, h,
                          boxstyle=f"round,pad=0.05,rounding_size={radius}",
                          facecolor=color, edgecolor="#ffffff",
                          linewidth=0.8, alpha=alpha, zorder=zorder)
    ax.add_patch(rect)

def label(ax, x, y, text, size=9, color="#ffffff", bold=False,
          ha="center", va="center", zorder=5):
    weight = "bold" if bold else "normal"
    ax.text(x, y, text, fontsize=size, color=color, fontweight=weight,
            ha=ha, va=va, zorder=zorder,
            fontfamily="monospace")

def arrow(ax, x1, y1, x2, y2, color="#aaaaaa", style="->", lw=1.5,
          label_text="", label_size=7.5):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color,
                                lw=lw, connectionstyle="arc3,rad=0.0"),
                zorder=4)
    if label_text:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx+0.1, my, label_text, fontsize=label_size,
                color=color, ha="left", va="center",
                fontfamily="monospace", zorder=6)

def section_title(ax, x, y, text, color):
    ax.text(x, y, text, fontsize=8.5, color=color, fontweight="bold",
            ha="left", va="center", fontfamily="monospace",
            alpha=0.9, zorder=6)

# ════════════════════════════════════════════════════════════════════════════
# TITLE
# ════════════════════════════════════════════════════════════════════════════
ax.text(12, 17.4, "PERGAMON DOCS AGENT — SYSTEM ARCHITECTURE",
        fontsize=15, color=C["highlight"], fontweight="bold",
        ha="center", va="center", fontfamily="monospace", zorder=6)
ax.text(12, 17.0, "Slack → Claude Opus 4.6 → Zendesk | Interactive Terminal Workflow",
        fontsize=9, color=C["subtext"], ha="center", va="center",
        fontfamily="monospace", zorder=6)

# ════════════════════════════════════════════════════════════════════════════
# 1. SLACK (Entry Point) — left top
# ════════════════════════════════════════════════════════════════════════════
box(ax, 0.4, 13.5, 3.8, 3.0, C["slack"])
section_title(ax, 0.7, 16.3, "① SLACK ENTRY POINT", "#bb86fc")
label(ax, 2.3, 15.7, "📢 #release channel", size=9, bold=True)
label(ax, 2.3, 15.2, "Posted by: Jakub", size=8, color=C["subtext"])
label(ax, 2.3, 14.7, "Free-form release notes:", size=8, color=C["subtext"])
label(ax, 2.3, 14.3, "• New features", size=8, color="#90ee90")
label(ax, 2.3, 13.95, "• Improvements", size=8, color="#90ee90")
label(ax, 2.3, 13.6, "• Bug fixes", size=8, color="#90ee90")

# ════════════════════════════════════════════════════════════════════════════
# 2. CLAUDE OPUS 4.6 — centre
# ════════════════════════════════════════════════════════════════════════════
box(ax, 8.5, 12.0, 7.0, 4.5, C["claude"], radius=0.4)
section_title(ax, 8.8, 16.3, "② INFERENCE ENGINE", "#f0a500")
label(ax, 12.0, 15.8, "🧠  Claude Opus 4.6", size=12, bold=True, color=C["highlight"])
label(ax, 12.0, 15.2, "Anthropic API  |  Adaptive Thinking ON", size=8.5, color=C["subtext"])

# inner detail boxes
box(ax, 8.8, 12.2, 3.0, 2.5, "#5a3010", alpha=0.7, radius=0.2)
label(ax, 10.3, 14.3, "NLP Tasks", size=8, bold=True, color="#f0a500")
label(ax, 10.3, 13.9, "Parse free-form Slack", size=7.5, color=C["subtext"])
label(ax, 10.3, 13.55, "Identify doc type", size=7.5, color=C["subtext"])
label(ax, 10.3, 13.2, "(Diataxis framework)", size=7.5, color=C["subtext"])
label(ax, 10.3, 12.85, "Detect article gaps", size=7.5, color=C["subtext"])
label(ax, 10.3, 12.5, "Cross-link suggestions", size=7.5, color=C["subtext"])

box(ax, 12.1, 12.2, 3.2, 2.5, "#5a3010", alpha=0.7, radius=0.2)
label(ax, 13.7, 14.3, "Content Tasks", size=8, bold=True, color="#f0a500")
label(ax, 13.7, 13.9, "Draft article updates", size=7.5, color=C["subtext"])
label(ax, 13.7, 13.55, "Create new articles", size=7.5, color=C["subtext"])
label(ax, 13.7, 13.2, "Generate diffs", size=7.5, color=C["subtext"])
label(ax, 13.7, 12.85, "Screenshot placeholders", size=7.5, color=C["subtext"])
label(ax, 13.7, 12.5, "Detect stale articles", size=7.5, color=C["subtext"])

# ════════════════════════════════════════════════════════════════════════════
# 3. PERSISTENT MEMORY — right top
# ════════════════════════════════════════════════════════════════════════════
box(ax, 17.0, 13.5, 6.5, 3.0, C["memory"])
section_title(ax, 17.3, 16.3, "③ PERSISTENT MEMORY", "#64b5f6")
# CLAUDE.md
box(ax, 17.2, 14.7, 1.8, 1.6, "#0d2a45", alpha=0.9, radius=0.15)
label(ax, 18.1, 15.8, "CLAUDE.md", size=8, bold=True, color="#64b5f6")
label(ax, 18.1, 15.45, "Style guides", size=7, color=C["subtext"])
label(ax, 18.1, 15.15, "Diataxis rules", size=7, color=C["subtext"])
label(ax, 18.1, 14.85, "Terminology", size=7, color=C["subtext"])
# .env
box(ax, 19.2, 14.7, 1.6, 1.6, "#0d2a45", alpha=0.9, radius=0.15)
label(ax, 20.0, 15.8, ".env", size=8, bold=True, color="#64b5f6")
label(ax, 20.0, 15.45, "Slack token", size=7, color=C["subtext"])
label(ax, 20.0, 15.15, "Zendesk creds", size=7, color=C["subtext"])
label(ax, 20.0, 14.85, "Anthropic key", size=7, color=C["subtext"])
# changelog.md
box(ax, 21.0, 14.7, 2.2, 1.6, "#0d2a45", alpha=0.9, radius=0.15)
label(ax, 22.1, 15.8, "changelog.md", size=8, bold=True, color="#64b5f6")
label(ax, 22.1, 15.45, "Per-release log", size=7, color=C["subtext"])
label(ax, 22.1, 15.15, "Articles changed", size=7, color=C["subtext"])
label(ax, 22.1, 14.85, "Audit trail", size=7, color=C["subtext"])
# skills
box(ax, 17.2, 13.55, 6.0, 0.9, "#0d2a45", alpha=0.9, radius=0.15)
label(ax, 20.2, 14.0, "~/.claude/commands/  →  /write-tutorial  /write-how-to  /write-reference  /update-article", size=7, color=C["subtext"])

# ════════════════════════════════════════════════════════════════════════════
# 4. HUMAN IN THE LOOP — centre vertical strip
# ════════════════════════════════════════════════════════════════════════════
box(ax, 8.5, 5.5, 7.0, 6.0, C["human"])
section_title(ax, 8.8, 11.3, "④ HUMAN IN THE LOOP  (terminal)", "#ffcc80")

steps = [
    ("Step 1", "Confirm parsed release feature list"),
    ("Step 2", "Describe features interactively (Q&A)"),
    ("Step 3", "Review article list — add missed articles"),
    ("Step 4", "Review plain text diff + changelog"),
    ("Step 5", "Final approval to publish"),
]
for i, (num, desc) in enumerate(steps):
    yy = 10.7 - i * 0.95
    box(ax, 8.8, yy - 0.35, 6.5, 0.75, "#5a4020", alpha=0.8, radius=0.15)
    label(ax, 9.6, yy + 0.02, f"✦ {num}:", size=8, bold=True,
          color="#ffcc80", ha="left")
    label(ax, 11.0, yy + 0.02, desc, size=8,
          color=C["subtext"], ha="left")

# ════════════════════════════════════════════════════════════════════════════
# 5. ZENDESK API — left middle/bottom
# ════════════════════════════════════════════════════════════════════════════
box(ax, 0.4, 5.5, 7.5, 6.0, C["tools"])
section_title(ax, 0.7, 11.3, "⑤ ZENDESK API", "#a5d6a7")

zd_items = [
    ("READ", [
        "List all articles",
        "Fetch full article HTML",
        "Fetch version history",
        "Get sections/categories",
    ]),
    ("WRITE", [
        "Update article body",
        "Create new articles",
        "Publish (draft → live)",
        "Rollback to prior version",
    ]),
]
xoff = 0.6
for method, items in zd_items:
    color = "#1e6e3a" if method == "READ" else "#6e1e1e"
    box(ax, xoff, 5.7, 3.3, 5.3, color, alpha=0.7, radius=0.2)
    label(ax, xoff + 1.65, 10.7, method, size=9, bold=True,
          color="#a5d6a7")
    for j, item in enumerate(items):
        label(ax, xoff + 1.65, 10.2 - j*0.85, f"• {item}",
              size=7.5, color=C["subtext"])
    xoff += 3.7

# Slack API note inside tools
box(ax, 0.6, 5.65, 7.0, 0.65, "#0d3020", alpha=0.8, radius=0.1)
label(ax, 4.1, 5.98,
      "Slack API  →  conversations.history  |  conversations.replies",
      size=7.5, color=C["subtext"])

# ════════════════════════════════════════════════════════════════════════════
# 6. OUTPUT — right bottom
# ════════════════════════════════════════════════════════════════════════════
box(ax, 17.0, 5.5, 6.5, 6.0, C["output"])
section_title(ax, 17.3, 11.3, "⑥ OUTPUT", "#90caf9")

outputs = [
    ("✅", "Updated articles live on Zendesk"),
    ("🆕", "New articles live on Zendesk"),
    ("📋", "Post-publish terminal report"),
    ("📝", "changelog.md entry logged"),
    ("📸", "Screenshot placeholders flagged"),
    ("🌐", "Multi-language flags raised"),
    ("⚠️",  "Staleness report (periodic)"),
    ("↩️",  "Rollback on request"),
]
for i, (icon, text) in enumerate(outputs):
    yy = 10.8 - i * 0.67
    label(ax, 17.5, yy, icon, size=9, ha="left")
    label(ax, 18.1, yy, text, size=8, color=C["subtext"], ha="left")

# ════════════════════════════════════════════════════════════════════════════
# ARROWS
# ════════════════════════════════════════════════════════════════════════════

# Slack → Claude
arrow(ax, 4.2, 15.0, 8.5, 14.5, color="#bb86fc", lw=2,
      label_text="release thread")

# Memory → Claude
arrow(ax, 17.0, 15.0, 15.5, 14.5, color="#64b5f6", lw=2,
      label_text="style rules")

# Claude ↔ Human (down)
arrow(ax, 12.0, 12.0, 12.0, 11.5, color="#ffcc80", lw=2,
      label_text="  interactive Q&A")
arrow(ax, 11.5, 11.5, 11.5, 12.0, color="#ffcc80", lw=1.5)

# Human → Zendesk (left)
arrow(ax, 8.5, 8.5, 7.9, 8.5, color="#a5d6a7", lw=2,
      label_text="")
ax.annotate("", xy=(7.9, 8.5), xytext=(8.5, 8.5),
            arrowprops=dict(arrowstyle="->", color="#a5d6a7", lw=2), zorder=4)

# Claude → Zendesk (read, diagonal left-down)
arrow(ax, 9.5, 12.0, 6.5, 11.0, color="#a5d6a7", lw=1.5,
      label_text=" fetch articles")

# Zendesk → Output (right)
arrow(ax, 7.9, 8.5, 17.0, 8.5, color="#90caf9", lw=2,
      label_text="  publish")

# Zendesk version history dashed rollback
ax.annotate("", xy=(4.1, 7.0), xytext=(17.0, 7.5),
            arrowprops=dict(arrowstyle="<-", color="#ff8a80", lw=1.5,
                            linestyle="dashed", connectionstyle="arc3,rad=-0.2"),
            zorder=4)
label(ax, 11.0, 6.7, "rollback (on request)", size=7.5,
      color="#ff8a80")

# Output → changelog
arrow(ax, 20.3, 11.5, 22.1, 14.7, color="#64b5f6", lw=1.2,
      label_text="")

# ════════════════════════════════════════════════════════════════════════════
# BOTTOM LEGEND
# ════════════════════════════════════════════════════════════════════════════
box(ax, 0.4, 0.3, 23.2, 4.8, "#1a1a2e", alpha=0.6, radius=0.3)
label(ax, 12.0, 4.8, "WORKFLOW SUMMARY", size=9, bold=True,
      color=C["highlight"])

flow = [
    "1. Jakub posts release notes in #release (Slack)",
    "2. Agent reads & parses free-form text → structured feature list",
    "3. Agent asks user to describe each feature interactively in terminal",
    "4. Agent scans all Zendesk articles → identifies articles to update + create",
    "5. User confirms article list, adds any missed articles",
    "6. Agent drafts all updates using user input + full knowledge base",
    "7. Agent presents plain text diff per article → user approves / requests changes",
    "8. User gives final approval → agent publishes to Zendesk",
    "9. Agent logs to changelog.md, flags screenshots, multi-language, staleness",
]
for i, step in enumerate(flow):
    col = i // 5
    row = i % 5
    x = 0.8 + col * 11.5
    y = 4.3 - row * 0.72
    label(ax, x, y, f"{'→' if i > 0 else '▶'} {step}", size=7.8,
          color=C["subtext"], ha="left")

# ════════════════════════════════════════════════════════════════════════════
# SAVE
# ════════════════════════════════════════════════════════════════════════════
output_path = "/Users/rakesh/Documents/pergdocsagent/architecture.png"
plt.tight_layout(pad=0)
plt.savefig(output_path, dpi=180, bbox_inches="tight",
            facecolor=fig.get_facecolor())
plt.close()
print(f"Saved: {output_path}")
