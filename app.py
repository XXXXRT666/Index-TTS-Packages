import os,sys
if len(sys.argv)==1:sys.argv.append('v2')
version="v1"if sys.argv[1]=="v1" else"v2"
os.environ["version"]=version
now_dir = os.getcwd()
sys.path.insert(0, now_dir)
import warnings
warnings.filterwarnings("ignore")
import torch,re,shutil
import platform
import psutil
import traceback
from tools.common import check_for_existance, clean_path
from multiprocessing import cpu_count
import subprocess
from subprocess import Popen
import signal
from config import python_exec,infer_device,is_half,exp_root,webui_port_main,webui_port_infer_tts,webui_port_uvr5,webui_port_subfix,is_share
from tools.i18n.i18n import I18nAuto, scan_language_list
from tools.asr_rename import asr_and_rename_files

os.environ['TORCH_DISTRIBUTED_DEBUG'] = 'INFO'
torch.manual_seed(233333)
tmp = os.path.join(now_dir, "TEMP")
os.makedirs(tmp, exist_ok=True)
os.makedirs(os.path.join(now_dir, "WORKSPACE"), exist_ok=True)
os.makedirs(os.path.join(now_dir, "WORKSPACE","source"), exist_ok=True)
os.makedirs(os.path.join(now_dir, "WORKSPACE","denoise_opt"), exist_ok=True)
os.makedirs(os.path.join(now_dir, "WORKSPACE","asr_opt"), exist_ok=True)
os.makedirs(os.path.join(now_dir, "WORKSPACE","slicer_opt"), exist_ok=True)
os.environ["TEMP"] = tmp
if(os.path.exists(tmp)):
    for name in os.listdir(tmp):
        if(name=="jieba.cache"):continue
        path="%s/%s"%(tmp,name)
        delete=os.remove if os.path.isfile(path) else shutil.rmtree
        try:
            delete(path)
        except Exception as e:
            print(str(e))
            pass

#os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["no_proxy"] = "localhost, 127.0.0.1, ::1"
os.environ["all_proxy"] = ""

language=sys.argv[-1] if sys.argv[-1] in scan_language_list() else "zh_CN"
os.environ["language"]=language
i18n = I18nAuto(language=language)
print(language)
import gradio as gr
n_cpu=cpu_count()

ngpu = torch.cuda.device_count()
gpu_infos = []
mem = []
if_gpu_ok = False

# 判断是否有能用来训练和加速推理的N卡
ok_gpu_keywords={"10","16","20","30","40","A2","A3","A4","P4","A50","500","A60","70","80","90","M4","T4","TITAN","L4","4060","H","600","506","507","508","509"}
set_gpu_numbers=set()
if torch.cuda.is_available() or ngpu != 0:
    for i in range(ngpu):
        gpu_name = torch.cuda.get_device_name(i)
        print(gpu_name)
        if any(value in gpu_name.upper()for value in ok_gpu_keywords):
            # A10#A100#V100#A40#P40#M40#K80#A4500
            if_gpu_ok = True  # 至少有一张能用的N卡
            gpu_infos.append("%s\t%s" % (i, gpu_name))
            set_gpu_numbers.add(i)
            mem.append(int(torch.cuda.get_device_properties(i).total_memory/ 1024/ 1024/ 1024+ 0.4))
# 判断是否支持mps加速
if torch.backends.mps.is_available():
    if_gpu_ok = True
    gpu_infos.append("%s\t%s" % ("0", "Apple Silicon"))
    mem.append(psutil.virtual_memory().total/ 1024 / 1024 / 1024) # 实测使用系统内存作为显存不会爆显存
    set_gpu_numbers.add(0)

gpus = "-".join([i[0] for i in gpu_infos])

model_list = ['checkpoints/bigvgan_discriminator.pth',
              'checkpoints/bigvgan_generator.pth',
              'checkpoints/bpe.model',
              'checkpoints/dvae.pth',
              'checkpoints/gpt.pth',
              'checkpoints/unigram_12000.vocab'
              ]

def custom_sort_key(s):
    # 使用正则表达式提取字符串中的数字部分和非数字部分
    parts = re.split('(\d+)', s)
    # 将数字部分转换为整数，非数字部分保持不变
    parts = [int(part) if part.isdigit() else part for part in parts]
    return parts

def set_default():
    global default_batch_size,default_max_batch_size,gpu_info,default_sovits_epoch,default_sovits_save_every_epoch,max_sovits_epoch,max_sovits_save_every_epoch,default_batch_size_s1,if_force_ckpt
    if_force_ckpt = False
    if if_gpu_ok and len(gpu_infos) > 0:
        gpu_info = "\n".join(gpu_infos)
        minmem = min(mem)
        default_batch_size = minmem // 2 if version!="v3"else minmem//8
        default_batch_size_s1=minmem // 2
    else:
        gpu_info = ("%s\t%s" % ("0", "CPU"))
        gpu_infos.append("%s\t%s" % ("0", "CPU"))
        set_gpu_numbers.add(0)

set_default()

p_label=None
p_uvr5=None
p_asr=None
p_denoise=None
p_tts_inference=None

def kill_proc_tree(pid, including_parent=True):
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        # Process already terminated
        return

    children = parent.children(recursive=True)
    for child in children:
        try:
            os.kill(child.pid, signal.SIGTERM)  # or signal.SIGKILL
        except OSError:
            pass
    if including_parent:
        try:
            os.kill(parent.pid, signal.SIGTERM)  # or signal.SIGKILL
        except OSError:
            pass

system=platform.system()
def kill_process(pid, process_name=""):
    if(system=="Windows"):
        cmd = "taskkill /t /f /pid %s" % pid
        # os.system(cmd)
        subprocess.run(cmd,shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        kill_proc_tree(pid)
    print(process_name + i18n("进程已终止"))

def process_info(process_name="", indicator=""):
    if indicator == "opened":
        return process_name + i18n("已开启")
    elif indicator == "open":
        return i18n("开启") + process_name
    elif indicator == "closed":
        return process_name + i18n("已关闭")
    elif indicator == "close":
        return i18n("关闭") + process_name
    elif indicator == "running":
        return process_name + i18n("运行中")
    elif indicator == "occupy":
        return process_name + i18n("占用中") + "," + i18n("需先终止才能开启下一次任务")
    elif indicator == "finish":
        return process_name + i18n("已完成")
    elif indicator == "failed":
        return process_name + i18n("失败")
    elif indicator == "info":
        return process_name + i18n("进程输出信息")
    else:
        return process_name

process_name_uvr5 = i18n("人声分离WebUI")
def change_uvr5():
    global p_uvr5
    if p_uvr5 is None:
        cmd = 'PYTHONPATH=. "%s" tools/uvr5/webui.py "%s" %s %s %s'%(python_exec,infer_device,is_half,webui_port_uvr5,is_share)
        yield process_info(process_name_uvr5, "opened"), {'__type__':'update','visible':False}, {'__type__':'update','visible':True}
        print(cmd)
        p_uvr5 = Popen(cmd, shell=True)
    else:
        kill_process(p_uvr5.pid, process_name_uvr5)
        p_uvr5 = None
        yield process_info(process_name_uvr5, "closed"), {'__type__':'update','visible':True}, {'__type__':'update','visible':False}

process_name_tts = i18n("TTS推理WebUI")
def change_tts_inference():
    global p_tts_inference
    #####v3暂不支持加速推理
    cmd = 'PYTHONPATH=. "%s" indextts/inference_webui.py "%s"'%(python_exec, language)
    if p_tts_inference is None:
        os.environ["is_half"]=str(is_half)
        os.environ["infer_ttswebui"]=str(webui_port_infer_tts)
        os.environ["is_share"]=str(is_share)
        yield process_info(process_name_tts, "opened"), {'__type__':'update','visible':False}, {'__type__':'update','visible':True}
        print(cmd)
        p_tts_inference = Popen(cmd, shell=True)
    else:
        kill_process(p_tts_inference.pid, process_name_tts)
        p_tts_inference = None
        yield process_info(process_name_tts, "closed"), {'__type__':'update','visible':True}, {'__type__':'update','visible':False}

process_name_denoise = i18n("语音降噪")
def open_denoise(denoise_inp_dir, denoise_opt_dir):
    global p_denoise
    if(p_denoise==None):
        denoise_inp_dir=clean_path(denoise_inp_dir)
        denoise_opt_dir=clean_path(denoise_opt_dir)
        check_for_existance([denoise_inp_dir])
        cmd = 'PYTHONPATH=. "%s" tools/cmd-denoise.py -i "%s" -o "%s" -p %s'%(python_exec,denoise_inp_dir,denoise_opt_dir,"float16"if is_half==True else "float32")

        yield process_info(process_name_denoise, "opened"), {"__type__": "update", "visible": False}, {"__type__": "update", "visible": True}, {"__type__": "update"}, {"__type__": "update"}
        print(cmd)
        p_denoise = Popen(cmd, shell=True)
        p_denoise.wait()
        p_denoise=None
        yield process_info(process_name_denoise, "finish"), {"__type__": "update", "visible": True}, {"__type__": "update", "visible": False}, {"__type__": "update", "value": denoise_opt_dir}, {"__type__": "update", "value": denoise_opt_dir}
    else:
        yield process_info(process_name_denoise, "occupy"), {"__type__": "update", "visible": False}, {"__type__": "update", "visible": True}, {"__type__": "update"}, {"__type__": "update"}

def close_denoise():
    global p_denoise
    if p_denoise is not None:
        kill_process(p_denoise.pid, process_name_denoise)
        p_denoise = None
    return process_info(process_name_denoise, "closed"), {"__type__": "update", "visible": True}, {"__type__": "update", "visible": False}

ps_slice=[]
process_name_slice = i18n("语音切分")
def open_slice(inp,opt_root,threshold,min_length,min_interval,hop_size,max_sil_kept,_max,alpha,n_parts):
    global ps_slice
    inp = clean_path(inp)
    opt_root = clean_path(opt_root)
    check_for_existance([inp])
    if(os.path.exists(inp)==False):
        yield i18n("输入路径不存在"), {"__type__": "update", "visible": True}, {"__type__": "update", "visible": False}, {"__type__": "update"}, {"__type__": "update"}, {"__type__": "update"}
        return
    if os.path.isfile(inp):n_parts=1
    elif os.path.isdir(inp):pass
    else:
        yield i18n("输入路径存在但不可用"), {"__type__": "update", "visible": True}, {"__type__": "update", "visible": False}, {"__type__": "update"}, {"__type__": "update"}, {"__type__": "update"}
        return
    if (ps_slice == []):
        for i_part in range(n_parts):
            cmd = 'PYTHONPATH=. "%s" tools/slice_audio.py "%s" "%s" %s %s %s %s %s %s %s %s %s''' % (python_exec,inp, opt_root, threshold, min_length, min_interval, hop_size, max_sil_kept, _max, alpha, i_part, n_parts)
            print(cmd)
            p = Popen(cmd, shell=True)
            ps_slice.append(p)
        yield process_info(process_name_slice, "opened"), {"__type__": "update", "visible": False}, {"__type__": "update", "visible": True}, {"__type__": "update"}, {"__type__": "update"}, {"__type__": "update"}
        for p in ps_slice:
            p.wait()
        ps_slice=[]
        yield process_info(process_name_slice, "finish"), {"__type__": "update", "visible": True}, {"__type__": "update", "visible": False}, {"__type__": "update", "value": opt_root}, {"__type__": "update", "value": opt_root}, {"__type__": "update", "value": opt_root}
    else:
        yield process_info(process_name_slice, "occupy"), {"__type__": "update", "visible": False}, {"__type__": "update", "visible": True}, {"__type__": "update"}, {"__type__": "update"}, {"__type__": "update"}

def close_slice():
    global ps_slice
    if (ps_slice != []):
        for p_slice in ps_slice:
            try:
                kill_process(p_slice.pid, process_name_slice)
            except:
                traceback.print_exc()
        ps_slice=[]
    return process_info(process_name_slice, "closed"), {"__type__": "update", "visible": True}, {"__type__": "update", "visible": False}

if os.path.exists(os.path.join('checkpoints','gpt.pth')):...
else:
    cmd = 'PYTHONPATH=. "%s" tools/download_models.py'%python_exec
    p = Popen(cmd, shell=True)
    p.wait()

def sync(text):
    return {'__type__': 'update', 'value': text}


def update_path(explorer):
    return gr.update(value=explorer)


def toggle_path(explorer):
    if explorer:
        return gr.update(visible=False)
    else:
        return gr.update(visible=True)

with gr.Blocks(title="IndexTTS WebUI") as app:
    gr.Markdown(
        value=
            i18n("本软件以Apache License 2.0协议开源, 作者不对软件具备任何控制力, 使用软件者、传播软件导出的声音者自负全责.") + "<br>" +
            i18n("如不认可该条款, 则不能使用或引用软件包内任何代码和文件. 详见根目录LICENSE.")
    )
    gr.Markdown(
        value=i18n("鸣谢：IndexTTS")+": " + "https://github.com/index-tts/index-tts" + "<br>" +
            i18n("中文教程文档") + ": " + "(施工中)https://gey5xcecoh.feishu.cn/wiki/XIdTwghVdirBFPkOERsctFC7nnf" + "<br>" +
        i18n("作者")+": "+ "宇宙重女库瓦特罗" + "<br>" +
        i18n("IndexTTS交流QQ群") + ": " + "553460296"
    )

    with gr.Tabs():
        with gr.TabItem("0-"+i18n("prompt制作")):#提前随机切片防止uvr5爆内存->uvr5->slicer->asr->打标

            with gr.Accordion(label="0a-"+i18n("UVR5人声伴奏分离&去混响去延迟工具")):
                with gr.Row():
                    with gr.Column(scale=3):
                        with gr.Row():
                            uvr5_info = gr.Textbox(label=process_info(process_name_uvr5, "info"))
                    open_uvr5 = gr.Button(value=process_info(process_name_uvr5, "open"),variant="primary",visible=True)
                    close_uvr5 = gr.Button(value=process_info(process_name_uvr5, "close"),variant="primary",visible=False)

            with gr.Accordion(label="0b-"+i18n("语音切分工具")):
                with gr.Row():
                    with gr.Column(scale=3):
                        with gr.Row():
                            with gr.Column():
                                # with gr.Row():
                                slice_inp_path = gr.Textbox(label=i18n("填写音频自动切分输入路径，或在将文件放入项目根目录下的WORKSPACE后在下方选择"), interactive=True,value="")
                                    # slice_inp_btn = gr.Button(value=i18n("选择"), variant="primary", visible=True)
                                slice_inp_ex = gr.FileExplorer(label=i18n("填写音频自动切分输入路径，或在下方选择"), file_count="single", interactive=True,root_dir="WORKSPACE",visible=True)
                                slice_inp_ex.change(update_path, [slice_inp_ex], [slice_inp_path])
                                # slice_inp_btn.click(toggle_path, [slice_inp_ex], [slice_inp_ex])
                            with gr.Column():
                                slice_opt_root = gr.Textbox(label=i18n("切分后的子音频的输出根目录"), interactive=True,value="WORKSPACE/slicer_opt")
                                slice_opt_ex = gr.FileExplorer(label=i18n("切分后的子音频的输出根目录"), file_count="single", interactive=True,root_dir="WORKSPACE",visible=True)
                                slice_opt_ex.change(update_path, [slice_opt_ex], [slice_opt_root])
                        with gr.Row():
                            threshold=gr.Textbox(label=i18n("threshold:音量小于这个值视作静音的备选切割点"),value="-34",visible=False)
                            min_length=gr.Textbox(label=i18n("min_length:每段最小多长，如果第一段太短一直和后面段连起来直到超过这个值"),value="4000",visible=False)
                            min_interval=gr.Textbox(label=i18n("min_interval:最短切割间隔"),value="300",visible=False)
                            hop_size=gr.Textbox(label=i18n("hop_size:怎么算音量曲线，越小精度越大计算量越高（不是精度越大效果越好）"),value="10",visible=False)
                            max_sil_kept=gr.Textbox(label=i18n("max_sil_kept:切完后静音最多留多长"),value="500",visible=False)
                        with gr.Row():
                            _max=gr.Slider(minimum=0,maximum=1,step=0.05,label=i18n("max:归一化后最大值多少"),value=0.9,interactive=True,visible=False)
                            alpha=gr.Slider(minimum=0,maximum=1,step=0.05,label=i18n("alpha_mix:混多少比例归一化后音频进来"),value=0.25,interactive=True,visible=False)
                        with gr.Row():
                            n_process=gr.Slider(minimum=1,maximum=n_cpu,step=1,label=i18n("切割使用的进程数"),value=4,interactive=True,visible=False)
                            slicer_info = gr.Textbox(label=process_info(process_name_slice, "info"))
                    open_slicer_button = gr.Button(value=process_info(process_name_slice, "open"),variant="primary",visible=True)
                    close_slicer_button = gr.Button(value=process_info(process_name_slice, "close"),variant="primary",visible=False)

            gr.Markdown(value="0c-"+i18n("语音降噪工具"))
            with gr.Row():
                with gr.Column(scale=3):
                    with gr.Row():
                        denoise_input_dir=gr.Textbox(label=i18n("填写输入文件夹路径"),value="WORKSPACE/slicer_opt")
                        slice_inp_ex = gr.FileExplorer(label=i18n("请选择输入文件夹"),
                                                       file_count="single", interactive=True, root_dir="WORKSPACE/slicer_opt",
                                                       visible=True)
                        slice_inp_ex.change(update_path, [slice_inp_ex], [denoise_input_dir])
                        denoise_output_dir=gr.Textbox(label=i18n("填写输出文件夹路径"),value="WORKSPACE/denoise_opt")
                    with gr.Row():
                        denoise_info = gr.Textbox(label=process_info(process_name_denoise, "info"))
                open_denoise_button = gr.Button(value=process_info(process_name_denoise, "open"),variant="primary",visible=True)
                close_denoise_button = gr.Button(value=process_info(process_name_denoise, "close"),variant="primary",visible=False)


            open_uvr5.click(change_uvr5, [], [uvr5_info,open_uvr5,close_uvr5])
            close_uvr5.click(change_uvr5, [], [uvr5_info,open_uvr5,close_uvr5])
            open_slicer_button.click(open_slice, [slice_inp_path,slice_opt_root,threshold,min_length,min_interval,hop_size,max_sil_kept,_max,alpha,n_process], [slicer_info,open_slicer_button,close_slicer_button,denoise_input_dir])
            close_slicer_button.click(close_slice, [], [slicer_info,open_slicer_button,close_slicer_button])
            open_denoise_button.click(open_denoise, [denoise_input_dir,denoise_output_dir], [denoise_info,open_denoise_button,close_denoise_button])
            close_denoise_button.click(close_denoise, [], [denoise_info,open_denoise_button,close_denoise_button])
        with gr.TabItem("1-"+i18n("TTS推理")):
            with gr.Row():
                open_tts = gr.Button(value=process_info(process_name_tts, "open"), variant='primary', visible=True)
                close_tts = gr.Button(value=process_info(process_name_tts, "close"), variant='primary', visible=False)
            with gr.Row():
                tts_info = gr.Textbox(label=process_info(process_name_tts, "info"))
            open_tts.click(change_tts_inference,
                           [], [tts_info, open_tts, close_tts])
            close_tts.click(change_tts_inference,
                            [], [tts_info, open_tts, close_tts])

    app.queue().launch(#concurrency_count=511, max_size=1022
        server_name="0.0.0.0",
        inbrowser=True,
        share=is_share,
        server_port=webui_port_main,
        quiet=True,
    )
