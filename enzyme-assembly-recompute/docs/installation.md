# Installation

## Requirements

The reference environment is Python 3.12 with NumPy 2.3.5, SciPy 1.17.0, and Matplotlib 3.10.8. The workflow runs from its source directory and uses CPU computation. A GPU is not required.

Commands below assume a working directory containing `run_analysis.py`.

## Linux, WSL, and macOS

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements-tested.txt
./.venv/bin/python -m pip check
```

The environment interpreter is called directly; shell activation is optional. A system providing `python3` but no global `python` command is supported by this command sequence.

For Ubuntu 24.04 with Python 3.12, an `ensurepip` error during environment creation can be resolved by installing the matching venv component:

```bash
sudo apt update
sudo apt install python3.12-venv
python3 -m venv .venv
```

Other interpreter versions require their corresponding venv component. See the [Python documentation](https://docs.python.org/3/library/venv.html) and [Ubuntu package record](https://packages.ubuntu.com/noble/python3.12-venv).

## Native Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-tested.txt
.\.venv\Scripts\python.exe -m pip check
```

If the Windows Python launcher is used, the first command can be replaced by `py -3.12 -m venv .venv`. Subsequent commands call the environment interpreter explicitly.

For workflow commands elsewhere in the documentation, replace `./.venv/bin/python` with `.\.venv\Scripts\python.exe` on native Windows.

## Dependency files

| File | Purpose |
|---|---|
| `requirements-tested.txt` | Fixed versions used by the numerical reference |
| `requirements.txt` | Broader version ranges for exploratory environments |
| `requirements-extract.txt` | Optional DOCX verification dependency |

The fixed file is the reproducibility default. Results obtained with broader ranges should retain the generated environment record. No package publication or hosted installation service is required.

## Verify installation

```bash
./.venv/bin/python run_analysis.py --version
./.venv/bin/python run_analysis.py --config configs/quick.json --check-only
./.venv/bin/python -m unittest discover -s tests -v
```

See [Usage](usage.md) for analysis commands and [Reproducibility](../REPRODUCIBILITY.md) for supported validation claims.
