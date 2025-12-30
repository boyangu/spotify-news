# Spotify News - Artist Dataset Builder

This project starts with extracting favorite artists from a Rekordbox/Spotify XML export. The script produces a ranked dataset of artists based on track appearances, with optional weighting when a track comment contains `!`.

## Usage

```bash
./build_artist_dataset.py path/to/export.xml
```

By default this writes:

- `artist_dataset.csv`
- `artist_dataset.json`

Override the output paths:

```bash
./build_artist_dataset.py path/to/export.xml --output data/artists.csv --json-output data/artists.json
```

## Scoring logic

- Each track appearance counts as **1**.
- If the track comment includes `!`, that track counts as **5**.
- Artist names are collected from:
  - The track `Artist` field (splitting on common separators like commas, `&`, `feat`, etc.).
  - Remixers in the track `Name`, when remix terms like `remix`, `rework`, `edit`, or `mix` are present in brackets.

The output dataset includes `rank`, `artist`, and `score` columns.
