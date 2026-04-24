# Security

## Scope

FunASR Batch Studio is a local desktop transcription tool. It does not intentionally transmit user media or transcripts to a hosted service, but upstream model download behavior may contact external endpoints when models are not already cached.

## Security posture

- local manifest and settings files are stored in the user app-state directory
- the app does not execute user-supplied code
- input handling is restricted to files and folders selected by the user
- temp wav names are sanitized to stable hashes to reduce path-fragility issues

## Known areas to review before public release

- third-party dependency updates
- model download source trust
- `ffmpeg` supply-chain and redistribution policy
- transcript storage location and workstation access controls

## Reporting

Until a public repository exists, report issues privately to the project owner.

