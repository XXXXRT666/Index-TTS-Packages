import os
import shutil
from typing import List, Dict


class PromptManager:
    def __init__(self, prompt_dir="saved_prompts"):
        self.prompt_dir = prompt_dir
        os.makedirs(self.prompt_dir, exist_ok=True)

    def save_prompt(self, audio_path: str, name: str = None) -> str:
        """保存上传的音频文件到 prompt 目录"""
        if not audio_path:
            return None

        # 如果没有指定名称，使用原文件名
        if not name:
            name = os.path.basename(audio_path)

        # 确保文件名有正确的扩展名
        if not any(name.endswith(ext) for ext in ['.wav', '.mp3', '.ogg']):
            name += '.wav'

        # 保存路径
        save_path = os.path.join(self.prompt_dir, name)

        # 复制文件
        shutil.copy2(audio_path, save_path)
        return save_path

    def list_prompts(self) -> List[Dict]:
        """列出所有保存的 prompts"""
        prompts = []
        if not os.path.exists(self.prompt_dir):
            return prompts

        for file in os.listdir(self.prompt_dir):
            if file.endswith(('.wav', '.mp3', '.ogg')):
                file_path = os.path.join(self.prompt_dir, file)
                prompts.append({
                    "name": file,
                    "path": file_path
                })
        return prompts

    def rename_prompt(self, old_path: str, new_name: str) -> str:
        """重命名已保存的 prompt"""
        if not old_path or not new_name:
            return None

        # 确保新名称有正确的扩展名
        if not any(new_name.endswith(ext) for ext in ['.wav', '.mp3', '.ogg']):
            ext = os.path.splitext(old_path)[1]
            new_name += ext

        new_path = os.path.join(self.prompt_dir, new_name)

        # 如果新名称的文件已存在，返回错误
        if os.path.exists(new_path) and new_path != old_path:
            raise ValueError(f"文件 '{new_name}' 已存在")

        # 重命名文件
        os.rename(old_path, new_path)
        return new_path

    def delete_prompt(self, path: str) -> bool:
        """删除已保存的 prompt"""
        if os.path.exists(path):
            os.remove(path)
            return True
        return False