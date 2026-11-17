#!/usr/bin/env bash
# One-time setup for the ReachMora 2D long-form engine (Linux/macOS sandbox or local machine).
# Installs Python packages and the offline speech model used to time the picture to the voiceover.
set -e
PY=${PYTHON:-python3}
command -v ffmpeg >/dev/null || { echo "ffmpeg missing: install it (apt-get install -y ffmpeg / brew install ffmpeg)"; exit 1; }
$PY -m pip install -q skia-python numpy scipy soundfile sherpa-onnx 2>/dev/null \
  || $PY -m pip install -q --break-system-packages skia-python numpy scipy soundfile sherpa-onnx
$PY -c "import skia, numpy, scipy, soundfile, sherpa_onnx; print('python packages ok')"
M=${RM_MODELS:-$HOME/models}; mkdir -p "$M"; cd "$M"
NAME=sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8
if [ ! -f "$NAME/encoder.int8.onnx" ]; then
  echo "downloading speech model (~460 MB, GitHub release)..."
  curl -sSL -O "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/$NAME.tar.bz2" && tar xjf "$NAME.tar.bz2" && rm -f "$NAME.tar.bz2" \
    || echo "WARNING: model download failed. Alignment will fall back to pause detection (less exact)."
fi
[ -f "$NAME/encoder.int8.onnx" ] && echo "speech model ok: $M/$NAME"
echo "cpus: $(nproc 2>/dev/null || sysctl -n hw.ncpu)"
