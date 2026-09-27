# coding: utf-8
"""MLX 模型入口解析回归：用临时目录模拟全新检出与已下载状态，不触碰真实 models/。"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config_server import ModelPaths


# 本地目录都不可用时的兜底仓库 ID，与 resolve_qwen3_asr_mlx_model 的返回值一致。
HUB_FALLBACK = 'mlx-community/Qwen3-ASR-1.7B-4bit'
COMPLETE = ['.gitkeep', 'config.json', 'weights.safetensors']


def make_model_dir(root, name, files):
    """按文件名建空文件；解析只看文件是否存在，不读取内容。"""
    model_dir = Path(root) / name
    model_dir.mkdir()
    for file_name in files:
        (model_dir / file_name).touch()
    return model_dir


class ResolveQwen3ASRMLXModelTests(unittest.TestCase):
    """覆盖仓库占位 .gitkeep 导致空目录被误判的故障，以及 8bit→4bit→Hub 的回退顺序。"""

    def resolve(self, files_8bit, files_4bit):
        """返回 (解析结果, 8bit 路径, 4bit 路径)；只替换目录属性，函数本体照常走真实文件系统。"""
        with tempfile.TemporaryDirectory() as root:
            dir_8bit = make_model_dir(root, '8bit', files_8bit)
            dir_4bit = make_model_dir(root, '4bit', files_4bit)
            with patch.object(ModelPaths, 'qwen3_asr_mlx_8bit_dir', dir_8bit), \
                    patch.object(ModelPaths, 'qwen3_asr_mlx_4bit_dir', dir_4bit):
                result = ModelPaths.resolve_qwen3_asr_mlx_model()
            return result, dir_8bit.as_posix(), dir_4bit.as_posix()

    def test_placeholder_only_dirs_fall_back_to_hub(self):
        # 全新检出：两个目录只有仓库跟踪的 .gitkeep，旧逻辑会选中空的 8bit 目录。
        result, _, _ = self.resolve(['.gitkeep'], ['.gitkeep'])
        self.assertEqual(result, HUB_FALLBACK)

    def test_incomplete_dirs_are_not_treated_as_models(self):
        # 缺 config.json 时加载器会把路径当仓库 ID；缺权重时加载器找不到 safetensors。两种都不能选。
        for files in (['.gitkeep', 'config.json'], ['.gitkeep', 'weights.safetensors']):
            with self.subTest(files=files):
                result, _, _ = self.resolve(files, files)
                self.assertEqual(result, HUB_FALLBACK)

    def test_complete_8bit_is_preferred(self):
        result, dir_8bit, _ = self.resolve(COMPLETE, COMPLETE)
        self.assertEqual(result, dir_8bit)

    def test_placeholder_8bit_falls_back_to_local_4bit(self):
        # 4bit 用另一种权重文件名，确认判定跟随加载器的 *.safetensors 规则，不绑定单一文件名。
        result, _, dir_4bit = self.resolve(['.gitkeep'], ['.gitkeep', 'config.json', 'model.safetensors'])
        self.assertEqual(result, dir_4bit)


if __name__ == '__main__':
    unittest.main()
