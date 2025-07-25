import logging
import os
import shutil
import traceback

import gradio as gr
from modelscope import snapshot_download

from tools.common import clean_path, list_root_directories
from tools.i18n.i18n import I18nAuto

i18n = I18nAuto()

logger = logging.getLogger(__name__)
import sys

import ffmpeg
import librosa
import soundfile as sf
import torch
from bsroformer import Roformer_Loader
from mdxnet import MDXNetDereverb
from vr import AudioPre, AudioPreDeEcho

weight_uvr5_root = "tools/uvr5/uvr5_weights"
# snapshot_download("mirror013/GPT-SoVits-uvr5-weight",local_dir=weight_uvr5_root)
uvr5_names = []
for name in os.listdir(weight_uvr5_root):
    if name.endswith(".pth") or name.endswith(".ckpt") or "onnx" in name:
        uvr5_names.append(name.replace(".pth", "").replace(".ckpt", ""))

device = sys.argv[1]
is_half = eval(sys.argv[2])
webui_port_uvr5 = int(sys.argv[3])
is_share = eval(sys.argv[4])


def html_left(text, label="p"):
    return f"""<div style="text-align: left; margin: 0; padding: 0;">
                <{label} style="margin: 0; padding: 0;">{text}</{label}>
                </div>"""


def html_center(text, label="p"):
    return f"""<div style="text-align: center; margin: 100; padding: 50;">
                <{label} style="margin: 0; padding: 0;">{text}</{label}>
                </div>"""


def ensure_dirs_exist():
    """确保必要的目录存在，如果不存在则创建"""
    dirs = ["WORKSPACE", "WORKSPACE/source", "WORKSPACE/output/uvr5_opt"]
    for dir_path in dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
    return "WORKSPACE/source"


# 修改 wav_inputs 相关代码
def save_uploaded_files(files):
    """将上传的文件保存到 WORKSPACE/input 目录"""
    ensure_dirs_exist()
    saved_paths = []
    for file in files:
        if file is not None:
            file_path = os.path.join("WORKSPACE", "source", os.path.basename(file.name))
            shutil.copy(file.name, file_path)
            saved_paths.append(file_path)
    return saved_paths


def save_file_update_explorer(files):
    ensure_dirs_exist()
    for file in files:
        if file is not None:
            file_path = os.path.join("WORKSPACE", "source", os.path.basename(file.name))
            shutil.copy(file.name, file_path)
    return gr.update(value=os.path.join("WORKSPACE", "source"))


def ensure_dir(path):
    if os.path.isfile(path):
        gr.Warning(i18n("请选择文件夹，不支持单文件"))
        return None
    if os.path.isdir(path):
        return path


def uvr(model_name, dir_wav_input, save_root_vocal, wav_inputs, save_root_ins, agg, format0):
    # 确保目录存在
    ensure_dirs_exist()

    # 如果有上传文件且没有指定输入目录，则使用上传的文件
    if wav_inputs and not dir_wav_input.strip():
        # 保存上传的文件到 WORKSPACE/input
        saved_paths = save_uploaded_files(wav_inputs)
        paths = saved_paths
        # 将目录设置为 WORKSPACE/input
        inp_root = os.path.join("WORKSPACE", "source")
    else:
        inp_root = dir_wav_input
        paths = wav_inputs

    infos = []
    try:
        inp_root = clean_path(inp_root)
        save_root_vocal = clean_path(save_root_vocal)
        save_root_ins = clean_path(save_root_ins)
        is_hp3 = "HP3" in model_name
        if model_name == "onnx_dereverb_By_FoxJoy":
            pre_fun = MDXNetDereverb(15)
        elif "roformer" in model_name.lower():
            func = Roformer_Loader
            pre_fun = func(
                model_path=os.path.join(weight_uvr5_root, model_name + ".ckpt"),
                config_path=os.path.join(weight_uvr5_root, model_name + ".yaml"),
                device=device,
                is_half=is_half,
            )
            if not os.path.exists(os.path.join(weight_uvr5_root, model_name + ".yaml")):
                infos.append(
                    "Warning: You are using a model without a configuration file. The program will automatically use the default configuration file. However, the default configuration file cannot guarantee that all models will run successfully. You can manually place the model configuration file into 'tools/uvr5/uvr5w_weights' and ensure that the configuration file is named as '<model_name>.yaml' then try it again. (For example, the configuration file corresponding to the model 'bs_roformer_ep_368_sdr_12.9628.ckpt' should be 'bs_roformer_ep_368_sdr_12.9628.yaml'.) Or you can just ignore this warning."
                )
                yield "\n".join(infos)
        else:
            func = AudioPre if "DeEcho" not in model_name else AudioPreDeEcho
            pre_fun = func(
                agg=int(agg),
                model_path=os.path.join(weight_uvr5_root, model_name + ".pth"),
                device=device,
                is_half=is_half,
            )
        if inp_root != "":
            paths = [os.path.join(inp_root, name) for name in os.listdir(inp_root)]
        else:
            paths = [path.name for path in paths]
        for path in paths:
            inp_path = os.path.join(inp_root, path)
            ext = os.path.splitext(inp_path)[-1].lower()
            if ext not in [".wav", ".mp3", ".flac", ".m4a", "mp4"]:
                infos.append(f"{os.path.basename(inp_path)}->Unsupported file format")
                continue
            if os.path.isfile(inp_path) == False:
                continue
            need_reformat = 1
            done = 0
            try:
                info = ffmpeg.probe(inp_path, cmd="ffprobe")
                if info["streams"][0]["channels"] == 2 and info["streams"][0]["sample_rate"] == "44100":
                    need_reformat = 0
                    pre_fun._path_audio_(inp_path, save_root_ins, save_root_vocal, format0, is_hp3)
                    done = 1
            except:
                need_reformat = 1
                traceback.print_exc()
            if need_reformat == 1:
                tmp_path = "%s/%s.reformatted.wav" % (
                    os.path.join(os.environ["TEMP"]),
                    os.path.basename(inp_path),
                )
                os.system(f'ffmpeg -i "{inp_path}" -vn -acodec pcm_s16le -ac 2 -ar 44100 "{tmp_path}" -y')
                inp_path = tmp_path
            try:
                if done == 0:
                    pre_fun._path_audio_(inp_path, save_root_ins, save_root_vocal, format0, is_hp3)
                infos.append("%s->Success" % (os.path.basename(inp_path)))
                yield "\n".join(infos)
            except:
                infos.append("%s->%s" % (os.path.basename(inp_path), traceback.format_exc()))
                yield "\n".join(infos)
    except:
        print(traceback.format_exc())
        infos.append(traceback.format_exc())
        yield "\n".join(infos)
    finally:
        try:
            if model_name == "onnx_dereverb_By_FoxJoy":
                del pre_fun.pred.model
                del pre_fun.pred.model_
            else:
                del pre_fun.model
                del pre_fun
        except:
            traceback.print_exc()
        print("clean_empty_cache")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    yield "\n".join(infos)


# 修改 but2.click 部分，在调用 uvr 函数前处理上传的文件
def process_inputs(model_choose, dir_wav_input, opt_vocal_root, wav_inputs, opt_ins_root, agg, format0):
    # 调用原来的 uvr 函数
    return next(uvr(model_choose, dir_wav_input, opt_vocal_root, wav_inputs, opt_ins_root, agg, format0))


with gr.Blocks(title="UVR5 WebUI", analytics_enabled=False) as app:
    gr.Markdown(
        value=i18n(
            "本软件以Apache License 2.0协议开源, 作者不对软件具备任何控制力, 使用软件者、传播软件导出的声音者自负全责."
        )
        + "<br>"
        + i18n("如不认可该条款, 则不能使用或引用软件包内任何代码和文件. 详见根目录LICENSE.")
    )
    with gr.Group():
        gr.Markdown(html_center(i18n("伴奏人声分离&去混响&去回声"), "h2"))
        with gr.Group():
            gr.Markdown(
                value=html_left(
                    i18n("人声伴奏分离批量处理， 使用UVR5模型。")
                    + "<br>"
                    + i18n(
                        "合格的文件夹路径格式举例： E:\\codes\\py39\\vits_vc_gpu\\白鹭霜华测试样例(去文件管理器地址栏拷就行了)。"
                    )
                    + "<br>"
                    + i18n("模型分为三类：")
                    + "<br>"
                    + i18n("1、保留人声：不带和声的音频选这个,内置BS_Roformer模型和HP2模型；")
                    + "<br>"
                    + i18n("2、仅保留主人声：带和声的音频选这个，对主人声可能有削弱。内置HP5一个模型；")
                    + "<br>"
                    + i18n("3、去混响、去延迟模型（by FoxJoy）：")
                    + "<br>  "
                    + i18n("(1)MDX-Net(onnx_dereverb):对于双通道混响是最好的选择，不能去除单通道混响；")
                    + "<br>&emsp;"
                    + i18n(
                        "(234)DeEcho:去除延迟效果。Aggressive比Normal去除得更彻底，DeReverb额外去除混响，可去除单声道混响，但是对高频重的板式混响去不干净。"
                    )
                    + "<br>"
                    + i18n("去混响/去延迟，附：")
                    + "<br>"
                    + i18n("1、DeEcho-DeReverb模型的耗时是另外2个DeEcho模型的接近2倍；")
                    + "<br>"
                    + i18n("3、个人推荐的最干净的配置是先BS_Roformer再DeEcho-Aggressive。"),
                    "h4",
                )
            )
            with gr.Row():
                with gr.Column():
                    model_choose = gr.Dropdown(label=i18n("模型"), choices=uvr5_names, value="HP5_only_main_vocal")
                    dir_wav_input = gr.Textbox(
                        label=i18n("输入待处理音频文件夹路径"),
                        placeholder="WORKSPACE/source",
                        show_copy_button=True,
                    )
                    input_explorer = gr.FileExplorer(
                        root_dir="WORKSPACE",
                        label=i18n("选择文件夹"),
                        file_count="single",
                        ignore_glob="**/.*",
                    )
                    wav_inputs = gr.File(
                        file_count="multiple",
                        label=i18n("也可选择上传文件，优先读文件夹"),
                    )
                    input_explorer.change(ensure_dir, inputs=input_explorer, outputs=dir_wav_input)
                with gr.Column():
                    agg = gr.Slider(
                        minimum=0,
                        maximum=20,
                        step=1,
                        label=i18n("人声提取激进程度"),
                        value=10,
                        interactive=True,
                        visible=False,  # 先不开放调整
                    )
                    opt_vocal_root = gr.Textbox(label=i18n("指定输出主人声文件夹"), value="WORKSPACE/uvr5_opt")
                    opt_ins_root = gr.Textbox(label=i18n("指定输出非主人声文件夹"), value="WORKSPACE/uvr5_opt")
                    format0 = gr.Radio(
                        label=i18n("导出文件格式"),
                        choices=["wav", "flac", "mp3", "m4a"],
                        value="flac",
                        interactive=True,
                    )
                    with gr.Column():
                        with gr.Row():
                            but2 = gr.Button(i18n("转换"), variant="primary")
                        with gr.Row():
                            vc_output4 = gr.Textbox(label=i18n("输出信息"), lines=3)
                wav_inputs.upload(save_file_update_explorer, inputs=[wav_inputs], outputs=dir_wav_input)
                but2.click(
                    uvr,
                    [
                        model_choose,
                        dir_wav_input,
                        opt_vocal_root,
                        wav_inputs,
                        opt_ins_root,
                        agg,
                        format0,
                    ],
                    [vc_output4],
                    api_name="uvr_convert",
                )
app.queue().launch(  # concurrency_count=511, max_size=1022
    server_name="0.0.0.0",
    inbrowser=True,
    share=is_share,
    server_port=webui_port_uvr5,
    quiet=True,
    allowed_paths=list_root_directories(),
    show_api=False,
)
