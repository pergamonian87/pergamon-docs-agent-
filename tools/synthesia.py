"""
Synthesia integration for the Pergamon Docs Agent.
Calls the Synthesia Video Agent to create release highlight videos.
Returns the video URL and thumbnail for embedding in release notes.
"""
from __future__ import annotations
import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def create_release_video(
    version: str,
    features: list[dict],
    release_summary: str,
) -> str:
    """
    Call the Synthesia Video Agent to create a release highlights video.
    Returns video URL and thumbnail URL for embedding in release notes.

    Args:
        version: Release version string e.g. "3.8.0"
        features: List of {"name": str, "description": str} dicts
        release_summary: 2-3 sentence summary of the release
    """
    synthesia_key = os.environ.get("SYNTHESIA_API_KEY", "").strip()
    if not synthesia_key:
        return json.dumps({
            "status": "no_api_key",
            "message": "Synthesia API key not found in .env. Insert [VIDEO NEEDED] placeholder.",
        })

    # Build scenes for the video
    feature_lines = " ".join(
        f"{f['name']}: {f['description']}" for f in features
    )
    scenes = [
        {
            "title": f"Pergamon {version} — What's New",
            "scriptText": f"{release_summary}",
        },
    ]
    for f in features:
        scenes.append({
            "title": f["name"],
            "scriptText": f"{f['name']} — {f['description']}",
        })
    scenes.append({
        "title": "Summary",
        "scriptText": f"That's what's new in Pergamon {version}. Update your platform to get started.",
    })

    headers = {
        "Authorization": synthesia_key,
        "Content-Type": "application/json",
    }
    payload = {
        "title": f"Pergamon {version} Release Highlights",
        "description": release_summary,
        "visibility": "private",
        "templateId": "6a82e53f-5f15-48d1-972d-423b81d901f9",
        "input": [
            {
                "avatarId": "anna_costume1_cameraA",
                "scriptText": scene["scriptText"],
                "title": scene["title"],
            }
            for scene in scenes
        ],
    }

    try:
        r = requests.post(
            "https://api.synthesia.io/v2/videos",
            headers=headers,
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        video_id = data.get("id", "")

        return json.dumps({
            "status": "ok",
            "video_id": video_id,
            "video_url": f"https://share.synthesia.io/{video_id}",
            "thumbnail_url": f"https://api.synthesia.io/{video_id}/thumbnail.gif",
            "embed_html": (
                f'<p><a href="https://share.synthesia.io/{video_id}">'
                f'Pergamon {version} Release Notes - Watch Video</a></p>'
                f'<p><a href="https://share.synthesia.io/{video_id}">'
                f'<img src="https://api.synthesia.io/{video_id}/thumbnail.gif" '
                f'width="512" height="288"></a></p>'
            ),
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Synthesia API error: {e}. Insert [VIDEO NEEDED] placeholder.",
        })
