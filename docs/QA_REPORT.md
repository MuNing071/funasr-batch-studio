# QA Report

## Automated checks run locally

```powershell
$env:PYTHONPATH='.'
python -m unittest discover -s tests -v
python -m funasr_gui.cli diagnostics
```

## GUI smoke

- created `MainWindow`
- showed the window in offscreen mode
- entered and detected a sample media file
- applied a model preset
- exited cleanly

## Real pipeline check

Validated with:

- input: local sample wav from the development workspace
- model: `paraformer-zh`
- output: temporary manifest + txt/json

Observed result:

- pipeline completed successfully
- txt and json outputs were written
- transcript preview: `欢迎大家来体验达摩院推出的语音识别模型。`

## Remaining manual checks before public release

- run one long-video batch through the GUI on a clean machine
- verify resume and retry after force-closing the app mid-run
- verify behavior on a CUDA-enabled machine
- verify Windows path handling with deep folder nesting and punctuation-heavy filenames
