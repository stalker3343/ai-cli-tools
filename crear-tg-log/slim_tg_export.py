#!/usr/bin/env python3
"""
Slim Telegram chat export JSON: keep message text, author names, dates, ids, and links.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def flatten_text(text: Any, links_out: list[dict[str, str]]) -> str:
    """Normalize Telegram `text` (str or list of fragments) to a plain string; collect text_link URLs."""
    if text is None:
        return ""
    if isinstance(text, str):
        return text
    if isinstance(text, list):
        parts: list[str] = []
        for item in text:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                fragment = item.get("text")
                if fragment is None:
                    continue
                if not isinstance(fragment, str):
                    fragment = str(fragment)
                if item.get("type") == "text_link" and item.get("href"):
                    links_out.append({"text": fragment, "url": str(item["href"])})
                parts.append(fragment)
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(text)


# Keys copied from a raw message, in output order.
RAW_KEYS = (
    "id",
    "date",
    "from",
    "text",
)


def slim_message(raw: dict[str, Any]) -> dict[str, Any]:
    links: list[dict[str, str]] = []
    flat = flatten_text(raw.get("text"), links)

    out: dict[str, Any] = {}
    for key in RAW_KEYS:
        if key == "text":
            out["text"] = flat
            continue
        if key not in raw:
            continue
        out[key] = raw[key]

    if links:
        out["links"] = links
    return out


def slim_export(
    data: dict[str, Any],
    *,
    drop_empty: bool,
) -> dict[str, Any]:
    messages_in = data.get("messages") or []
    messages_out: list[dict[str, Any]] = []

    for raw in messages_in:
        if not isinstance(raw, dict):
            continue
        if raw.get("type") != "message":
            continue
        slim = slim_message(raw)
        if drop_empty and not (slim.get("text") or "").strip():
            continue
        messages_out.append(slim)

    result: dict[str, Any] = {
        "name": data.get("name"),
        "id": data.get("id"),
        "messages": messages_out,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Slim Telegram JSON export for LLM / analysis.")
    parser.add_argument(
        "input",
        type=Path,
        help="Path to result.json",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output path (default: <input_dir>/result.slim.json)",
    )
    parser.add_argument(
        "--drop-empty",
        action="store_true",
        default=True,
        help="Drop messages with no text after normalization (can break reply chains to empty ids).",
    )
    parser.add_argument(
        "--keep-empty",
        action="store_false",
        dest="drop_empty",
        help="Keep messages with no text after normalization.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indent (default: 2; use 0 for compact).",
    )
    args = parser.parse_args()

    inp = args.input.expanduser().resolve()
    out = args.output
    if out is None:
        out = inp.parent / "result.slim.json"
    else:
        out = out.expanduser().resolve()

    with inp.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise SystemExit("Top-level JSON must be an object.")

    slim = slim_export(
        data,
        drop_empty=args.drop_empty,
    )

    indent = None if args.indent == 0 else args.indent
    with out.open("w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False, indent=indent)
        f.write("\n")

    print(f"Wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
