#!/usr/bin/env python3
"""Scan a Pokemon card image and extract structured info.

Uses Claude's vision API to read the card, then optionally looks it up in the
free Pokemon TCG API (https://pokemontcg.io) to verify the set and get pricing
from Cardmarket.

Usage:
    python scan_card.py path/to/card.jpg
    python scan_card.py card1.jpg card2.png card3.jpg
    python scan_card.py card.jpg --no-lookup
    python scan_card.py card.jpg --json
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
from pathlib import Path
from typing import Literal

import anthropic
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

MODEL = "claude-opus-4-6"
POKEMON_TCG_API = "https://api.pokemontcg.io/v2/cards"

Condition = Literal[
    "Mint",
    "Near Mint",
    "Excellent",
    "Good",
    "Light Played",
    "Played",
    "Poor",
    "Unknown",
]

Language = Literal[
    "English",
    "German",
    "French",
    "Spanish",
    "Italian",
    "Portuguese",
    "Japanese",
    "Korean",
    "Chinese",
    "Dutch",
    "Unknown",
]


class CardReading(BaseModel):
    """What Claude sees on the card."""

    card_name: str = Field(description="The Pokemon's name as printed on the card.")
    set_name: str = Field(
        description=(
            "The set/expansion name. Look at the small symbol in the bottom-right "
            "corner of the art, or the set code near the card number. Examples: "
            "'Base Set', 'Scarlet & Violet - Paldea Evolved', 'Sword & Shield - Evolving Skies'. "
            "Use 'Unknown' if you cannot identify it."
        )
    )
    card_number: str = Field(
        description=(
            "The card number, usually printed at the bottom as 'X/Y' (e.g. '4/102') "
            "or just a number for newer sets (e.g. '025/193'). Include the full string."
        )
    )
    language: Language = Field(
        description="The language the card is printed in, based on the text on the card."
    )
    condition: Condition = Field(
        description=(
            "Best-effort estimate of the card's condition from the photo. "
            "Look for: edge whitening, corner wear, scratches on the holo/surface, "
            "bends, dents, print lines, dirt. Use standard TCG grading: "
            "Mint (flawless), Near Mint (minor wear), Excellent (light play wear), "
            "Good (noticeable wear), Light Played, Played, Poor. "
            "Use 'Unknown' if the photo quality prevents assessment."
        )
    )
    condition_notes: str = Field(
        default="",
        description="Brief notes on what you observed that informed the condition grade. Empty string if nothing notable.",
    )


SYSTEM_PROMPT = """You are a Pokemon trading card expert helping someone catalog their collection for resale.

Your job: look at the card photo and extract the requested fields accurately.

Guidance:
- Card name: just the Pokemon name (e.g. "Charizard", not "Charizard VMAX" unless VMAX/V/ex is part of the printed name).
- Set name: prefer the official English set name. The set symbol is usually bottom-right of the artwork.
- Card number: include the full printed form like "4/102" or "199/091".
- Condition is hard from a photo - be honest. If you can't tell, say "Unknown".
- Language: determine from the text on the card, not from the set name.
"""


def encode_image(path: Path) -> tuple[str, str]:
    """Return (base64_data, media_type) for an image file."""
    media_type, _ = mimetypes.guess_type(path)
    if media_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        raise ValueError(
            f"Unsupported image type: {media_type or 'unknown'} for {path}. "
            "Use JPG, PNG, WEBP, or GIF."
        )
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return data, media_type


def scan_with_claude(client: anthropic.Anthropic, image_path: Path) -> CardReading:
    """Ask Claude to read the card."""
    image_data, media_type = encode_image(image_path)

    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        thinking={"type": "adaptive"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Extract the card information from this Pokemon card photo.",
                    },
                ],
            }
        ],
        output_format=CardReading,
    )

    if response.parsed_output is None:
        raise RuntimeError(
            f"Claude could not extract structured card info from {image_path}. "
            f"Stop reason: {response.stop_reason}"
        )
    return response.parsed_output


def lookup_pokemon_tcg(reading: CardReading) -> dict | None:
    """Look up the card in the Pokemon TCG API.

    Returns the first matching card dict, or None if no match / lookup failed.
    """
    if reading.card_name in ("", "Unknown"):
        return None

    # Build a query. The number often looks like "4/102" - strip to the printed number.
    number_part = reading.card_number.split("/")[0].strip().lstrip("0") or "0"

    queries = []
    if reading.set_name not in ("", "Unknown"):
        # Try set name + number + name. Pokemon TCG API uses Lucene-style query.
        queries.append(
            f'name:"{reading.card_name}" number:"{number_part}" set.name:"{reading.set_name}"'
        )
    # Fallback: just name + number
    queries.append(f'name:"{reading.card_name}" number:"{number_part}"')

    for q in queries:
        try:
            resp = requests.get(
                POKEMON_TCG_API,
                params={"q": q, "pageSize": 1},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
            if data:
                return data[0]
        except requests.RequestException:
            continue
    return None


def format_text(reading: CardReading, match: dict | None) -> str:
    """Human-readable output."""
    lines = [
        f"Card Name:    {reading.card_name}",
        f"Set:          {reading.set_name}",
        f"Card Number:  {reading.card_number}",
        f"Language:     {reading.language}",
        f"Condition:    {reading.condition}",
    ]
    if reading.condition_notes:
        lines.append(f"  notes: {reading.condition_notes}")

    if match:
        lines.append("")
        lines.append("Verified via Pokemon TCG API:")
        lines.append(f"  Official set: {match.get('set', {}).get('name', '?')}")
        lines.append(f"  Official number: {match.get('number', '?')}")
        lines.append(f"  Rarity: {match.get('rarity', '?')}")
        cm = match.get("cardmarket", {})
        prices = cm.get("prices", {})
        if prices:
            lines.append("  Cardmarket prices (EUR):")
            for key in ("averageSellPrice", "lowPrice", "trendPrice"):
                if prices.get(key) is not None:
                    lines.append(f"    {key}: {prices[key]}")
            if cm.get("url"):
                lines.append(f"  Cardmarket URL: {cm['url']}")
    return "\n".join(lines)


def format_json(reading: CardReading, match: dict | None) -> str:
    out = reading.model_dump()
    if match:
        out["pokemon_tcg_match"] = {
            "id": match.get("id"),
            "set_name": match.get("set", {}).get("name"),
            "set_id": match.get("set", {}).get("id"),
            "number": match.get("number"),
            "rarity": match.get("rarity"),
            "images": match.get("images"),
            "cardmarket": match.get("cardmarket"),
        }
    return json.dumps(out, indent=2, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan Pokemon cards with Claude.")
    parser.add_argument("images", nargs="+", type=Path, help="One or more card image files.")
    parser.add_argument(
        "--no-lookup",
        action="store_true",
        help="Skip the Pokemon TCG API cross-reference.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of formatted text.",
    )
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print(
            "ERROR: ANTHROPIC_API_KEY is not set. Copy .env.example to .env "
            "and add your key from https://console.anthropic.com/",
            file=sys.stderr,
        )
        return 1

    client = anthropic.Anthropic()

    for i, image_path in enumerate(args.images):
        if not image_path.is_file():
            print(f"ERROR: {image_path} not found.", file=sys.stderr)
            continue

        if i > 0 and not args.json:
            print("\n" + "=" * 50 + "\n")

        if not args.json:
            print(f"Scanning: {image_path}")
            print("-" * 50)

        try:
            reading = scan_with_claude(client, image_path)
        except Exception as e:
            print(f"ERROR scanning {image_path}: {e}", file=sys.stderr)
            continue

        match = None if args.no_lookup else lookup_pokemon_tcg(reading)

        if args.json:
            print(format_json(reading, match))
        else:
            print(format_text(reading, match))

    return 0


if __name__ == "__main__":
    sys.exit(main())
