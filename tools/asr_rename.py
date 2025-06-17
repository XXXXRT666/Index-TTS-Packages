import os
import shutil

from faster_whisper import WhisperModel

def asr_and_rename_files(input_dir,output_dir,device='cpu',precision='float32'):
    """
    使用语音识别模型为音频文件命名，并保存到指定目录
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    if not os.path.isdir("tools/asr/models/"):
        os.makedirs("tools/asr/models/")

    model_path = "tools/asr/models/faster-whisper-large-v3"  # 模型路径
    if not os.path.isdir(model_path) or not os.path.isfile(os.path.join(model_path, 'config.json')):
        from modelscope import snapshot_download
        # 下载模型
        print("ASR模型不存在，开始下载...")
        snapshot_download('keepitsimple/faster-whisper-large-v3', local_dir=model_path)
    model = WhisperModel(
        model_size_or_path=model_path, device=device, local_files_only=True,
        compute_type=precision)
    audio_extensions = ['.wav','.mp3']
    for root, dirs, files in os.walk(input_dir):
        for file_name in files:
            if file_name.startswith('.'):
                continue
            # 检查文件扩展名
            file_ext = os.path.splitext(file_name)[1].lower()
            file_path = os.path.join(root, file_name)
            # 检查是否为音频文件
            is_audio = file_ext in audio_extensions
            if not is_audio:
                continue
            print(f"处理音频文件: {file_path}")
            try:
                segments, info = model.transcribe(
                    audio=file_path,
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=700),
                    language=None)
                text = ''
                if info.language == "zh":
                    print("检测为中文文本, 转 FunASR 处理")
                    if ("only_asr" not in globals()):
                        from tools.asr.funasr_asr import only_asr  # 如果用英文就不需要导入下载模型
                    text = only_asr(file_path, language=info.language.lower())

                if text == '':
                    for segment in segments:
                        text += segment.text
                        # 清理文本，防止文件名非法字符
                text = text.strip()
                for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
                    text = text.replace(char, '')
                # 创建相对路径保持目录结构
                rel_path = os.path.relpath(root, input_dir)
                target_dir = os.path.join(output_dir, rel_path)
                os.makedirs(target_dir, exist_ok=True)
                # 构建新文件名
                ori_name = os.path.splitext(file_name)[0]
                output_file_name = f"{ori_name}-{text[:20]}{file_ext}"
                output_file_path = os.path.join(target_dir, output_file_name)
                shutil.move(file_path, output_file_path)
                print(f"已处理: {output_file_path}")
            except Exception as e:
                print(f"处理文件 {file_path} 时出错: {str(e)}")
        # shutil.copy(file_path, output_file_path)

if __name__ == "__main__":
    # from modelscope import snapshot_download
    #

    input_dir = "WORKSPACE/input"  # 输入目录
    output_dir = "WORKSPACE/output"  # 输出目录
    device = "cpu"  # 使用的设备
    precision = "float32"  # 精度
    asr_and_rename_files(input_dir, output_dir, device, precision)