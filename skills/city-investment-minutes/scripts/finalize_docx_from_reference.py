#!/usr/bin/env python3
"""Finalize a generated docx so its package structure matches the reference docx.

Rule:
- Keep generated `word/document.xml` (content body).
- By default, keep reference `docProps/core.xml` (metadata, including timestamps).
- Optionally keep generated `docProps/core.xml` only when explicitly requested.
- All other parts are taken from the reference file.

This makes the output structurally identical to the reference template while
preserving the generated meeting content.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}

REQUIRED_IDENTICAL_FILES = [
    "word/styles.xml",
    "word/numbering.xml",
    "word/settings.xml",
    "word/fontTable.xml",
    "word/theme/theme1.xml",
    "word/webSettings.xml",
    "word/_rels/document.xml.rels",
    "word/footnotes.xml",
    "word/endnotes.xml",
    "[Content_Types].xml",
]


def _read_zip_bytes(path: str) -> dict[str, bytes]:
    with zipfile.ZipFile(path, "r") as zf:
        return {name: zf.read(name) for name in zf.namelist()}


def _extract_num_ids_from_document_xml(document_xml: bytes) -> set[str]:
    root = ET.fromstring(document_xml)
    used: set[str] = set()
    for p in root.findall(".//w:body/w:p", NS):
        p_pr = p.find("w:pPr", NS)
        if p_pr is None:
            continue
        num_pr = p_pr.find("w:numPr", NS)
        if num_pr is None:
            continue
        num_id = num_pr.find("w:numId", NS)
        if num_id is None:
            continue
        val = num_id.attrib.get(f"{{{W_NS}}}val")
        if val:
            used.add(val)
    return used


def _extract_num_ids_from_numbering_xml(numbering_xml: bytes) -> set[str]:
    root = ET.fromstring(numbering_xml)
    ids = set()
    for num in root.findall("w:num", NS):
        val = num.attrib.get(f"{{{W_NS}}}numId")
        if val:
            ids.add(val)
    return ids


def _validate_numbering_compatibility(
    generated_document_xml: bytes, reference_numbering_xml: bytes
) -> None:
    used = _extract_num_ids_from_document_xml(generated_document_xml)
    available = _extract_num_ids_from_numbering_xml(reference_numbering_xml)
    missing = sorted(used - available, key=lambda x: int(x) if x.isdigit() else x)
    if missing:
        raise ValueError(
            "Generated document.xml uses numId(s) not present in reference numbering.xml: "
            + ", ".join(missing)
        )


def _finalize(
    reference_path: str,
    generated_path: str,
    output_path: str,
    keep_generated_core: bool,
) -> None:
    reference_parts = _read_zip_bytes(reference_path)
    generated_parts = _read_zip_bytes(generated_path)

    if "word/document.xml" not in generated_parts:
        raise ValueError("Generated docx is missing word/document.xml")
    if "word/numbering.xml" not in reference_parts:
        raise ValueError("Reference docx is missing word/numbering.xml")

    _validate_numbering_compatibility(
        generated_document_xml=generated_parts["word/document.xml"],
        reference_numbering_xml=reference_parts["word/numbering.xml"],
    )

    # Build output strictly from reference package entries.
    with zipfile.ZipFile(reference_path, "r") as ref_zip:
        ref_infos = ref_zip.infolist()

    with zipfile.ZipFile(output_path, "w") as out_zip:
        for info in ref_infos:
            name = info.filename
            if name == "word/document.xml":
                data = generated_parts["word/document.xml"]
            elif (
                keep_generated_core
                and name == "docProps/core.xml"
                and name in generated_parts
            ):
                data = generated_parts[name]
            else:
                data = reference_parts[name]

            # Preserve the original entry metadata as much as possible.
            new_info = zipfile.ZipInfo(filename=name, date_time=info.date_time)
            new_info.compress_type = info.compress_type
            new_info.external_attr = info.external_attr
            new_info.flag_bits = info.flag_bits
            out_zip.writestr(new_info, data)

    # Post-check: required files must be byte-identical to reference.
    out_parts = _read_zip_bytes(output_path)
    for rel_path in REQUIRED_IDENTICAL_FILES:
        if rel_path not in out_parts:
            raise ValueError(f"Output docx missing required file: {rel_path}")
        if out_parts[rel_path] != reference_parts[rel_path]:
            raise ValueError(f"Output differs from reference in: {rel_path}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze generated docx structure to the reference template."
    )
    parser.add_argument("--reference", required=True, help="Reference .docx path")
    parser.add_argument("--generated", required=True, help="Generated .docx path")
    parser.add_argument("--output", required=True, help="Final .docx output path")
    parser.add_argument(
        "--keep-generated-core",
        action="store_true",
        help="Keep generated docProps/core.xml instead of reference metadata",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    keep_generated_core = args.keep_generated_core
    try:
        _finalize(
            reference_path=args.reference,
            generated_path=args.generated,
            output_path=args.output,
            keep_generated_core=keep_generated_core,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"[OK] finalized: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
