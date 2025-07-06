import os
import re
import sys

import torch

# 推理用的指定模型
is_half_str = os.environ.get("is_half", "True")
is_half = True if is_half_str.lower() == "true" else False
is_share_str = os.environ.get("is_share", "False")
is_share = True if is_share_str.lower() == "true" else False


exp_root = "logs"
python_exec = sys.executable or "python"

webui_port_main = 9874
webui_port_uvr5 = 9873
webui_port_infer_tts = 9872
webui_port_subfix = 9871

api_port = 9880


def get_device_dtype_sm(idx: int) -> tuple[torch.device, torch.dtype, float, float]:
    cpu = torch.device("cpu")
    cuda = torch.device(f"cuda:{idx}")
    if not torch.cuda.is_available():
        return cpu, torch.float32, 0.0, 0.0
    device_idx = idx
    capability = torch.cuda.get_device_capability(device_idx)
    name = torch.cuda.get_device_name(device_idx)
    mem_bytes = torch.cuda.get_device_properties(device_idx).total_memory
    mem_gb = mem_bytes / (1024**3) + 0.4
    major, minor = capability
    sm_version = major + minor / 10.0
    is_16_series = bool(re.search(r"16\d{2}", name)) and sm_version == 7.5
    if mem_gb < 4 or sm_version < 5.3:
        return cpu, torch.float32, 0.0, 0.0
    if sm_version == 6.1 or is_16_series is True:
        return cuda, torch.float32, sm_version, mem_gb
    if sm_version > 6.1:
        return cuda, torch.float16, sm_version, mem_gb
    return cpu, torch.float32, 0.0, 0.0


IS_GPU = True
GPU_INFOS: list[str] = []
GPU_INDEX: set[int] = set()
GPU_COUNT = torch.cuda.device_count()
tmp: list[tuple[torch.device, torch.dtype, float, float]] = []
memset: set[float] = set()

for i in range(max(GPU_COUNT, 1)):
    tmp.append(get_device_dtype_sm(i))

for j in tmp:
    device = j[0]
    memset.add(j[3])
    if device.type != "cpu":
        GPU_INFOS.append(f"{device.index}\t{torch.cuda.get_device_name(device.index)}")
        GPU_INDEX.add(device.index)

infer_device = max(tmp, key=lambda x: (x[2], x[3]))[0]
is_half = any(dtype == torch.float16 for _, dtype, _, _ in tmp)
