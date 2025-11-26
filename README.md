# Giri-Prasad

Giri-Prasad is an AI-powered automation agent for Windows that combines large-language-model reasoning, real-time computer control, and reinforcement learning feedback. The agent inspects screenshots of the desktop, decides on keyboard or mouse actions, and learns from user feedback by tracking rewards and success rates. A web interface is included for monitoring sessions and giving feedback from the browser.

## Key Capabilities

- **Autonomous desktop control** powered by Ollama-hosted vision/language models (e.g., `llava`, `gemma3`, `mistral`).
- **Structured action loop** producing JSON instructions (`press`, `write`, `click`, `done`) that drive PyAutoGUI operations.
- **Human-in-the-loop reinforcement feedback** with positive/negative rewards, success-rate tracking, and persistent session logs.
- **Flask + Socket.IO dashboard** showing live logs, rewards, and model reasoning with real-time feedback buttons.
- **Screenshot capture and optional YOLO labeling** to ground the model in the current desktop view.
- **Voice prompt support** using `whisper-mic` when launched in voice mode.

## Repository Layout

```
controller/
   main.py             # CLI entry point that launches the agent loop
   control.py          # OS interaction layer, reward prompting, stats logging
   config.py           # Ollama client configuration and environment loading
   core/
      screenshot.py     # Screenshot capture helpers
      operating_system.py # Keyboard/mouse abstractions via PyAutoGUI
      style.py          # ANSI coloring utilities for console output
      ...               # Misc helpers (labeling, OCR, etc.)
   models/
      apis.py           # Ollama chat bridge, screenshot capture, JSON cleaning
      prompts.py        # System/user prompt templates with reward instructions
      weights/best.pt   # YOLO weights (optional labeled-click support)
   web/
      app.py            # Flask + Socket.IO server with action logger and rewards
      templates/index.html
requirements.txt      # Core agent dependencies
requirements-web.txt  # Web dashboard dependencies
labeled_images/       # Sample labeled datasets for training/testing
screenshots/          # Latest screenshot captured from the desktop loop
session_stats/        # Auto-created JSON summaries per CLI session
```

## Prerequisites

- Windows 10/11 (project uses Windows-specific key bindings by default).
- Python 3.10+ (virtual environment recommended).
- [Ollama](https://ollama.com) installed locally with desired models pulled (`ollama pull llava`).
- Optional GPU acceleration for YOLO / EasyOCR (falls back gracefully on CPU).

## Installation

1. **Create and activate a virtual environment** (example using PowerShell):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install core dependencies**:

   ```powershell
   pip install -r requirements.txt
   ```

3. **Install web dashboard dependencies (optional)**:

   ```powershell
   pip install -r requirements-web.txt
   ```

4. **Configure Ollama host (optional)**:

   - Default: connects to `http://127.0.0.1:11434`.
   - Remote host: set `OLLAMA_HOST` in a `.env` file or environment variable, e.g.

     ```env
     OLLAMA_HOST=http://192.168.1.50:11434
     ```

## Running the CLI Agent

Launch the agent from the repo root:

```powershell
python -m controller.main
```

or run the entry module directly:

```powershell
python controller/main.py --model llava
```

### CLI Flags

- `--model <name>` – Ollama model (default `llava`).
- `--voice` – enable microphone capture via `whisper-mic` for the initial objective.
- `--verbose` – print verbose diagnostic output from prompts and API calls.
- `--prompt "objective"` – skip interactive prompt and start immediately.

### Reward & Feedback Loop

After each executed action, the CLI asks:

```
Was this action correct? (y/n/s to skip):
```

- `y` assigns **+1.0 reward**, increments success count, and appends a positive feedback message to the model context.
- `n` assigns **-0.5 reward**, increments failure count, and appends corrective feedback to the model context.
- `s` skips feedback for ambiguous actions.

Session metrics (total actions, success rate, cumulative reward) print continuously and are persisted in `session_stats/session_YYYYMMDD_HHMMSS.json` at the end of each run.

### Voice Mode

Install audio extras (`pip install -r requirements-audio.txt`) and run with `--voice` to dictate objectives via microphone.

## Running the Web Dashboard

1. Ensure the virtual environment is active and dependencies installed.
2. Start the Flask server:

   ```powershell
   python -m controller.web.app
   ```

3. Open `http://localhost:5000` in a browser.
4. Provide an objective and pick a model, then click **🚀 Start Agent**.

### Web Features

- **Live log stream** of every LLM response and executed action.
- **Feedback buttons** per action (`✓ Success` / `✗ Failed`) mapping to +10 and -5 reward respectively.
- **Statistics panel** summarizing reward, success rate, and loop count.
- **Ollama health checks** with the ability to start `ollama serve` from the UI on Windows.

Reward values for the web UI are configurable in `controller/web/app.py` (`ActionLogger.log_action` and `/api/feedback`).

## Prompting & Model Behaviour

- System prompts are tailored per model family (standard, labeled YOLO, or OCR mode).
- Prompts explicitly instruct the agent to rely on keyboard (`press`, `write`) actions and to treat feedback messages as guidance for maximizing reward.
- Screenshots are captured each loop (`screenshots/screenshot.png`) and attached to Ollama vision models.

## Extending the Agent

- **Custom Actions**: extend `controller/control.py` to add new action types or instrumentation.
- **Reward Scheme**: adjust values in `update_stats` (CLI) or Flask endpoints (web) to tune learning signals.
- **Model Prompts**: modify `controller/models/prompts.py` to add rules, examples, or new prompt templates.
- **Integration Hooks**: use the session stats JSON files for downstream analytics or RL fine-tuning pipelines.

## Troubleshooting

- **Ollama connection errors**: verify `ollama serve` is running and the model is pulled (`ollama pull llava`).
- **Permission issues**: run the terminal as Administrator if PyAutoGUI cannot send inputs.
- **Blank screenshots**: ensure no security software blocks screen capture; `screenshots/` will contain the latest capture.
- **Loop exits early**: the CLI stops after 10 loops by default; adjust `loop_count` guards in `controller/control.py` as needed.

## Development Notes

- When packaging for distribution, expose `controller.main:main_entry` as a console script entry point.
- YOLO labeling is currently disabled (`use_labeling = False`), but the pipeline is scaffolded for future use.
- Tests are not included; manual verification is recommended after changes (run CLI and web flows).

---

Maintained by Giri Prasad. Contributions and customizations are welcome—tweak reward schedules, add new models, or build additional interfaces on top of the core agent loop.
