"""Extract labeled dancer markers from vector Sway formation exports.

This is a layout-specific importer, not OCR. Positions retain the PDF's stage
orientation (backstage at the top) and stage dimensions, expressed in feet.
Offstage positions are retained and flagged rather than moved onto the stage.
"""
from __future__ import annotations

import math
import re

import pymupdf

from .repair import validate

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PAGES = 80


class PDFImportError(ValueError):
    """A document cannot be reliably interpreted as a Sway vector export."""


def _lines(page):
    return [
        ("".join(s["text"] for s in line["spans"]).strip(), pymupdf.Rect(line["bbox"]))
        for block in page.get_text("dict")["blocks"]
        for line in block.get("lines", [])
    ]


def _parse_page(page, page_number):
    lines = _lines(page)
    text = "\n".join(line for line, _ in lines)
    header = re.search(
        r"([\d.]+)\s*['′]\s*[x×]\s*([\d.]+)\s*['′]\s*stage\s*\|\s*(\d+)\s*performers",
        text, re.IGNORECASE,
    )
    label = next((line for line, _ in lines if re.fullmatch(r"F\d+", line)), None)
    if not header or not label:
        raise PDFImportError(f"Page {page_number}: expected a Sway formation label and stage/performer header. Scanned images and other PDF layouts are not supported.")
    width, height = float(header[1]), float(header[2])
    expected = int(header[3])
    if not all(math.isfinite(v) and v > 0 for v in (width, height)) or not 1 <= expected <= 100:
        raise PDFImportError(f"Page {page_number}: invalid stage dimensions or performer count.")
    drawings = page.get_drawings()
    if len(drawings) > 30000:
        raise PDFImportError(f"Page {page_number}: drawing complexity exceeds the import limit.")
    # Rounded stage borders are stroked outlines with straight segments. Match
    # their aspect ratio to the physical dimensions, not a fixed pixel box.
    borders = [d["rect"] for d in drawings
               if d["type"] == "s" and d["rect"].width > page.rect.width * .2
               and d["rect"].height > page.rect.height * .2
               and d["rect"].width < page.rect.width * .95
               and abs(d["rect"].width / d["rect"].height - width / height) < .025
               and any(item[0] in ("l", "re") for item in d["items"])]
    if not borders:
        raise PDFImportError(f"Page {page_number}: could not identify the stage boundary.")
    stage = max(borders, key=lambda r: r.width * r.height)
    circles = [d["rect"] for d in drawings
               if d["type"] == "fs" and d.get("fill") is not None
               and d.get("color") and all(channel >= .9 for channel in d["color"])
               and len(d["items"]) == 4 and all(item[0] == "c" for item in d["items"])
               and stage.width * .008 < d["rect"].width < stage.width * .08
               and abs(d["rect"].width - d["rect"].height) < .2]
    # A dancer's name is centered immediately above their current marker.
    # White outlines distinguish current dancers from blue transition ghosts.
    # Unlabeled ghosts and transition paths must not become extra dancers.
    # Entrances/exits may place several dancers at the exact same point. Sway
    # draws a marker and text for each one, even when those drawings overlap.
    # Group coincident markers so every distinct label is retained at that point.
    groups = []
    for marker in circles:
        group = next((g for g in groups if max(abs(a-b) for a,b in zip(g[0], marker)) < .01), None)
        if group is None:
            groups.append([marker])
        else:
            group.append(marker)
    dancers = []
    used_labels = set()
    for group in groups:
        marker = group[0]
        cx, cy, radius = (marker.x0 + marker.x1) / 2, (marker.y0 + marker.y1) / 2, marker.width / 2
        nearby = [(name, box) for name, box in lines
                  if name and any(c.isalpha() for c in name)
                  and abs((box.x0 + box.x1) / 2 - cx) <= radius * .8
                  and radius * .7 <= cy - box.y1 <= radius * 3.5]
        if not nearby:
            continue
        nearby.sort(key=lambda item: abs((item[1].x0 + item[1].x1) / 2 - cx) + abs(cy - item[1].y1 - radius * 1.5))
        if len(group) > 1 and len(nearby) != len(group):
            raise PDFImportError(f"Page {page_number}: overlapping dancer markers do not have matching distinct labels. Export with visible names.")
        for name, _ in nearby[:len(group)]:
            if name in used_labels:
                raise PDFImportError(f"Page {page_number}: ambiguous or duplicate dancer label {name!r}.")
            used_labels.add(name)
            dancers.append({"id": name, "x": round((cx - stage.x0) / stage.width * width, 4),
                            "y": round((cy - stage.y0) / stage.height * height, 4)})
    if len(dancers) != expected:
        raise PDFImportError(f"Page {page_number} ({label}): matched {len(dancers)} labeled dancer markers; expected {expected}. Export a 2D PDF with visible names.")
    hold = re.search(r"([\d.]+)s\s+hold", text)
    formation = {"name": label, "dancers": dancers, "source_page": page_number}
    if hold:
        formation["hold_seconds"] = float(hold[1])
    return {"width": width, "height": height, "units": "ft"}, formation


def import_sway_pdf(content: bytes) -> dict:
    if len(content) > MAX_PDF_BYTES:
        raise PDFImportError("PDF exceeds the 10 MB upload limit.")
    if not content.startswith(b"%PDF-"):
        raise PDFImportError("Upload a valid PDF exported from Sway.")
    try:
        document = pymupdf.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise PDFImportError("The PDF is damaged or unreadable. Export it again from Sway.") from exc
    with document:
        if document.needs_pass:
            raise PDFImportError("Password-protected PDFs are not supported.")
        if not 1 <= len(document) <= MAX_PAGES:
            raise PDFImportError(f"Upload a PDF with between 1 and {MAX_PAGES} pages.")
        routine = {"stage": None, "formations": []}
        for i, page in enumerate(document):
            stage, formation = _parse_page(page, i + 1)
            if routine["stage"] is not None and routine["stage"] != stage:
                raise PDFImportError(f"Page {i+1}: stage dimensions differ from the first page.")
            routine["stage"] = stage
            routine["formations"].append(formation)
    first_roster = {p["id"] for p in routine["formations"][0]["dancers"]}
    pages = []
    for formation in routine["formations"]:
        errors = validate({"stage": routine["stage"], "formations": [formation]})
        if {p["id"] for p in formation["dancers"]} != first_roster:
            errors.append("Dancer roster differs from the first page. Verify the names before importing.")
        pages.append({"page": formation["source_page"], "name": formation["name"],
                      "dancer_count": len(formation["dancers"]), "issues": errors,
                      "importable": not errors})
    return {"routine": routine, "pages": pages,
            "warnings": ["Positions were extracted from the PDF. Review each formation before confirming.",
                         "Stage coordinates are in feet; backstage is at the top. Left/right choreography is not inferred.",
                         "Pages with offstage dancers, spacing violations, or mismatched rosters cannot be loaded for repair. Exclude them in the preview."]}
