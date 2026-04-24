from __future__ import annotations


MODEL_PRESETS: dict[str, dict[str, object]] = {
    "Balanced": {
        "model": "paraformer-zh",
        "vad_model": "fsmn-vad",
        "punc_model": "ct-punc-c",
        "device": "cpu",
        "batch_size_s": 300,
        "description": "Recommended default for long-form Chinese transcription.",
    },
    "Fast CPU": {
        "model": "paraformer-zh",
        "vad_model": "fsmn-vad",
        "punc_model": "ct-punc-c",
        "device": "cpu",
        "batch_size_s": 120,
        "description": "Shorter batches for steadier CPU runs and lower memory pressure.",
    },
    "GPU Throughput": {
        "model": "paraformer-zh",
        "vad_model": "fsmn-vad",
        "punc_model": "ct-punc-c",
        "device": "cuda",
        "batch_size_s": 600,
        "description": "Higher throughput when CUDA is available.",
    },
    "SenseVoice Review": {
        "model": "SenseVoiceSmall",
        "vad_model": "",
        "punc_model": "",
        "device": "cpu",
        "batch_size_s": 180,
        "description": "Useful for quick exploration with a different recognition model.",
    },
}

