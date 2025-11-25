# Running this project locally

> Quick steps to get the Posit Shiny app running on a macOS / Linux workstation.

1. Create and activate a virtual environment

```bash
cd /Users/craigbrewster/Documents/GitHub/posit-zenith-shiny
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Start the Shiny app (development)

```bash
# default: http://127.0.0.1:8000
python -m shiny run --reload app:app --port 8000
```

4. Data

- The app reads CSVs from the `data/` directory (`users.csv`, `tenancies.csv`, `licences.csv`, `timeseries.csv`). Keep these files in place or update paths in `app.py`.

**Deploying to Posit Connect (high level)**

- Posit Connect can deploy apps directly from a Git repository. Ensure this repository is pushed to a remote (GitHub, GitLab, or a git server) and that `app.py` and `requirements.txt` are at the repository root.
- On Posit Connect: choose "New Content" -> "Python Shiny App" and point it at the Git repository. Connect will install Python packages from `requirements.txt` and run `app.py`.

Notes and recommendations

- Python version: use Python 3.10+ locally. If your Posit Connect server requires a specific runtime, configure it on the server.
- Warnings: the app currently emits Shiny deprecation warnings about `layout_column_wrap` needing a named `width` parameter — these are non-blocking but worth addressing for future compatibility.
- I created a branch `setup/run-deploy` with the small fixes (syntax + requirements cleanup) and this `RUN.md` file; push that branch to your remote and then use Posit Connect to deploy from that branch.

If you want, I can also:
- Add a `Dockerfile` for containerised deployment.
- Tidy the Shiny deprecation warnings by naming the `width=` parameter in the UI calls.
- Create a simple GitHub Actions workflow to automatically push a tagged release to Posit Connect (if you use an API key).