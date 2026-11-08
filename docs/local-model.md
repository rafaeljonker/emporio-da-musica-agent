# Running Gemma 4 locally (`PROVIDER=local`)

`make up PROVIDER=local` runs Gemma 4 through [Ollama](https://ollama.com/download). Before it starts, `emporio local-model` detects the machine, picks the model size by memory, prints the download size and expected time per reply, pulls the tag and creates `emporio-gemma` with a 16k-token context. On a Mac, install the Ollama app first (Docker on macOS has no Metal).

Routes:
- **Apple Silicon Mac:** native Ollama, with Metal.
- **NVIDIA GPU:** Ollama in Docker with the GPU, when `nvidia-smi` works and Docker lists the `nvidia` runtime.
- **Anything else:** Ollama in Docker on the CPU.

The table follows `choose_local_model` in [`backend/src/emporio/platform/local_model.py`](../backend/src/emporio/platform/local_model.py). Memory is system RAM.

| Machine | Model | Download | Time per reply (estimate) |
|---|---|---|---|
| Apple Silicon Mac, 32 GB or more | `gemma4:31b` | ~20 GB | about 10-30 s |
| Apple Silicon Mac, 16 to 31 GB | `gemma4:12b` | ~8 GB | about 20-60 s, less with Metal |
| Apple Silicon Mac, under 16 GB | `gemma4:e4b` | ~10 GB | about 10-30 s |
| Any NVIDIA GPU | `gemma4:31b` | ~20 GB | a few seconds with 24 GB+ of VRAM, minutes if it spills to RAM |
| CPU only, 16 GB or more | `gemma4:12b` | ~8 GB | about 20-60 s |
| CPU only, under 16 GB | `gemma4:e4b` | ~10 GB | about 10-30 s |

None of these times has been measured: they are research estimates (CPU decoding is bound by RAM bandwidth). For replies in a few seconds, use the hosted demo.
