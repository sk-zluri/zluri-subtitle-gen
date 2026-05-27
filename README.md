# Zluri Subtitle Generator Skill

Generates professional-quality SRT subtitle files from MP4 videos using Whisper large-v3.

Produces single-line, ~1.5–2.5s cues that match the readability standard established in the Ideal Subtitle Demo — ready to import into Premiere Pro with minimal manual editing.

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
- **GPU** — strongly recommended. See table below for what's supported.
- **ffmpeg** — required by Whisper to decode MP4 audio

| Machine | GPU acceleration | Speed |
|---|---|---|
| Windows with NVIDIA GPU | CUDA | Fast (~1–3 min per video) |
| Mac with Apple Silicon (M1/M2/M3/M4) | MPS (Metal) | Fast (~1–3 min per video) |
| Mac with Intel chip / no GPU | CPU only | Slow (~10–20 min per video) |

---

## Setup (one-time)

### 1. Install ffmpeg

**Mac:**
```
brew install ffmpeg
```
(Install Homebrew first if needed: [brew.sh](https://brew.sh))

**Windows:** Download from [ffmpeg.org/download.html](https://ffmpeg.org/download.html) and add it to your PATH.

Quick check for both: run `ffmpeg -version` in a terminal — it should print a version number.

### 2. Install PyTorch

Go to **[pytorch.org/get-started/locally](https://pytorch.org/get-started/locally/)**, select your OS, Package = Pip, Language = Python, and your compute platform. Copy and run the generated command.

**Mac (Apple Silicon or Intel):**
```
pip install torch torchvision torchaudio
```

**Windows with NVIDIA GPU** — select your CUDA version (check with `nvidia-smi`). Example for CUDA 12.6:
```
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
```

### 3. Install Whisper and dependencies

```
pip install -r requirements.txt
```

### 4. Verify GPU is active (optional but recommended)

**Mac (Apple Silicon):**
```
python -c "import torch; print('MPS available:', torch.backends.mps.is_available())"
```

**Windows (NVIDIA):**
```
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

When you run the script, the first line printed will confirm which device it's using, e.g. `Loading Whisper large-v3 (MPS) ...`

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

**GPU not detected (Windows/NVIDIA)** — Re-run the PyTorch install command from step 2 and make sure you selected the correct CUDA version (`nvidia-smi` shows it in the top-right corner).

**GPU not detected (Mac/Apple Silicon)** — Make sure you installed the standard PyTorch for Mac (no CUDA flag). Run the verify command in step 4; if MPS shows `False`, try reinstalling PyTorch.

**Some product names still wrong** — Add them to `TERM_CORRECTIONS` in `generate_subtitles.py` and re-run. If a name is consistently wrong, it's worth adding it permanently.
