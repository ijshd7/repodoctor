# RepoDoctor

A CLI tool that detects technical debt in Python and JavaScript/TypeScript codebases.

## Features

- **Complexity analysis**: Long functions, high cyclomatic complexity, large files, deep nesting
- **Code duplication**: Detects duplicate blocks across files
- **Dependency analysis**: Import graphs, circular dependencies, coupling metrics
- **Git analysis**: Commit churn, hotspots, contributor spread (gracefully skipped if not a Git repo)

## Requirements

- **Python 3.10+**
- **pip 21.3+** (for editable installs)

## Installation

### Using a virtual environment (recommended)

```bash
cd repodoctor
python --version   # Must show 3.10 or higher
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install --upgrade pip   # Requires pip 21.3+ for editable installs
pip install -e .
```

If `python --version` shows 3.9 or lower, use a newer Python (e.g. `pyenv shell 3.11` or `pyenv local 3.11`) and remove any existing `.venv` before creating a new one.

**pyenv + pyenv-virtualenv:** If you use pyenv-virtualenv and still see the wrong Python version, use the explicit path to bypass shims. **Important:** Deactivate any active venv first (or use a fresh terminal), otherwise `pyenv which python` may resolve to the wrong interpreter:

```bash
deactivate          # Or: source deactivate (if using pyenv-virtualenv)
rm -rf .venv
$(pyenv which python) -m venv .venv
source .venv/bin/activate
python --version   # Should now show 3.11.x
```

If `python --version` still shows the wrong version in your interactive terminal (pyenv-virtualenv can override PATH), run `hash -r` after activate to clear the shell's command cache, or use `.venv/bin/python` explicitly (e.g. `.venv/bin/python -m pip install -e .`).

With the venv activated, run `repodoctor` from any directory to scan other repos.

### Direct install

```bash
pip install --upgrade pip   # Requires pip 21.3+ for editable installs
pip install -e .
```

### Alternative: pipx (isolated global install)

```bash
pipx install -e /path/to/repodoctor
```

## Usage

```bash
repodoctor scan [PATH] [OPTIONS]
repodoctor version
```

### Scan Options

- `--format` / `-f`: Output format (`terminal`, `json`, `html`)
- `--output` / `-o`: Output file path (for json/html)
- `--threshold` / `-t`: Minimum severity to display
- `--exclude` / `-e`: Glob patterns to skip
- `--no-git`: Skip Git analysis
