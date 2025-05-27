
import logging
import subprocess
import torchaudio,warnings

logging.getLogger("markdown_it").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("asyncio").setLevel(logging.ERROR)
logging.getLogger("charset_normalizer").setLevel(logging.ERROR)
logging.getLogger("torchaudio._extension").setLevel(logging.ERROR)
logging.getLogger("multipart.multipart").setLevel(logging.ERROR)
warnings.simplefilter(action='ignore', category=FutureWarning)

import os, re, sys
import torch
from time import time as ttime
from tools.i18n.i18n import I18nAuto, scan_language_list
from indextts.infer import IndexTTS
import gradio as gr
import numpy as np
import random

tts = IndexTTS(model_dir="checkpoints",cfg_path="checkpoints/config.yaml")
device = tts.device
try:
    import gradio.analytics as analytics
    analytics.version_check = lambda:None
except:...
version=model_version=os.environ.get("version","v2")

infer_ttswebui = os.environ.get("infer_ttswebui", 9872)
infer_ttswebui = int(infer_ttswebui)
is_share = os.environ.get("is_share", "False")
is_share = eval(is_share)
if "_CUDA_VISIBLE_DEVICES" in os.environ:
    os.environ["CUDA_VISIBLE_DEVICES"] = os.environ["_CUDA_VISIBLE_DEVICES"]
is_half = eval(os.environ.get("is_half", "True")) and torch.cuda.is_available()
# is_half=False
punctuation = set(['!', '?', '…', ',', '.', '-'," "])

def set_seed(seed):
    if seed == -1:
        seed = random.randint(0, 1000000)
    seed = int(seed)
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
# set_seed(42)

language=os.environ.get("language","zh_CN")
language=sys.argv[-1] if sys.argv[-1] in scan_language_list() else language
i18n = I18nAuto(language=language)

# os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'  # 确保直接启动推理UI时也能够设置。

os.environ["HF_ENDPOINT"]          = "https://hf-mirror.com"

now_dir = os.getcwd()
splits = {"，", "。", "？", "！", ",", ".", "?", "!", "~", ":", "：", "—", "…", }

def merge_short_text_in_array(texts, threshold):
    if (len(texts)) < 2:
        return texts
    result = []
    text = ""
    for ele in texts:
        text += ele
        if len(text) >= threshold:
            result.append(text)
            text = ""
    if (len(text) > 0):
        if len(result) == 0:
            result.append(text)
        else:
            result[len(result) - 1] += text
    return result

##ref_wav_path+prompt_text+prompt_language+text(单个)+text_language+top_k+top_p+temperature
# cache_tokens={}#暂未实现清理机制
cache= {}
def get_tts_wav(ref_wav_path, text,index,output_dir):
    global cache
    if ref_wav_path:pass
    else:gr.Warning(i18n('请选择参考音频'))
    if text:pass
    else:gr.Warning(i18n('请填入推理文本'))
    os.makedirs(output_dir, exist_ok=True)
    t = []

    t0 = ttime()

    text = text.strip("\n")
    index = int(index)
    output_path = os.path.join(output_dir, f"{index:04d}-{text[:20]}.wav")

    # if (text[0] not in splits and len(get_first(text)) < 4): text = "。" + text if text_language != "en" else "." + text

    print(i18n("实际输入的目标文本:"), text)

    t1 = ttime()
    t.append(t1-t0)

    while "\n\n" in text:
        text = text.replace("\n\n", "\n")
    print(i18n("实际输入的目标文本(切句后):"), text)
    tts.infer(ref_wav_path,text,output_path)

    return gr.update(value=output_path)


def split(todo_text):
    todo_text = todo_text.replace("……", "。").replace("——", "，")
    if todo_text[-1] not in splits:
        todo_text += "。"
    i_split_head = i_split_tail = 0
    len_text = len(todo_text)
    todo_texts = []
    while 1:
        if i_split_head >= len_text:
            break  # 结尾一定有标点，所以直接跳出即可，最后一段在上次已加入
        if todo_text[i_split_head] in splits:
            i_split_head += 1
            todo_texts.append(todo_text[i_split_tail:i_split_head])
            i_split_tail = i_split_head
        else:
            i_split_head += 1
    return todo_texts


def cut1(inp):
    inp = inp.strip("\n")
    inps = split(inp)
    split_idx = list(range(0, len(inps), 4))
    split_idx[-1] = None
    if len(split_idx) > 1:
        opts = []
        for idx in range(len(split_idx) - 1):
            opts.append("".join(inps[split_idx[idx]: split_idx[idx + 1]]))
    else:
        opts = [inp]
    opts = [item for item in opts if (not set(item).issubset(punctuation) and not item == '\n')]
    return "\n".join(opts)


def cut2(inp):
    inp = inp.strip("\n")
    inps = split(inp)
    if len(inps) < 2:
        return inp
    opts = []
    summ = 0
    tmp_str = ""
    for i in range(len(inps)):
        summ += len(inps[i])
        tmp_str += inps[i]
        if summ > 50:
            summ = 0
            opts.append(tmp_str)
            tmp_str = ""
    if tmp_str != "":
        opts.append(tmp_str)
    # print(opts)
    if len(opts) > 1 and len(opts[-1]) < 50:  ##如果最后一个太短了，和前一个合一起
        opts[-2] = opts[-2] + opts[-1]
        opts = opts[:-1]
    opts = [item for item in opts if (not set(item).issubset(punctuation) and not item == '\n')]
    return "\n".join(opts)


def cut3(inp):
    inp = inp.strip("\n")
    opts = ["%s" % item for item in inp.strip("。").split("。")]
    opts = [item for item in opts if (not set(item).issubset(punctuation) and not item == '\n')]
    return  "\n".join(opts)

def cut4(inp):
    inp = inp.strip("\n")
    opts = re.split(r'(?<!\d)\.(?!\d)', inp.strip("."))
    opts = [item for item in opts if (not set(item).issubset(punctuation) and not item == '\n')]
    return "\n".join(opts)


# contributed by https://github.com/AI-Hobbyist/GPT-SoVITS/blob/main/GPT_SoVITS/inference_webui.py
def cut5(inp):
    inp = inp.strip("\n")
    punds = {',', '.', ';', '?', '!', '、', '，', '。', '？', '！', ';', '：', '…'}
    mergeitems = []
    items = []

    for i, char in enumerate(inp):
        if char in punds:
            if char == '.' and i > 0 and i < len(inp) - 1 and inp[i - 1].isdigit() and inp[i + 1].isdigit():
                items.append(char)
            else:
                items.append(char)
                mergeitems.append("".join(items))
                items = []
        else:
            items.append(char)

    if items:
        mergeitems.append("".join(items))

    opt = [item for item in mergeitems if (not set(item).issubset(punds) and not item == '\n')]
    return "\n".join(opt)

def split_text(full_text,how_to_cut):
    if (how_to_cut == i18n("凑四句一切")):
        text = cut1(full_text)
    elif (how_to_cut == i18n("凑50字一切")):
        text = cut2(full_text)
    elif (how_to_cut == i18n("按中文句号。切")):
        text = cut3(full_text)
    elif (how_to_cut == i18n("按英文句号.切")):
        text = cut4(full_text)
    elif (how_to_cut == i18n("按标点符号切")):
        text = cut5(full_text)
    else:
        text = full_text
    text = re.sub('[\n]+', '\n', text)
    lines = text.split("\n")
    start = 0
    end = min(9,len(lines))
    have_next=True
    if end < 9:
        have_next=False
    return text,lines,gr.update(interactive=False),gr.update(interactive=have_next),start,end

def update_text(full_text):
    lines = full_text.split("\n")
    start = 0
    end = min(9, len(lines))
    have_next = True
    if end < 9:
        have_next = False
    return full_text, lines, gr.update(interactive=False), gr.update(interactive=have_next), start, end

def custom_sort_key(s):
    # 使用正则表达式提取字符串中的数字部分和非数字部分
    parts = re.split('(\d+)', s)
    # 将数字部分转换为整数，非数字部分保持不变
    parts = [int(part) if part.isdigit() else part for part in parts]
    return parts

def html_center(text, label='p'):
    return f"""<div style="text-align: center; margin: 100; padding: 50;">
                <{label} style="margin: 0; padding: 0;">{text}</{label}>
                </div>"""

def html_left(text, label='p'):
    return f"""<div style="text-align: left; margin: 0; padding: 0;">
                <{label} style="margin: 0; padding: 0;">{text}</{label}>
                </div>"""

def load_prompt(prompt_dir):
    if not os.path.exists(prompt_dir):
        os.makedirs(prompt_dir)
    prompt_list = []
    for file in os.listdir(prompt_dir):
        if file.lower().endswith(".wav"):
            prompt_list.append(file)
    prompt_list.sort(key=custom_sort_key)
    return prompt_list

def next_page(id_start,id_end,batch_size,df):
    id_start = int(id_start)
    id_end = int(id_end)
    batch_size = int(batch_size)
    id_start += batch_size
    id_end = batch_size + id_start - 1
    id_end = min(id_end, len(df.values)-1)
    have_next = True
    if id_end >= len(df.values) - 1:
        have_next = False
    return gr.update(interactive=True), gr.update(interactive=have_next), \
            id_start, id_end

def prev_page(id_start,id_end,batch_size,df):
    id_start = int(id_start)
    id_end = int(id_end)
    batch_size = int(batch_size)
    id_start -= batch_size
    id_end = batch_size + id_start - 1
    id_start = max(id_start, 0)
    id_end = min(id_end, len(df.values)-1)
    have_prev = True
    if id_start <= 0:
        have_prev = False
    return gr.update(interactive=have_prev), gr.update(interactive=True), \
            id_start, id_end

def ensure_dir(path):
    if os.path.isfile(path):
        gr.Warning(i18n("请选择文件夹，不支持单文件"))
        return None,None
    if os.path.isdir(path):
        return path,path+"_gen"

def update_audio(input_dir,audio_name):
    target_path = os.path.join(input_dir,audio_name)
    return gr.update(value=target_path)


def open_finder():
    """
    跨平台打开系统文件管理器

    Args:
        path: 要打开的���件夹路径

    Returns:
        None
    """
    path="WORKSPACE"
    if not os.path.exists(path):
        gr.Warning(i18n("路径不存在，请检查路径是否正确"))
        return

    if not os.path.isdir(path):
        # 如果是文件，则打开其所在目录
        path = os.path.dirname(path)

    system = sys.platform

    try:
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", path])
        else:  # Linux
            # 尝试常见的文件管理器
            for opener in ["xdg-open", "nautilus", "dolphin", "thunar", "pcmanfm", "caja"]:
                try:
                    subprocess.run([opener, path], check=False)
                    break
                except FileNotFoundError:
                    continue
    except Exception as e:
        gr.Warning(i18n(f"打开文件管理器失败: {str(e)}"))


with gr.Blocks(title="Index-TTS Editor") as app:
    gr.Markdown(
        value=i18n("本软件以Apache License 2.0协议开源, 作者不对软件具备任何控制力, 使用软件者、传播软件导出的声音者自负全责.") + "<br>" + i18n("如不认可该条款, 则不能使用或引用软件包内任何代码和文件. 详见根目录LICENSE.")
    )
    with gr.Group():
        with gr.Row():
            with gr.Column():
                inp_dir = gr.Textbox(label=i18n("参考音频目录"), value="WORKSPACE/output/denoise_opt",
                                     placeholder=i18n("填写参考音频文件所在的文件夹地址，或将文件放入项目根目录下的WORKSPACE文件夹后在下方选择"),
                                     interactive=True,show_copy_button=True)
                inp_explorer = gr.FileExplorer(label=i18n("打开文件浏览器"), interactive=True,value="WORKSPACE/output/denoise_opt",
                                               file_count="single",root_dir="WORKSPACE")
        #     with gr.Column(scale=7):
        #         open_finder_btn = gr.Button(i18n("打开系统文件管理器"), variant="primary")
        # open_finder_btn.click(open_finder,inputs=[],outputs=[])
            #     inp_ref = gr.Audio(label=i18n("请上传3~10秒内参考音频，超过会报错！"), type="filepath", scale=7)
        out_dir = gr.Textbox(label=i18n("输出音频目录"), value="", interactive=True,
                             placeholder=i18n("输入输出音频文件的目录路径"))
        inp_explorer.change(ensure_dir, inputs=inp_explorer, outputs=[inp_dir, out_dir])
        # load_prompts_btn = gr.Button(i18n("加载参考音频"), variant="primary")

        gr.Markdown(html_center(i18n("*请填写需要合成的目标文本"), 'h3'))
        with gr.Row():
            with gr.Column(scale=13):
                text = gr.Textbox(label=i18n("需要合成的文本"), value="", lines=26, max_lines=26)
            with gr.Column():
                cut_method_dropdown = gr.Dropdown(label=i18n("切分文本方法"),value=i18n("按标点符号切"),
                                                  choices=[i18n("凑四句一切"), i18n("凑50字一切"), i18n("按中文句号。切"), i18n("按英文句号.切"), i18n("按标点符号切")])
                cut_text_btn = gr.Button(i18n("切分文本"), variant="primary")
                load_text_btn = gr.Button(i18n("刷新文本&参考音频列表"), variant="primary")
                batch_size = gr.Slider(label=i18n("批处理大小"), value=10, minimum=1, maximum=10, step=1,visible=False)
                df_len = gr.Textbox(label=i18n("文本分句总数"), value="0", interactive=False)

        with gr.Row():
            df = gr.DataFrame(col_count=2, label=i18n("文本列表"), interactive=False,
                              show_row_numbers=True, visible=False)
            df.change(lambda x: len(x), inputs=df, outputs=[df_len], queue=False)
        with gr.Row(max_height=80):
            prev_page_btn = gr.Button(i18n("上一页"), variant="primary")
            id_start = gr.Textbox(value="0", label=i18n("最小序号"),interactive=False)
            id_end = gr.Textbox(value=f"{batch_size.value}", label=i18n("最大序号"),interactive=False)
            next_page_btn = gr.Button(i18n("下一页"), variant="primary")

        cut_text_btn.click(split_text, inputs=[text,cut_method_dropdown], outputs=[text, df,prev_page_btn,next_page_btn,id_start,id_end])
        next_page_btn.click(next_page, inputs=[id_start, id_end, batch_size, df],outputs=[prev_page_btn,next_page_btn,id_start,id_end])
        prev_page_btn.click(prev_page, inputs=[id_start, id_end, batch_size, df],outputs=[prev_page_btn,next_page_btn,id_start,id_end])
        load_text_btn.click(update_text, inputs=text, outputs=[text, df,prev_page_btn,next_page_btn,id_start,id_end])

        @gr.render(inputs=[df,id_start,id_end],
                   triggers=[df.change,id_start.change,load_text_btn.click],
                   queue=False,
                   concurrency_limit=1)
        def render_texts(df,id_start,id_end):
            if len(df.values) == 0:
                gr.Markdown("## No Input Provided", key="no_input")
            else:
                start = int(id_start)
                end = int(id_end)
                for i, input_ in enumerate(df.values):
                    # print(type(i))
                    if i < start:
                        continue
                    if i > end:
                        break
                    with gr.Row(max_height=200):
                        sentence_index = gr.Textbox(value=str(i), label="序号", interactive=False,
                                                    # key=f"index_{i}",
                                                    min_width=10)
                        with gr.Column():
                            sentence_text = gr.Textbox(value=input_[0],type="text",max_lines=3,
                                                       # key=f"text_{i}",
                                                       label="目标文本",interactive=False)
                            choices = load_prompt(inp_dir.value)
                            ref_selector = gr.Dropdown(label=i18n("选择参考音频"),
                                                           choices=choices,value=choices[0] if len(choices)>0 else None,)

                        default_prompt_path = os.path.join(inp_dir.value, choices[0]) if len(choices)>0 else None
                        if default_prompt_path:
                            ref_audio = gr.Audio(label=i18n("或者上传音频文件"), interactive=True,value=default_prompt_path,
                                                 type="filepath")
                        else:
                            ref_audio = gr.Audio(label=i18n("或者上传音频文件"), interactive=True,
                                                 type="filepath")

                        with gr.Column():
                            regen_button = gr.Button('生成音频',
                                                     key=f"regen_{i}", interactive=True,variant="primary",
                                                     )
                            target_path = f"{i:04d}-{input_[0][:20]}.wav"
                            if os.path.isfile(target_path):
                                audio = gr.Audio(label="生成结果",interactive=False,show_download_button=True,
                                                 type="filepath",value=target_path)
                            else:
                                audio = gr.Audio(label="生成结果",interactive=False, show_download_button=True,
                                                 type="filepath")

                        def gen_single(ref_path, text,index,out_dir):
                            return get_tts_wav(ref_path,text,index, out_dir)

                        ref_selector.select(update_audio, inputs=[inp_dir,ref_selector], outputs=ref_audio)

                        regen_button.click(gen_single,inputs=[ref_audio,sentence_text,sentence_index,out_dir],concurrency_limit=1,
                                                     concurrency_id="gpu_queue",
                                                              outputs=[audio])



if __name__ == '__main__':
    app.queue().launch(#concurrency_count=511, max_size=1022
        server_name="0.0.0.0",
        inbrowser=True,
        share=is_share,
        server_port=infer_ttswebui,
        quiet=True,
    )
