from typing import Iterable

import gradio.themes.base as ThemeBase
from gradio.themes.utils import colors, fonts, sizes


class Seafoam(ThemeBase.Base):
    def __init__(
        self,
        *,
        primary_hue: colors.Color | str = colors.emerald,
        secondary_hue: colors.Color | str = colors.blue,
        neutral_hue: colors.Color | str = colors.blue,
        spacing_size: sizes.Size | str = sizes.spacing_md,
        radius_size: sizes.Size | str = sizes.radius_md,
        text_size: sizes.Size | str = sizes.text_lg,
        font: fonts.Font | str | Iterable[fonts.Font | str] = (
            "Menlo",
            "Consolas",
            fonts.GoogleFont("Quicksand"),
            "ui-sans-serif",
            "sans-serif",
        ),
        font_mono: fonts.Font | str | Iterable[fonts.Font | str] = (
            "Menlo",
            "Consolas",
            fonts.GoogleFont("Quicksand"),
            "ui-sans-serif",
            "sans-serif",
        ),
    ):
        super().__init__(
            primary_hue=primary_hue,
            secondary_hue=secondary_hue,
            neutral_hue=neutral_hue,
            spacing_size=spacing_size,
            radius_size=radius_size,
            text_size=text_size,
            font=font,
            font_mono=font_mono,
        )
        super().set(
            # Light
            body_background_fill="linear-gradient(45deg,rgb(128, 238, 238),rgb(200, 240, 230))",  # 浅色模式背景渐变
            button_secondary_background_fill_hover="rgb(169, 208, 254)",
            button_primary_background_fill="linear-gradient(90deg, *primary_200, *secondary_200)",
            button_primary_background_fill_hover="linear-gradient(90deg,rgb(153, 240, 202),rgb(169, 208, 254))",
            button_primary_text_color="black",
            button_cancel_background_fill="rgb(255, 166, 166)",
            button_cancel_background_fill_hover="rgb(255, 134, 134)",
            slider_color="*secondary_300",
            block_title_text_weight="500",
            block_border_width="3px",
            block_shadow="*shadow_drop_lg",
            button_primary_shadow="*shadow_drop_lg",
            button_large_padding="32px",
            button_large_text_weight="500",
        )


js = r"""
function createGradioAnimation() {
    
    const params = new URLSearchParams(window.location.search);
    if (params.has('__theme')) {
        params.delete('__theme');
        const newUrl = `${window.location.pathname}?${params.toString()}`;
        window.location.replace(newUrl);
    }
    
    var container = document.createElement('div');
    container.id = 'gradio-animation';
    container.style.fontSize = '2em';
    container.style.fontWeight = '500';
    container.style.textAlign = 'center';
    container.style.marginTop = '5px';
    container.style.marginBottom = '-5px';
    container.style.fontFamily = '-apple-system, sans-serif, Arial, Calibri';

    var text = 'Welcome to Index-TTS !';
    for (var i = 0; i < text.length; i++) {
        (function(i){
            setTimeout(function(){
                var letter = document.createElement('span');
                letter.style.opacity = '0';
                letter.style.transition = 'opacity 0.5s';
                letter.innerText = text[i];

                container.appendChild(letter);

                setTimeout(function() {
                    letter.style.opacity = '1';
                }, 50);
            }, i * 250);
        })(i);
    }

    var gradioContainer = document.querySelector('.gradio-container');
    gradioContainer.insertBefore(container, gradioContainer.firstChild);

    return 'Animation created';
}
"""


css = """
/* CSSStyleRule */

.markdown {
    padding: 10px;
}

@media (prefers-color-scheme: light) {
    .markdown {
        background-color: lightblue;
        color: #000;
    }
}

@media (prefers-color-scheme: dark) {
    .markdown {
        background-color: #4b4b4b;
        color: rgb(244, 244, 245);
    }
}

::selection {
    background: #ffc078 !important;
}

footer {
    height: 50px !important;
    background-color: transparent !important;
    display: flex;
    justify-content: center;
    align-items: center;
}

footer * {
    display: none !important;
}

"""
top_html = """
<div align="center">
    <div style="margin-bottom: 20px; font-size: 20px;">{}</div>
    <div style="display: flex; gap: 30px; justify-content: center;">
        <a href="https://github.com/index-tts/index-tts" target="_blank">
            <img src="https://img.shields.io/badge/GitHub-Index%20TTS-blue.svg?style=for-the-badge&logo=github" style="width: auto; height: 40px;">
        </a>
        <a href="https://gey5xcecoh.feishu.cn/wiki/XIdTwghVdirBFPkOERsctFC7nnf" target="_blank">
            <img src="https://img.shields.io/badge/简体中文-阅读文档-blue?style=for-the-badge&logo=googledocs&logoColor=white" style="width: auto; height: 40px;">
        </a>
        <a href="https://github.com/index-tts/index-tts/blob/main/LICENSE" target="_blank">
            <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=for-the-badge&logo=apache" style="width: auto; height: 40px;">
        </a>
        <a href="https://github.com/index-tts/index-tts/blob/main/INDEX_MODEL_LICENSE" target="_blank">
            <img src="https://img.shields.io/badge/Model%20License-Non--Commercial-blue?style=for-the-badge&logo=creative-commons&logoColor=white" style="width: auto; height: 40px;">
        </a>
    </div>
</div>
"""


uvr5_html = """
<div align="center">
    <div style="margin-bottom: 10px; font-size: 20px;">{}</div>
</div>
<div>
    <p style="font-size: 18px;">{}</p>
</div>
"""
