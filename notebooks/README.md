# Notebooks

This directory contains Jupyter notebooks for interactive exploration of the `sat_private` pipeline.

## Contents

| Notebook | Description |
|---|---|
| `sat_private_pipeline.ipynb` | Full annotated 22-cell walkthrough: encode → prompt → verify → DIMACS → decode |

## Running

```bash
pip install -e .[dev]
pip install jupyter
jupyter notebook notebooks/
```

## Notes

- Never run notebooks with real secret state in a shared or cloud environment.
- The `caller_secret_state.json` output from demo cells is `.gitignored` and must not be committed.
