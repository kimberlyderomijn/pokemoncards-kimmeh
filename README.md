# pokemoncards-kimmeh

CLI tool that reads a Pokemon card photo and fills in the fields you need to list it for sale:

- Card Name
- Set
- Card Number
- Language
- Condition

It uses Claude's vision API to read the card, then cross-references the free
[Pokemon TCG API](https://pokemontcg.io) to verify the set/number and pull
current Cardmarket pricing.

## Why not scrape cardmarket.com?

Cardmarket's terms of service forbid scraping, and the HTML is fragile. The
Pokemon TCG API includes a `cardmarket` block on every card with current
`averageSellPrice`, `lowPrice`, and `trendPrice` in EUR - same data, no scraping.

## Setup

```bash
# 1. Install dependencies (use a venv if you like)
pip install -r requirements.txt

# 2. Add your Anthropic API key
cp .env.example .env
# Edit .env and paste your key from https://console.anthropic.com/
```

## Usage

```bash
# Scan one card
python scan_card.py path/to/card.jpg

# Scan several at once
python scan_card.py card1.jpg card2.png card3.jpg

# Skip the Pokemon TCG API lookup (just use Claude's reading)
python scan_card.py card.jpg --no-lookup

# Output JSON (handy if you want to pipe into a spreadsheet later)
python scan_card.py card.jpg --json
```

### Example output

```
Scanning: charizard.jpg
--------------------------------------------------
Card Name:    Charizard
Set:          Base Set
Card Number:  4/102
Language:     English
Condition:    Excellent
  notes: Light edge whitening on bottom-left corner, surface clean.

Verified via Pokemon TCG API:
  Official set: Base
  Official number: 4
  Rarity: Rare Holo
  Cardmarket prices (EUR):
    averageSellPrice: 412.5
    lowPrice: 89.99
    trendPrice: 389.0
  Cardmarket URL: https://www.cardmarket.com/en/Pokemon/...
```

## Notes

- **Condition is a best-effort estimate.** Grading from a photo is approximate - use
  it as a starting point, not a replacement for in-hand inspection.
- **Photos:** JPG, PNG, WEBP, and GIF are supported. A clean, well-lit shot of the
  front of the card works best.
- **Model:** uses `claude-opus-4-6` with adaptive thinking for accurate reads.
