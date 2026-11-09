# CSV-driven Browser Automation Video Recorder

Browser automation and session recording utility built with Python 3.9+ and Playwright (Sync API). It processes structured rows from a CSV file, performs search automation with a simulated on-screen cursor and visual interaction effects, and outputs high-definition `.webm` video recordings.

---

## Deliverables & Structure

```text
github_submission/
├── capture_video.py       # Main entry point (CSV parsing and execution loop)
├── qscript.py             # Automation module (CaptureVideo_Magento, visual overlay)
├── requirements.txt       # Dependencies (playwright only)
├── input.csv              # Input dataset (UTF-8, delimiter ';', quotechar '"')
├── .gitignore             # Standard Python ignore rules
├── README.md              # Project documentation and setup guide
└── video/                 # Output folder for recorded .webm files
    ├── Acme Berlin Tech.webm
    └── Bavaria Soft Solutions.webm
```

---

## Requirements

- Python 3.9+
- Playwright (`pip install -r requirements.txt`)
- Chromium browser binaries (`playwright install chromium`)
- Standard library modules only (`csv`, `os`, `sys`, `time`, `math`, `random`, `re`, `shutil`)

---

## Setup & Running

### 1. Virtual Environment Setup

```bash
# Clone or navigate to the repository
cd github_submission

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (cmd):
.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Run Automation

```bash
python capture_video.py
```

The script iterates over each row in `input.csv`, runs the search scenario, saves the resulting video to `./video/<Company Name>.webm`, and outputs the absolute file path to `stdout`.

---

## Input CSV Format (`input.csv`)

- **Encoding**: UTF-8
- **Delimiter**: `;`
- **Field Qualifier**: `"`
- **Header**:
  ```csv
  URL;Company Name;Language;Country;Postcode;City;Street;HouseNo
  ```
- **Example**:
  ```csv
  "https://duckduckgo.com";"Acme Berlin Tech";"en";"Germany";"10115";"Berlin";"Friedrichstrasse";"42"
  "https://duckduckgo.com";"Bavaria Soft Solutions";"de";"Germany";"80331";"Munich";"Marienplatz";"1"
  ```

---

## Implementation Details

### Client-side Visual Overlay (`context.add_init_script`)
Because Playwright video recording records headless browser viewports without capturing the operating system cursor, a visual overlay is injected into the browser context via `context.add_init_script`:
- **SVG Cursor**: Topmost 32x32 white arrow with a black outline and click passthrough (`pointer-events: none`).
- **Yellow Highlight**: Semi-transparent yellow circle (32px radius) following the cursor pointer.
- **Click Wave**: Animated ripple element expanding on click events that automatically removes itself upon completion.
- **Search Suggestions**: Custom drop-down matching DuckDuckGo styling with dynamic query completions (bold/regular font hierarchy) updating on keystrokes.
- **State Continuity**: Coordinates and visibility flags persist in `sessionStorage` across full page navigations.

### Motion & Timing
- **Cursor Trajectory**: Curved cubic ease-in-out interpolation (`smooth_move_to`) with subtle orthogonal offsets rather than linear movements.
- **Human typing cadence**: Randomized typing delays between 70ms and 150ms per character, with word-boundary pauses.
- **Navigation Safety**: Navigation click ripples complete their animation cycle before trigger, avoiding frozen animation artifacts during page unloads.

### Core API (`qscript.py`)
```python
PATH_TO_VIDEO_FOLDER = "./video"

def CaptureVideo_Magento(
    url,
    company_name,
    language,
    country,
    postcode,
    city,
    street,
    house_no,
):
    ...
```
- Creates `PATH_TO_VIDEO_FOLDER` if it does not already exist.
- Sanitizes file paths to avoid invalid character collisions on Windows and Linux filesystems.
- Handles browser lifecycle cleanly with `try ... finally` resource cleanup.
- Returns the absolute path (`os.path.abspath`) to the recorded `.webm` file on success, or `None` on failure.
