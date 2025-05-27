
<div align="center">
<img src='assets/index_icon.png' width="250"/>
</div>


<h2><center>IndexTTS批量语音克隆工具</h2>

<p align="center">
<a href='https://arxiv.org/abs/2502.05512'><img src='https://img.shields.io/badge/ArXiv-2502.05512-red'></a>

## Usage Instructions
详细步骤可以点击链接查看教程视频：（）
### Environment Setup
1. Download this repository:
```bash
git clone https://github.com/nanaoto/index-tts-webui.git
cd index-tts-webui
```

### 运行webui
#### MacOS
双击`run.sh.command`脚本，或在终端中运行以下命令：
```bash
bash run.sh
```
#### Linux
在终端中运行以下命令：
```bash
bash run.sh
```
#### Windows
双击`run.bat`脚本，或在git bash中运行以下命令：
```bash
bash run.sh
```

#### 已测试环境
|OS| Python  | CUDA | GPU                       |RAM|
|---|---------|------|---------------------------|---|
|Linux| 3.10.12 | 12.4 | NVIDIA GeForce RTX 4090   |-|
|MacOS|3.10.12|-| Apple M1                  |16GB|
|MacOS|3.10.12|-| Apple M2                  |16GB|
|MacOS|3.10.12|-| Apple M3                  |16GB|
|MacOS|3.10.12|-| Apple M4                  |16GB|
|Windows 11|3.10.12|-| NVIDIA GeForce RTX 3060Ti |-|

## Acknowledge
1. [tortoise-tts](https://github.com/neonbjb/tortoise-tts)
2. [XTTSv2](https://github.com/coqui-ai/TTS)
3. [BigVGAN](https://github.com/NVIDIA/BigVGAN)
4. [wenet](https://github.com/wenet-e2e/wenet/tree/main)
5. [icefall](https://github.com/k2-fsa/icefall)

## 📚 Citation

🌟 If you find our work helpful, please leave us a star and cite our paper.

```
@article{deng2025indextts,
  title={IndexTTS: An Industrial-Level Controllable and Efficient Zero-Shot Text-To-Speech System},
  author={Wei Deng, Siyi Zhou, Jingchen Shu, Jinchao Wang, Lu Wang},
  journal={arXiv preprint arXiv:2502.05512},
  year={2025}
}
```
