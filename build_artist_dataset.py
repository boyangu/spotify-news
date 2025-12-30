#!/usr/bin/env python3
"""Build an artist ranking dataset from a Rekordbox/Spotify XML export."""

from __future__ import annotations

import argparse
import csv
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

REMIX_KEYWORDS = (
    "remix",
    "rework",
    "edit",
    "mix",
    "version",
)

SPLIT_PATTERN = re.compile(
    r"\s*(?:,|;|/|\\|\s{2,}|\s+&\s+|\s+and\s+|\s+feat\.?\s+|\s+ft\.?\s+|\s+x\s+|\s+vs\.?\s+)\s*",
    flags=re.IGNORECASE,
)

REMIX_SEGMENT_PATTERN = re.compile(r"[\[(](.*?)[\])]", flags=re.IGNORECASE)


@dataclass(frozen=True)
class TrackInfo:
    name: str
    artists: List[str]
    comment: str


def normalize_artist(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip())


def split_artists(raw: str) -> List[str]:
    raw = raw.strip()
    if not raw:
        return []
    parts = [normalize_artist(part) for part in SPLIT_PATTERN.split(raw) if part.strip()]
    return [part for part in parts if part]


def extract_remix_artists(track_name: str) -> List[str]:
    remix_artists: List[str] = []
    for segment in REMIX_SEGMENT_PATTERN.findall(track_name or ""):
        lower_segment = segment.lower()
        if any(keyword in lower_segment for keyword in REMIX_KEYWORDS):
            cleaned = segment
            for keyword in REMIX_KEYWORDS:
                cleaned = re.sub(rf"\b{re.escape(keyword)}\b", "", cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.replace("-", " ")
            remix_artists.extend(split_artists(cleaned))
    return remix_artists


def get_attribute(attributes: dict[str, str], *names: str) -> str:
    for name in names:
        for key, value in attributes.items():
            if key.lower() == name.lower():
                return value
    return ""


def parse_tracks(xml_path: Path) -> Iterable[TrackInfo]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    for track in root.iter():
        if track.tag.lower() != "track":
            continue
        name = get_attribute(track.attrib, "Name", "TrackName")
        artist_field = get_attribute(track.attrib, "Artist", "TrackArtist")
        comment = get_attribute(track.attrib, "Comment", "Comments")

        artists = split_artists(artist_field)
        remix_artists = extract_remix_artists(name)
        all_artists = [normalize_artist(artist) for artist in artists + remix_artists if artist]
        if not all_artists:
            continue
        yield TrackInfo(name=name, artists=all_artists, comment=comment)


def calculate_scores(tracks: Iterable[TrackInfo]) -> dict[str, int]:
    scores: dict[str, int] = {}
    for track in tracks:
        weight = 5 if "!" in (track.comment or "") else 1
        for artist in track.artists:
            if not artist:
                continue
            scores[artist] = scores.get(artist, 0) + weight
    return scores


def write_dataset(scores: dict[str, int], output_path: Path) -> None:
    sorted_artists = sorted(scores.items(), key=lambda item: (-item[1], item[0].lower()))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rank", "artist", "score"])
        for rank, (artist, score) in enumerate(sorted_artists, start=1):
            writer.writerow([rank, artist, score])


def write_json(scores: dict[str, int], output_path: Path) -> None:
    sorted_artists = sorted(scores.items(), key=lambda item: (-item[1], item[0].lower()))
    payload = [
        {"rank": rank, "artist": artist, "score": score}
        for rank, (artist, score) in enumerate(sorted_artists, start=1)
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an artist ranking dataset from an XML export.")
    parser.add_argument("xml_path", type=Path, help="Path to the Rekordbox/Spotify XML export.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artist_dataset.csv"),
        help="Path to write the CSV dataset (default: artist_dataset.csv).",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("artist_dataset.json"),
        help="Optional JSON output path (default: artist_dataset.json).",
    )
    args = parser.parse_args()

    tracks = list(parse_tracks(args.xml_path))
    scores = calculate_scores(tracks)

    write_dataset(scores, args.output)
    if args.json_output:
        write_json(scores, args.json_output)


if __name__ == "__main__":
    main()
