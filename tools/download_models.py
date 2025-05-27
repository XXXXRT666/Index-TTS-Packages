from modelscope import snapshot_download,model_file_download


snapshot_download("IndexTeam/Index-TTS",local_dir="checkpoints",
                  revision="v1.0.1")