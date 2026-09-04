from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_SOURCE_COMMIT = "ebb180cc6fdbea63ca4f5fac576c2ee726b5bc78"
DEFAULT_SOURCE_URL = (
    "https://github.com/ascherj/neetcode-250-guide/blob/"
    f"{DEFAULT_SOURCE_COMMIT}/neetcode_250_complete.json"
)


def _leetcode_slug(url: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    try:
        problem_index = parts.index("problems")
        slug = parts[problem_index + 1]
    except (ValueError, IndexError) as exc:
        raise ValueError(f"Invalid LeetCode problem URL: {url}") from exc
    if not slug:
        raise ValueError(f"LeetCode problem URL has no slug: {url}")
    return slug


def build_catalog(source_path: Path) -> dict[str, object]:
    source = json.loads(source_path.read_text(encoding="utf-8"))
    problems = source.get("problems") if isinstance(source, dict) else None
    if not isinstance(problems, list) or not problems:
        raise ValueError("Source catalog does not contain a non-empty problems list.")

    aliases: dict[str, str] = {}
    for problem in problems:
        if not isinstance(problem, dict):
            raise ValueError("Source catalog contains a malformed problem.")
        neetcode_slug = problem.get("slug")
        leetcode_url = problem.get("leetcode_url")
        if not isinstance(neetcode_slug, str) or not isinstance(leetcode_url, str):
            raise ValueError("Source problem is missing slug or leetcode_url.")
        leetcode_slug = _leetcode_slug(leetcode_url)
        if neetcode_slug == leetcode_slug:
            continue
        existing = aliases.get(neetcode_slug)
        if existing is not None and existing != leetcode_slug:
            raise ValueError(f"Conflicting mapping for {neetcode_slug}.")
        aliases[neetcode_slug] = leetcode_slug

    return {
        "metadata": {
            "coverage": "NeetCode 250",
            "source": DEFAULT_SOURCE_URL,
            "source_commit": DEFAULT_SOURCE_COMMIT,
            "validated_target_count": len(aliases),
        },
        "aliases": dict(sorted(aliases.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the checked-in NeetCode-to-LeetCode slug catalog."
    )
    parser.add_argument("source", type=Path, help="Downloaded NeetCode 250 JSON file")
    parser.add_argument("output", type=Path, help="Catalog path to overwrite")
    args = parser.parse_args()
    catalog = build_catalog(args.source)
    args.output.write_text(
        json.dumps(catalog, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
