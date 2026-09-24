from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from uuid import uuid4

from aiohttp import ClientSession

GITHUB_API = "https://api.github.com"


class GitHubTransactionError(RuntimeError):
    pass


class GitHubTransactionWriter:
    def __init__(
        self,
        session: ClientSession,
        token: str | None,
        repository: str,
        branch: str,
        profile_id: str,
    ) -> None:
        self._session = session
        self._token = (token or "").strip()
        self.repository = repository.strip()
        self.branch = branch.strip() or "main"
        self.profile_id = profile_id.strip()

    @property
    def configured(self) -> bool:
        return bool(self._token and self.repository and self.profile_id)

    async def submit_later(
        self,
        *,
        media: dict,
        canonical_title: str,
        taxonomy: list[dict],
        benchmark: dict,
    ) -> dict:
        if not self.configured:
            raise GitHubTransactionError(
                "GitHub queue není nakonfigurovaná. Otevři Configure u Anime Benchmark a vlož GitHub token."
            )

        anilist_id = media.get("id")
        if not isinstance(anilist_id, int) or anilist_id <= 0:
            raise GitHubTransactionError("AniList ID chybí nebo je neplatné.")

        now = datetime.now(timezone.utc)
        suffix = uuid4().hex[:8]
        transaction_id = (
            f"tx_anilist_later_{anilist_id}_{now.strftime('%Y%m%d%H%M%S')}_{suffix}"
        )
        transaction = {
            "schema_version": "tracker-transaction-v1",
            "transaction_id": transaction_id,
            "profile_id": self.profile_id,
            "description": f"Anime Benchmark Later import: {canonical_title}",
            "operations": [
                {
                    "op": "import_anilist_later",
                    "queued_at": now.isoformat(),
                    "anilist": {
                        "id": anilist_id,
                        "canonical_title": canonical_title,
                        "english_title": (media.get("title") or {}).get("english"),
                        "romaji_title": (media.get("title") or {}).get("romaji"),
                        "native_title": (media.get("title") or {}).get("native"),
                        "site_url": media.get("siteUrl"),
                        "format": media.get("format"),
                        "status": media.get("status"),
                        "episodes": media.get("episodes"),
                        "duration": media.get("duration"),
                        "country": media.get("countryOfOrigin"),
                        "source": media.get("source"),
                        "year": (media.get("startDate") or {}).get("year"),
                    },
                    "taxonomy": taxonomy,
                    "benchmark": benchmark,
                }
            ],
        }

        path = (
            f"transactions/production/{now.year:04d}/{now.month:02d}/"
            f"{transaction_id}.json"
        )
        payload = {
            "message": f"Queue Anime Benchmark Later import for AniList {anilist_id}",
            "content": base64.b64encode(
                (json.dumps(transaction, indent=2, ensure_ascii=False) + "\n").encode(
                    "utf-8"
                )
            ).decode("ascii"),
            "branch": self.branch,
        }

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        url = f"{GITHUB_API}/repos/{self.repository}/contents/{path}"

        async with self._session.put(
            url,
            headers=headers,
            json=payload,
            timeout=20,
        ) as response:
            body = await response.json(content_type=None)
            if response.status not in {200, 201}:
                message = body.get("message") if isinstance(body, dict) else str(body)
                raise GitHubTransactionError(
                    f"GitHub transaction write failed ({response.status}): {message}"
                )

        content = (body or {}).get("content") or {}
        commit = (body or {}).get("commit") or {}
        return {
            "transaction_id": transaction_id,
            "path": path,
            "commit_sha": commit.get("sha"),
            "html_url": content.get("html_url"),
        }
