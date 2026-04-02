"""
Zendesk Help Center API tools for the Pergamon Docs Agent.
Handles: list, read, create, update, publish, rollback articles.
"""
from __future__ import annotations
import os
import json
import time
import requests
from pathlib import Path


def _auth() -> tuple[str, str]:
    subdomain = os.environ["ZENDESK_SUBDOMAIN"]
    email = os.environ["ZENDESK_EMAIL"]
    token = os.environ["ZENDESK_API_TOKEN"]
    return f"https://{subdomain}.zendesk.com", (f"{email}/token", token)


def list_zendesk_articles() -> str:
    """Return a JSON list of all articles: id, title, section_id, updated_at."""
    base, auth = _auth()
    articles = []
    url = f"{base}/api/v2/help_center/en-us/articles.json?per_page=100"
    while url:
        r = requests.get(url, auth=auth)
        r.raise_for_status()
        data = r.json()
        for a in data["articles"]:
            articles.append({
                "id": a["id"],
                "title": a["title"],
                "section_id": a["section_id"],
                "updated_at": a["updated_at"],
                "draft": a.get("draft", False),
                "html_url": a.get("html_url", ""),
            })
        url = data.get("next_page")
    return json.dumps(articles, indent=2)


def get_zendesk_article(article_id: int) -> str:
    """Fetch full article: title, body HTML, section_id, updated_at."""
    base, auth = _auth()
    r = requests.get(
        f"{base}/api/v2/help_center/en-us/articles/{article_id}.json",
        auth=auth,
    )
    if r.status_code == 404:
        return json.dumps({
            "error": "not_found",
            "article_id": article_id,
            "message": (
                f"Article {article_id} not found. This ID may be a section ID, not an article ID. "
                "Use get_sections to look up section IDs, or list_zendesk_articles to find valid article IDs."
            ),
        }, indent=2)
    r.raise_for_status()
    a = r.json()["article"]
    return json.dumps({
        "id": a["id"],
        "title": a["title"],
        "body": a["body"],
        "section_id": a["section_id"],
        "updated_at": a["updated_at"],
        "draft": a.get("draft", False),
        "html_url": a.get("html_url", ""),
    }, indent=2)


def get_article_versions(article_id: int) -> str:
    """Fetch version history for rollback support."""
    base, auth = _auth()
    r = requests.get(
        f"{base}/api/v2/help_center/articles/{article_id}/translations.json",
        auth=auth,
    )
    r.raise_for_status()
    translations = r.json().get("translations", [])
    versions = [
        {
            "id": t["id"],
            "updated_at": t["updated_at"],
            "draft": t.get("draft", False),
        }
        for t in translations
    ]
    return json.dumps(versions, indent=2)


def create_zendesk_article(
    title: str,
    body: str,
    section_id: int,
    draft: bool = True,
) -> str:
    """Create a new article in the specified section. Returns article id and url."""
    base, auth = _auth()

    # Step 1 — create the article shell
    payload = {
        "article": {
            "title": title,
            "locale": "en-us",
            "draft": True,
            "permission_group_id": 11340166249359,  # Admins group
            "user_segment_id": None,  # Visible to everyone
        }
    }
    r = requests.post(
        f"{base}/api/v2/help_center/sections/{section_id}/articles.json",
        auth=auth,
        json=payload,
    )
    r.raise_for_status()
    a = r.json()["article"]
    article_id = a["id"]

    # Step 2 — update the translation with the body content
    translation_payload = {
        "translation": {
            "locale": "en-us",
            "title": title,
            "body": body,
            "draft": draft,
        }
    }
    r2 = requests.put(
        f"{base}/api/v2/help_center/articles/{article_id}/translations/en-us.json",
        auth=auth,
        json=translation_payload,
    )
    r2.raise_for_status()

    return json.dumps({
        "id": article_id,
        "title": a["title"],
        "html_url": a.get("html_url", ""),
        "draft": draft,
    }, indent=2)


def update_zendesk_article(article_id: int, title: str, body: str) -> str:
    """Update an existing article body and title. Saves as draft."""
    base, auth = _auth()
    payload = {
        "translation": {
            "title": title,
            "body": body,
            "draft": True,
        }
    }
    r = requests.put(
        f"{base}/api/v2/help_center/articles/{article_id}/translations/en-us.json",
        auth=auth,
        json=payload,
    )
    r.raise_for_status()
    t = r.json()["translation"]
    return json.dumps({
        "id": article_id,
        "title": t.get("title", ""),
        "updated_at": t.get("updated_at", ""),
        "draft": t.get("draft", True),
    }, indent=2)


def publish_zendesk_article(article_id: int) -> str:
    """Publish an article (set draft: false). Retries up to 3 times."""
    base, auth = _auth()
    payload = {"translation": {"draft": False}}
    for attempt in range(1, 4):
        try:
            r = requests.put(
                f"{base}/api/v2/help_center/articles/{article_id}/translations/en-us.json",
                auth=auth,
                json=payload,
            )
            r.raise_for_status()
            t = r.json()["translation"]
            return json.dumps({
                "id": article_id,
                "published": True,
                "html_url": t.get("html_url", ""),
                "updated_at": t.get("updated_at", ""),
            }, indent=2)
        except requests.HTTPError as e:
            if attempt == 3:
                # Save draft locally so no work is lost
                _save_local_draft(article_id, payload)
                return json.dumps({
                    "id": article_id,
                    "published": False,
                    "error": str(e),
                    "local_draft_saved": True,
                }, indent=2)
            time.sleep(2)
    return json.dumps({"id": article_id, "published": False}, indent=2)


def rollback_zendesk_article(article_id: int) -> str:
    """
    Fetch the previous translation version and restore it.
    Zendesk doesn't have a native rollback — we re-fetch the current live
    version details and flag for manual restore.
    """
    base, auth = _auth()
    # Fetch article to confirm it exists
    r = requests.get(
        f"{base}/api/v2/help_center/en-us/articles/{article_id}.json",
        auth=auth,
    )
    r.raise_for_status()
    a = r.json()["article"]
    return json.dumps({
        "id": article_id,
        "title": a["title"],
        "note": (
            "To rollback: fetch a saved draft from the /drafts/ directory "
            "or use Zendesk's Article Versions in the Guide editor. "
            "Zendesk API does not expose historical versions directly."
        ),
    }, indent=2)


def get_sections() -> str:
    """List all Zendesk sections with id and name."""
    base, auth = _auth()
    r = requests.get(
        f"{base}/api/v2/help_center/en-us/sections.json?per_page=100",
        auth=auth,
    )
    r.raise_for_status()
    sections = [
        {"id": s["id"], "name": s["name"], "category_id": s["category_id"]}
        for s in r.json().get("sections", [])
    ]
    return json.dumps(sections, indent=2)


def _save_local_draft(article_id: int, payload: dict) -> None:
    """Save a failed publish as a local draft file."""
    drafts_dir = Path(__file__).parent.parent / "drafts"
    drafts_dir.mkdir(exist_ok=True)
    filepath = drafts_dir / f"article_{article_id}_draft.json"
    with open(filepath, "w") as f:
        json.dump({"article_id": article_id, "payload": payload}, f, indent=2)
