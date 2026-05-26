#!/usr/bin/env python3
"""Apply text corrections and dedup to existing SRT files (no re-transcription needed)."""

import re
from pathlib import Path

CORRECTIONS = [
    (re.compile(r'\bLuri\b'), 'Zluri'),
    (re.compile(r'\bluri\b'), 'Zluri'),
]

DEDUP_OVERLAP = 0.6


def word_set(text):
    return set(re.sub(r'[^a-z ]', '', text.lower()).split())


def parse_srt(text):
    blocks = []
    for block in re.split(r'\n\n+', text.strip()):
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            blocks.append({
                'idx': lines[0],
                'timing': lines[1],
                'text': ' '.join(lines[2:]),
            })
    return blocks


def dedup(blocks):
    result = list(blocks)
    i = 0
    while i < len(result) - 1:
        a = word_set(result[i]['text'])
        b = word_set(result[i + 1]['text'])
        if a and len(a & b) / len(a) >= DEDUP_OVERLAP:
            result.pop(i)
        else:
            i += 1
    return result


def renumber(blocks):
    for i, b in enumerate(blocks, 1):
        b['idx'] = str(i)
    return blocks


def to_srt(blocks):
    return '\n\n'.join(
        f"{b['idx']}\n{b['timing']}\n{b['text']}" for b in blocks
    ) + '\n'


srts = sorted(Path('.').glob('*.srt'))
for srt_path in srts:
    original = srt_path.read_text(encoding='utf-8')
    text = original
    for pat, rep in CORRECTIONS:
        text = pat.sub(rep, text)
    blocks = parse_srt(text)
    before = len(blocks)
    blocks = dedup(blocks)
    blocks = renumber(blocks)
    new_text = to_srt(blocks)
    srt_path.write_text(new_text, encoding='utf-8')
    removed = before - len(blocks)
    note = f'  (-{removed} dupes)' if removed else ''
    changed = 'patched' if new_text != original else 'ok'
    print(f'{srt_path.name}: {len(blocks)} cues  [{changed}]{note}')
