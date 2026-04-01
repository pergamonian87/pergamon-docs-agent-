"""
Slack API tools for the Pergamon Docs Agent.
Fetches release threads from #release channel.
Falls back to manual paste if Slack credentials are not configured.
"""
from __future__ import annotations
import os
import json
import requests


def fetch_slack_release_thread() -> str:
    """
    Fetch the most recent release thread from the Slack #release channel.
    If Slack credentials are not configured, returns a prompt for manual input.
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

    # Get recent messages from the channel
    r = requests.get(
        "https://slack.com/api/conversations.history",
        headers=headers,
        params={"channel": channel_id, "limit": 20},
    )
    r.raise_for_status()
    data = r.json()

    if not data.get("ok"):
        return json.dumps({
            "status": "error",
            "error": data.get("error", "Unknown Slack API error"),
        })

    messages = data.get("messages", [])

    # Find the most recent message that looks like a release announcement
    # (contains a version number pattern like 3.8.0)
    import re
    release_msg = None
    for msg in messages:
        text = msg.get("text", "")
        if re.search(r"\d+\.\d+\.\d+", text):
            release_msg = msg
            break

    if not release_msg:
        return json.dumps({
            "status": "no_release_found",
            "message": "No release thread found in the last 20 messages.",
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
