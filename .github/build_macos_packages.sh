#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

cd "$SCRIPT_DIR"

cd ..

mkdir venv

PYTHON_VERSION="3.10.17"
PY_RELEASE_VERSION="20250521"

WGET_CMD="wget -nv --tries=25 --wait=5 --read-timeout=40 --retry-on-http-error=404"

$WGET_CMD "https://github.com/astral-sh/python-build-standalone/releases/download/$PY_RELEASE_VERSION/cpython-$PYTHON_VERSION+$PY_RELEASE_VERSION-aarch64-apple-darwin-pgo+lto-full.tar.zst" -O python.tar.zst

tar --use-compress-program=unzstd -xf python.tar.zst

mv python/install/* venv

rm -rf python.tar.zst
rm -rf python

WORKDIR=$(pwd)
export PYTHONPATH=WORKDIR
export PATH="$WORKDIR/venv/bin:$PATH"

echo "Using cached ffmpeg"
rsync -a ~/ffmpeg-cache/ ./venv/

pip3.10 install deepspeed
pip3.10 install --upgrade pip
pip3.10 install -r requirements.txt -i https://pypi.org/simple

/opt/homebrew/bin/python3 -m pip install setuptools huggingface_hub modelscope -U --break-system-packages

/opt/homebrew/bin/hf download IndexTeam/IndexTTS-1.5 \
    config.yaml bigvgan_discriminator.pth bigvgan_generator.pth bpe.model dvae.pth gpt.pth unigram_12000.vocab \
    --local-dir checkpoints

cp ./.github/install_for_mac.sh .

rm -rf .github
rm -rf .git
rm -rf .gitignore

# echo "Downloading funasr..."
# $WGET_CMD "https://huggingface.co/XXXXRT/GPT-SoVITS-Pretrained/resolve/main/funasr.zip"
# unzip -q funasr.zip -d tools/asr/models
# rm -rf funasr.zip

echo "Downloading uvr5 weight..."
$WGET_CMD "https://huggingface.co/XXXXRT/GPT-SoVITS-Pretrained/resolve/main/uvr5_weights.zip"
unzip -q uvr5_weights.zip
rm -rf uvr5_weights.zip
mv uvr5_weights/* tools/uvr5/uvr5_weights
rm -rf uvr5_weights

echo "Downloading NLTK"
PY_PREFIX=$(python3.10 -c "import sys; print(sys.prefix)")
NLTK_URL="https://huggingface.co/XXXXRT/GPT-SoVITS-Pretrained/resolve/main/nltk_data.zip"
$WGET_CMD "$NLTK_URL" -O nltk_data.zip
unzip -q -o nltk_data -d "$PY_PREFIX"
rm -rf nltk_data.zip

date_mmdd=${DATE:-$(date +%m%d)}

pkg_name="Index-TTS-Packages-$date_mmdd-apple-arm64"

cd ../

cp -R "$WORKDIR" "$pkg_name"

echo "7z a -tzip -mm=Deflate $pkg_name.zip $pkg_name -mx=9 -mmt=on -bb1"

7z a -tzip -mm=Deflate "$pkg_name.zip" "$pkg_name" -mx=9 -mmt=on -bb1

echo "Upload to ModelScope"
msUser=$MODELSCOPE_USERNAME
msToken=$MODELSCOPE_TOKEN

/opt/homebrew/bin/modelscope upload "$msUser/Index-TTS-Packages" "$pkg_name.zip" "$pkg_name.zip" --repo-type model --token "$msToken"
