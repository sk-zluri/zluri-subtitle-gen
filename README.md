# Zluri Subtitle Generator Skill

Generates professional-quality SRT subtitle files from MP4 videos using Whisper large-v3.

Designed for Zluri Academy screen-recording videos. Produces single-line, ~1.5–2.5s cues that match the readability standard established in the Ideal Subtitle Demo — ready to import into Premiere Pro with minimal manual editing.

---

## What it does

- Transcribes audio with word-level timestamps (Whisper large-v3)
- Rebuilds subtitles as single-line cues, breaking at natural speech rhythm points
- Corrects product terms automatically: `Zluri`, `GitHub`, `IGA`, `SSO`, `Okta`, `Slack`, `Workday`, `Jira`, `Salesforce`, `Microsoft`, `Azure`
- Removes Whisper hallucinations and near-duplicate cues
- Saves one `.srt` file alongside each `.mp4`

---

## Requirements

- **Python 3.11+** — [python.org/downloads](https://www.python.org/downloads/)
- **NVIDIA GPU with 4GB+ VRAM** — strongly recommended (RTX series). CPU works but is 10–20× slower.
- **ffmpeg** — required by Whisper to decode MP4 audio

---

## Setup (one-time)

### 1. Install ffmpeg

Download from [ffmpeg.org/download.html](https://ffmpeg.org/download.html) and make sure `ffmpeg` is on your PATH.  
Quick check: open a terminal and run `ffmpeg -version`. It should print a version number.

### 2. Install PyTorch

Go to **[pytorch.org/get-started/locally](https://pytorch.org/get-started/locally/)**, select your OS, Package = Pip, Language = Python, and your CUDA version (check it with `nvidia-smi`). Copy and run the generated `pip install` command.

Example for CUDA 12.6:
```
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
```

If you don't have an NVIDIA GPU, select CPU and run:
```
pip install torch torchvision torchaudio
```

### 3. Install Whisper and dependencies

```
pip install -r requirements.txt
```

### 4. Verify GPU is active (optional but recommended)

```
python -c "import torch; print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"
```

---

## Usage

1. Copy your `.mp4` files into a folder.
2. Copy `generate_subtitles.py` into the same folder (or run it from anywhere with a path).
3. Open a terminal in that folder and run:

```
python generate_subtitles.py
```

The script will:
- Load the Whisper model (downloads ~2.9 GB on first run, cached after that)
- Process each `.mp4` file one by one
- Save a `.srt` file next to each video

**Processing time** (approximate, with GPU):
| Video length | Time |
|---|---|
| 3–5 min | ~15–20s |
| 10–15 min | ~50–90s |
| 20+ min | ~3 min |

CPU-only is roughly 10–20× slower.

---

## Patching existing SRTs

If you already have `.srt` files generated with an older version of this tool, run:

```
python patch_srts.py
```

This applies the latest term corrections and removes duplicate cues without re-transcribing.

---

## Customising

### Adding product terms

Open `generate_subtitles.py` and find the `TERM_CORRECTIONS` list near the top. Add a line:

```python
(re.compile(r'\byourterm\b', re.IGNORECASE), 'YourTerm'),
```

### Adjusting subtitle style

These constants at the top of `generate_subtitles.py` control the output style:

| Constant | Default | What it does |
|---|---|---|
| `MAX_CHARS` | `52` | Max characters per subtitle line |
| `MAX_DURATION` | `2.5` | Max seconds per cue |
| `PAUSE_BREAK_SECS` | `0.25` | Minimum speech pause to trigger a cue break |
| `MIN_CUE_DURATION` | `0.7` | Cues shorter than this are merged with a neighbour |

---

## Troubleshooting

**"No .mp4 files found"** — Make sure you're running the script from the folder containing your videos, or check that the files end in `.mp4` (lowercase).

**Whisper model download is slow** — The large-v3 model is ~2.9 GB and downloads once to `~/.cache/whisper`. After that, it loads from disk in ~10 seconds.

**GPU not detected after installing PyTorch** — Re-run the PyTorch install command from step 2. Make sure you selected the correct CUDA version for your driver (`nvidia-smi` shows it in the top-right corner of the output).

**Some product names still wrong** — Add them to `TERM_CORRECTIONS` in `generate_subtitles.py` and re-run. If a name is consistently wrong, it's worth adding it permanently.
