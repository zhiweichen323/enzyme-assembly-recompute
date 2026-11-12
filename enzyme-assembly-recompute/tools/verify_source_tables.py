#!/usr/bin/env python3
"""Optionally verify CSV tables against a locally held original DOCX."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=BASE / 'reference' / 'original_supplementary.docx',
                        help='Locally held source supplement; it is not bundled in this repository.')
    args = parser.parse_args()
    source = args.source.expanduser()
    if not source.is_file():
        parser.error('Source DOCX not found. Main analysis needs only CSV inputs. For optional source verification, pass --source /path/to/the/original.docx.')
    try:
        from docx import Document
    except ImportError:
        parser.error('This optional tool needs python-docx: install requirements-extract.txt with the same Python interpreter.')
    manifest = json.loads((BASE / 'reference' / 'data_provenance.json').read_text(encoding='utf-8'))
    if hashlib.sha256(source.read_bytes()).hexdigest() != manifest['source_sha256']:
        raise ValueError('Source DOCX SHA256 differs from the recorded source version.')
    tables = Document(source).tables
    names = ('table_s1_annotations.csv', 'table_s2_pathways_as_reported.csv', 'table_s3_features_as_reported.csv')
    for i, name in enumerate(names):
        expected = [[cell.text.strip() for cell in row.cells] for row in tables[i].rows][1:]
        with (BASE / 'data' / name).open(encoding='utf-8-sig', newline='') as stream:
            actual = list(csv.reader(stream))[1:]
        if actual != expected:
            raise ValueError(f'Table cell mismatch: {name}')
        print(f'Verified source table {i + 1}: {len(expected)} rows.')
    for name, expected_hash in manifest['input_sha256'].items():
        actual_hash = hashlib.sha256((BASE / 'data' / name).read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(f'Input file changed: {name}')
    print('All supplied table cells and CSV hashes match. This verifies extraction, not the biological correctness of source annotations.')
    return 0


if __name__ == '__main__':
    main()
