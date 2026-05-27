#!/usr/bin/env python3
"""
Generate styled SRT subtitles from MP4 files using Whisper large-v3.
Produces single-line cues (~1.5-2.5s) matching professional readability standards.
See README.md for setup and usage instructions.
"""

import re
import sys
import time
from pathlib import Path

import torch
import whisper

# ---------------------------------------------------------------------------
# Configuration — adjust these to tune subtitle style
# ---------------------------------------------------------------------------
MODEL_NAME = "large-v3"
MAX_CHARS = 52          # max characters per subtitle line
MAX_DURATION = 2.5      # max seconds per cue
PAUSE_BREAK_SECS = 0.25 # speech pause that triggers a cue break
PAUSE_MIN_CHARS = 25    # only pause-break if current cue is already this long
MIN_CUE_DURATION = 0.7  # cues shorter than this get merged with a neighbour
HALLUCINATION_DUR = 0.15
DEDUP_OVERLAP = 0.6     # word-overlap ratio at which a repeated cue is dropped

# ---------------------------------------------------------------------------
# Term corrections — add product names your videos mention
# ---------------------------------------------------------------------------
TERM_CORRECTIONS = [
    (re.compile(r'\bzluri\b', re.IGNORECASE), 'Zluri'),
    (re.compile(r'\bluri\b',  re.IGNORECASE), 'Zluri'),   # Whisper sometimes drops the Z
    (re.compile(r'\bgithub\b', re.IGNORECASE), 'GitHub'),
    (re.compile(r'\bi\.?g\.?a\.?\b', re.IGNORECASE), 'IGA'),
    (re.compile(r'\bs\.?s\.?o\.?\b',  re.IGNORECASE), 'SSO'),
    (re.compile(r'\bokta\b',       re.IGNORECASE), 'Okta'),
    (re.compile(r'\bworkday\b',    re.IGNORECASE), 'Workday'),
    (re.compile(r'\bjira\b',       re.IGNORECASE), 'Jira'),
    (re.compile(r'\bslack\b',      re.IGNORECASE), 'Slack'),
    (re.compile(r'\bsalesforce\b', re.IGNORECASE), 'Salesforce'),
    (re.compile(r'\bmicrosoft\b',  re.IGNORECASE), 'Microsoft'),
    (re.compile(r'\bazure\b',      re.IGNORECASE), 'Azure'),
]

# Words that can start a new clause — break before these after a comma
CLAUSE_STARTERS = {
    'but', 'and', 'so', 'because', 'when', 'if', 'while', 'then',
    'which', 'that', 'where', 'as', 'once', 'until', 'unless',
    'however', 'therefore', 'thus', 'now', 'next', 'also', 'finally',
}

if torch.cuda.is_available():
    DEVICE = 'cuda'
    USE_FP16 = True
elif torch.backends.mps.is_available():
    DEVICE = 'mps'
    USE_FP16 = False   # fp16 on MPS is unstable; mps alone gives the speed boost
else:
    DEVICE = 'cpu'
    USE_FP16 = False


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def correct_terms(text):
    for pattern, replacement in TERM_CORRECTIONS:
        text = pattern.sub(replacement, text)
    return text


def format_ts(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_cues(words):
    """
    Re-chunk word-level Whisper output into single-line subtitle cues.

    Break priority:
      1. Hyphen merge  — token starting with '-' is glued to previous word (Whisper artifact)
      2. Hard limit    — adding this word would exceed MAX_CHARS or MAX_DURATION
      3. Sentence end  — previous word ends with . ? !
      4. Pause break   — natural speech pause >= PAUSE_BREAK_SECS with sufficient content
      5. Clause break  — comma followed by a clause-starting word
    """
    cues = []
    bucket = []

    def emit():
        if not bucket:
            return
        text = correct_terms(' '.join(w['word'].strip() for w in bucket))
        cues.append({'start': bucket[0]['start'], 'end': bucket[-1]['end'], 'text': text})
        bucket.clear()

    for word_data in words:
        raw = word_data.get('word', '').strip()
        if not raw:
            continue

        # Glue hyphen-continuation tokens back onto the previous word
        # (Whisper splits "event-based" into ["event", "-based"])
        if raw.startswith('-') and bucket:
            last = bucket[-1]
            bucket[-1] = {
                'word': last['word'].rstrip() + raw,
                'start': last['start'],
                'end': word_data['end'],
            }
            continue

        if not bucket:
            bucket.append(word_data)
            continue

        current_text  = ' '.join(w['word'].strip() for w in bucket)
        candidate     = current_text + ' ' + raw
        duration      = word_data['end'] - bucket[0]['start']
        pause         = word_data['start'] - bucket[-1]['end']
        prev_word     = bucket[-1]['word'].strip()

        hard_limit   = len(candidate) > MAX_CHARS or duration > MAX_DURATION
        sent_end     = bool(prev_word) and prev_word[-1] in '.?!'
        pause_break  = (pause >= PAUSE_BREAK_SECS
                        and len(current_text) >= PAUSE_MIN_CHARS
                        and len(bucket) >= 3)
        clause_break = (prev_word.endswith(',')
                        and raw.lower() in CLAUSE_STARTERS
                        and len(bucket) >= 4)

        if hard_limit or sent_end or pause_break or clause_break:
            emit()

        bucket.append(word_data)

    emit()
    return cues


def _word_set(text):
    return set(re.sub(r'[^a-z ]', '', text.lower()).split())


def clean_cues(cues):
    """
    Three-pass cleanup:
      1. Drop zero-duration Whisper hallucinations.
      2. Drop near-duplicate consecutive cues (Whisper sometimes repeats a phrase).
      3. Merge cues shorter than MIN_CUE_DURATION into their best neighbour.
    """
    # Pass 1: hallucination filter
    cleaned = [c for c in cues
               if not (c['end'] - c['start'] < HALLUCINATION_DUR and len(c['text']) > 15)]

    # Pass 2: dedup — if cue[i] is mostly contained in cue[i+1], drop cue[i]
    i = 0
    while i < len(cleaned) - 1:
        a = _word_set(cleaned[i]['text'])
        b = _word_set(cleaned[i + 1]['text'])
        if a and len(a & b) / len(a) >= DEDUP_OVERLAP:
            cleaned.pop(i)
        else:
            i += 1

    # Pass 3: merge short cues
    i = 0
    while i < len(cleaned):
        c = cleaned[i]
        if c['end'] - c['start'] < MIN_CUE_DURATION:
            if i > 0:
                prev = cleaned[i - 1]
                cleaned[i - 1] = {
                    'start': prev['start'],
                    'end': c['end'],
                    'text': prev['text'] + ' ' + c['text'],
                }
                cleaned.pop(i)
                continue
            if i < len(cleaned) - 1:
                nxt = cleaned[i + 1]
                cleaned[i] = {
                    'start': c['start'],
                    'end': nxt['end'],
                    'text': c['text'] + ' ' + nxt['text'],
                }
                cleaned.pop(i + 1)
                continue
        i += 1

    return cleaned


def to_srt(cues):
    lines = []
    for i, c in enumerate(cues, 1):
        lines += [str(i), f"{format_ts(c['start'])} --> {format_ts(c['end'])}", c['text'], '']
    return '\n'.join(lines)


def process_video(path, model):
    t0 = time.time()
    print(f"  {path.name} ... ", end='', flush=True)

    result = model.transcribe(
        str(path),
        word_timestamps=True,
        language='en',
        task='transcribe',
        fp16=USE_FP16,
        verbose=False,
        device=DEVICE,
    )

    all_words = [w for seg in result['segments'] for w in seg.get('words', [])]
    cues = clean_cues(build_cues(all_words))
    out_path = path.with_suffix('.srt')
    out_path.write_text(to_srt(cues), encoding='utf-8')
    print(f"{len(cues)} cues  |  {time.time() - t0:.0f}s  ->  {out_path.name}")


def main():
    videos = sorted(Path('.').glob('*.mp4'))
    if not videos:
        sys.exit("No .mp4 files found in current directory.")

    print(f"Loading Whisper {MODEL_NAME} ({DEVICE.upper()}) ...", end=' ', flush=True)
    model = whisper.load_model(MODEL_NAME, device=DEVICE)
    print("ready.\n")
    print(f"Found {len(videos)} video(s) to process:\n")

    for v in videos:
        process_video(v, model)

    print("\nAll done. SRT files are saved next to each video.")


if __name__ == '__main__':
    main()
