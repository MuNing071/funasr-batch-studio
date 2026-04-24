# Contributing

## Development principles

- keep the GUI thin and move processing rules into `funasr_gui/core`
- prefer deterministic local behavior over hidden automations
- preserve resume safety and manifest compatibility when changing runtime behavior
- keep tests focused on the most failure-prone surfaces: paths, resume, history, diagnostics, and UI initialization

## Local development

```powershell
python -m pip install -U pip
python -m pip install -e .[dev]
```

Run tests:

```powershell
$env:PYTHONPATH='.'
python -m unittest discover -s tests -v
```

## Pull request expectations

- explain user-visible behavior changes
- mention any manifest format changes
- include at least one test for bug fixes in core behavior
- keep docs in sync with new controls or workflows
