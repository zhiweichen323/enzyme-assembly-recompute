#!/usr/bin/env python3
"""Validate repository documentation, configuration examples, and input provenance."""
from __future__ import annotations
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from run_analysis import validate_config

EXCLUDED = {'.git', '.venv', 'venv', '__pycache__', 'results', 'results_reference'}


def repository_files():
    for path in BASE.rglob('*'):
        if path.is_file() and not set(path.relative_to(BASE).parts) & EXCLUDED:
            yield path


def main():
    required = ['README.md', 'README.en.md', 'CONTRIBUTING.md', 'REPRODUCIBILITY.md',
                'CITATION.md', 'LICENSE_NOTICE.md', '.gitignore', '.gitattributes',
                '.github/workflows/tests.yml', 'configs/schema.json']
    for name in required:
        if not (BASE / name).is_file():
            raise ValueError(f'Missing repository file: {name}')
    forbidden = re.compile(r'chatgpt\.com/library|libfile_|/workspace/scratch/|/home/chenzw|sandbox:|YOUR_USERNAME|YOUR_GITHUB_EMAIL|老师|截图|本整理版|给你')
    links = 0
    markdown_files = 0
    for path in repository_files():
        if path.suffix == '.json':
            text = path.read_text(encoding='utf-8-sig')
            json.loads(text)
            if forbidden.search(text):
                raise ValueError(f'Account-specific or delivery-only text in {path.relative_to(BASE)}')
        if path.suffix != '.md':
            continue
        markdown_files += 1
        text = path.read_text(encoding='utf-8')
        if forbidden.search(text):
            raise ValueError(f'Account-specific or delivery-only text in {path.relative_to(BASE)}')
        if len(re.findall(r'^```', text, re.M)) % 2:
            raise ValueError(f'Unbalanced fenced code in {path.relative_to(BASE)}')
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', text):
            target = target.strip().strip('<>')
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith('#'):
                continue
            local = unquote(parsed.path)
            candidate = BASE / local.lstrip('/') if local.startswith('/') else path.parent / local
            if not candidate.exists():
                raise ValueError(f'Broken local link: {path.relative_to(BASE)} -> {target}')
            links += 1
    for name in ('quick', 'main'):
        config = json.loads((BASE / 'configs' / f'{name}.json').read_text())
        validate_config(config)
        if not (BASE / 'configs' / config['$schema']).is_file():
            raise ValueError(f'Missing schema target for {name}.json')
    provenance = json.loads((BASE / 'reference/data_provenance.json').read_text())
    for name, expected in provenance['input_sha256'].items():
        actual = hashlib.sha256((BASE / 'data' / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'Input checksum mismatch: {name}')
    print(json.dumps({'status': 'passed', 'markdown_files': markdown_files,
                      'resolved_local_links': links, 'configurations': 2,
                      'input_checksums': len(provenance['input_sha256'])}, indent=2))
    return 0


if __name__ == '__main__':
    main()
