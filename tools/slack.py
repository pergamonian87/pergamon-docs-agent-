"""
Slack API tools for the Pergamon Docs Agent.
Fetches release threads from #release channel.
Falls back to manual paste if Slack credentials are not configured.
"""
from __future__ import annotations
import os
import json
import requests
from datetime import datetime
from pathlib import Path


def _state_path() -> Path:
    return Path(__file__).parent.parent / "drafts" / "slack_state.json"


def _load_slack_state() -> dict:
    p = _state_path()
    return json.loads(p.read_text()) if p.exists() else {}


def save_slack_thread_state(version: str, last_ts: str, message_count: int) -> None:
    """Persist the last-seen thread state for a version to enable refresh runs."""
    p = _state_path()
    p.parent.mkdir(exist_ok=True)
    state = _load_slack_state()
    state[version] = {
        "last_parsed_at": datetime.now().isoformat(),
        "last_message_ts": last_ts,
        "message_count": message_count,
    }
    p.write_text(json.dumps(state, indent=2))


def fetch_slack_release_thread(version: str = None) -> str:
    """
    Fetch a release thread from the Slack #release channel.
    If version is provided, finds that specific version's thread.
    Otherwise fetches the most recent release thread.
    Falls back to manual paste if Slack credentials are not configured.
    """
    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    channel_id = os.environ.get("SLACK_RELEASE_CHANNEL_ID", "").strip()

    if not token or not channel_id:
        return json.dumps({
            "status": "no_slack_credentials",
            "message": (
                "Slack credentials are not configured. "
                "Please paste the release notes from Slack directly into the terminal "
                "when prompted, and I will parse them from there."
            ),
        })

    headers = {"Authorization": f"Bearer {token}"}

    # Scan more messages when targeting a specific version — it may be further back
    limit = 50 if version else 20
    r = requests.get(
        "https://slack.com/api/conversations.history",
        headers=headers,
        params={"channel": channel_id, "limit": limit},
    )
    r.raise_for_status()
    data = r.json()

    if not data.get("ok"):
        return json.dumps({
            "status": "error",
            "error": data.get("error", "Unknown Slack API error"),
        })

    messages = data.get("messages", [])

    import re
    # Matches: semantic versions (3.9.0), date versions (15.06.2026), or "release" keyword
    _RELEASE_PATTERN = re.compile(r"\d+\.\d+[\.\d]*|\brelease\b", re.IGNORECASE)

    release_msg = None
    for msg in messages:
        text = msg.get("text", "")
        if version:
            # Accept any substring match — handles "3.9.0", "15.06.2026", "Release June 2026", etc.
            if version.lower() in text.lower():
                release_msg = msg
                break
        else:
            if _RELEASE_PATTERN.search(text):
                release_msg = msg
                break

    if not release_msg:
        not_found = (
            f"No release thread found matching '{version}' in the last {limit} messages."
            if version else
            f"No release thread found in the last {limit} messages."
        )
        return json.dumps({
            "status": "no_release_found",
            "message": not_found,
        })

    # Fetch thread replies
    thread_ts = release_msg.get("thread_ts") or release_msg.get("ts")
    replies_data = requests.get(
        "https://slack.com/api/conversations.replies",
        headers=headers,
        params={"channel": channel_id, "ts": thread_ts},
    ).json()

    thread_messages = []
    for msg in replies_data.get("messages", []):
        thread_messages.append({
            "user": msg.get("user", "unknown"),
            "text": msg.get("text", ""),
            "ts": msg.get("ts", ""),
        })

    return json.dumps({
        "status": "ok",
        "release_message": release_msg.get("text", ""),
        "thread": thread_messages,
    }, indent=2)


def fetch_slack_thread_updates(version: str) -> str:
    """
    Fetch only new comments added to a version's Slack thread since the last parse.
    Requires a prior run with --version to have established a baseline state.
    """
    state = _load_slack_state()
    version_state = state.get(version)

    if not version_state:
        return json.dumps({
            "status": "no_prior_state",
            "message": (
                f"No prior parse state found for version {version}. "
                "Run the full release workflow with --version first to establish a baseline."
            ),
        })

    since_ts = version_state["last_message_ts"]
    last_parsed_at = version_state["last_parsed_at"]

    result = fetch_slack_release_thread(version=version)
    data = json.loads(result)

    if data.get("status") != "ok":
        return result

    all_messages = data.get("thread", [])
    new_messages = [m for m in all_messages if float(m["ts"]) > float(since_ts)]

    if not new_messages:
        return json.dumps({
            "status": "no_updates",
            "version": version,
            "last_parsed_at": last_parsed_at,
            "message": f"No new comments on the {version} thread since {last_parsed_at}.",
        })

    # Advance the state to the latest message seen
    save_slack_thread_state(version, all_messages[-1]["ts"], len(all_messages))

    return json.dumps({
        "status": "ok",
        "version": version,
        "last_parsed_at": last_parsed_at,
        "new_message_count": len(new_messages),
        "release_message": data.get("release_message", ""),
        "new_messages": new_messages,
    }, indent=2)
