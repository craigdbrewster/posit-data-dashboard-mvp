# Posit Zenith Shiny Dashboard

Python Shiny prototype for viewing Connect, Workbench, and tenancy usage metrics.

## Run locally
- Python 3.9+ recommended.
- Install deps: `pip install -r requirements.txt`
- Start the app: `shiny run --reload app.py`

## Data
- Source data lives in `data/usage_log.csv`. The app reads it via `data.py`; keep that file in place when moving the project.

## Packaging
- When ready to move into a walled garden, zip the repo contents (exclude `.git` and `.venv`) and import into Posit Workbench.
