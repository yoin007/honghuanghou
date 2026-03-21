#!/usr/bin/env python3
"""
二维码美化生成器 V3
优化版：更协调的比例、更简洁的设计

用法:
    python generate_qr.py --url "https://example.com" --title "扫码访问"
    python generate_qr.py --url "https://example.com" --title "标题" --subtitle "诚邀参与"
"""

import argparse
import os
import platform
import hashlib

try:
    import qrcode
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
    from qrcode.image.styles.colormasks import SolidFillColorMask
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError as e:
    print(f"缺少依赖: {e}")
    print("请安装: pip3 install qrcode[pil] pillow")
    exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """获取跨平台中文字体"""
    system = platform.system()

    font_paths = []
    if system == "Darwin":  # macOS
        font_paths = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
        ]
    elif system == "Windows":
        font_paths = [
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc",
        ]
    else:  # Linux
        font_paths = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/arphic/ukai.ttc",
        ]

    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue

    return ImageFont.load_default()


def create_qr_code(
    url: str,
    title: str = None,
    subtitle: str = None,
    logo_path: str = None,
    output_path: str = None,
    theme: str = "gradient",
    qr_size: int = 400,
) -> str:
    """
    生成美化二维码

    Args:
        url: 二维码链接
        title: 主标题
        subtitle: 副标题
        logo_path: Logo路径
        output_path: 输出路径
        theme: 主题 (gradient/elegant/warm)
        qr_size: 二维码尺寸

    Returns:
        输出文件路径
    """

    # 主题配置
    themes = {
        "gradient": {
            "name": "渐变紫蓝",
            "bg_color": (102, 126, 234),
            "bg_end": (118, 75, 162),
            "qr_color": (102, 126, 234),
            "text_color": (255, 255, 255),
            "card_bg": (255, 255, 255),
        },
        "elegant": {
            "name": "优雅深蓝",
            "bg_color": (30, 58, 138),
            "bg_end": (59, 130, 246),
            "qr_color": (59, 130, 246),
            "text_color": (255, 255, 255),
            "card_bg": (255, 255, 255),
        },
        "warm": {
            "name": "温暖橙红",
            "bg_color": (234, 88, 12),
            "bg_end": (251, 146, 60),
            "qr_color": (234, 88, 12),
            "text_color": (255, 255, 255),
            "card_bg": (255, 255, 255),
        },
    }

    config = themes.get(theme, themes["gradient"])

    # ========== 创建二维码 ==========
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # 创建纯色二维码
    color_mask = SolidFillColorMask(
        back_color=(255, 255, 255),
        front_color=config["qr_color"],
    )

    qr_img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        color_mask=color_mask,
    )

    qr_img = qr_img.get_image() if hasattr(qr_img, 'get_image') else qr_img
    qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
    if qr_img.mode != "RGBA":
        qr_img = qr_img.convert("RGBA")

    # 嵌入 Logo
    if logo_path and os.path.exists(logo_path):
        qr_img = add_logo(qr_img, logo_path, qr_size)

    # ========== 计算画布尺寸 ==========
    padding = 40  # 内边距
    card_radius = 20  # 卡片圆角

    # 标题区域高度
    title_height = 0
    if title:
        title_height = 50  # 主标题
        if subtitle:
            title_height += 30  # 副标题
        title_height += 20  # 间距

    # 画布尺寸
    canvas_width = qr_size + padding * 2
    canvas_height = qr_size + padding * 2 + title_height + 60  # 60 为底部提示区域

    # ========== 创建画布 ==========
    canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # ========== 渐变背景 ==========
    bg_start = config["bg_color"]
    bg_end = config["bg_end"]
    for y in range(canvas_height):
        ratio = y / canvas_height
        r = int(bg_start[0] + (bg_end[0] - bg_start[0]) * ratio)
        g = int(bg_start[1] + (bg_end[1] - bg_start[1]) * ratio)
        b = int(bg_start[2] + (bg_end[2] - bg_start[2]) * ratio)
        draw.line([(0, y), (canvas_width, y)], fill=(r, g, b, 255))

    # ========== 标题区域 ==========
    current_y = padding
    if title:
        # 主标题
        title_font = get_font(28, bold=True)
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (canvas_width - title_width) // 2
        draw.text((title_x, current_y), title, fill=config["text_color"], font=title_font)
        current_y += 45

        # 副标题
        if subtitle:
            sub_font = get_font(20)
            sub_bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
            sub_width = sub_bbox[2] - sub_bbox[0]
            sub_x = (canvas_width - sub_width) // 2
            draw.text((sub_x, current_y), subtitle, fill=config["text_color"], font=sub_font)
            current_y += 35

        current_y += 15  # 标题与二维码间距

    # ========== 二维码白色卡片背景 ==========
    card_x = padding
    card_y = current_y
    card_width = qr_size
    card_height = qr_size + 50  # 额外空间放提示文字

    # 绘制圆角白色卡片
    draw.rounded_rectangle(
        (card_x, card_y, card_x + card_width, card_y + card_height),
        radius=card_radius,
        fill=(255, 255, 255, 255),
    )

    # ========== 贴上二维码 ==========
    canvas.paste(qr_img, (padding, current_y), qr_img)

    # ========== 底部提示文字 ==========
    tip_y = current_y + qr_size + 15
    tip_font = get_font(18)
    tip_text = "长按识别二维码"
    tip_bbox = draw.textbbox((0, 0), tip_text, font=tip_font)
    tip_width = tip_bbox[2] - tip_bbox[0]
    tip_x = (canvas_width - tip_width) // 2
    draw.text((tip_x, tip_y), tip_text, fill=(128, 128, 128), font=tip_font)

    # ========== 保存 ==========
    if not output_path:
        hash_str = hashlib.md5(url.encode()).hexdigest()[:8]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, f"qr_{hash_str}.png")
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    canvas.save(output_path, "PNG")
    print(f"✅ 二维码已生成: {output_path}")

    return output_path


def add_logo(qr_img: Image.Image, logo_path: str, qr_size: int) -> Image.Image:
    """在二维码中心添加 Logo"""
    try:
        logo = Image.open(logo_path)

        # Logo 尺寸为二维码的 25%
        logo_size = int(qr_size * 0.25)
        padding = int(logo_size * 0.1)

        # 创建白色圆形背景
        bg_circle = Image.new("RGBA", (logo_size, logo_size), (255, 255, 255, 255))
        mask = Image.new("L", (logo_size, logo_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, logo_size, logo_size), fill=255)

        # 调整 logo 大小
        logo_resized = logo.resize(
            (logo_size - padding * 2, logo_size - padding * 2),
            Image.Resampling.LANCZOS
        )
        if logo_resized.mode != "RGBA":
            logo_resized = logo_resized.convert("RGBA")

        # 将 logo 粘贴到白色背景中心
        bg_circle.paste(logo_resized, (padding, padding))

        # 计算位置并粘贴到二维码中心
        pos = ((qr_size - logo_size) // 2, (qr_size - logo_size) // 2)
        qr_img.paste(bg_circle, pos, mask)

    except Exception as e:
        print(f"⚠️ Logo 处理失败: {e}")

    return qr_img


def main():
    parser = argparse.ArgumentParser(description="二维码美化生成器 V3")
    parser.add_argument("--url", required=True, help="二维码链接")
    parser.add_argument("--title", default=None, help="主标题")
    parser.add_argument("--subtitle", default=None, help="副标题")
    parser.add_argument("--logo", default=None, help="Logo图片路径")
    parser.add_argument("--output", default=None, help="输出路径")
    parser.add_argument("--theme", choices=["gradient", "elegant", "warm"], default="gradient", help="主题样式")
    parser.add_argument("--size", type=int, default=400, help="二维码尺寸")

    args = parser.parse_args()

    output = create_qr_code(
        url=args.url,
        title=args.title,
        subtitle=args.subtitle,
        logo_path=args.logo,
        output_path=args.output,
        theme=args.theme,
        qr_size=args.size,
    )

    return output


if __name__ == "__main__":
    main()