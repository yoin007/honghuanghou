#!/usr/bin/env python3
"""
二维码美化生成器 V2
支持：渐变背景、圆角边框、装饰元素、阴影效果、多种主题模板

用法:
    python generate_v2.py --url "https://example.com" --title "扫码访问" --theme gradient
    python generate_v2.py --url "https://example.com" --title "标题" --theme elegant --subtitle "诚邀参与"
"""

import argparse
import os

try:
    import qrcode
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer, CircleModuleDrawer
    from qrcode.image.styles.colormasks import SolidFillColorMask, VerticalGradiantColorMask
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError as e:
    print(f"缺少依赖: {e}")
    print("请安装: pip3 install qrcode[pil] pillow")
    exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LOGO = os.path.join(SCRIPT_DIR, "logos", "default.jpg")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# 预设主题
THEMES = {
    "gradient": {
        "name": "渐变紫蓝",
        "bg_gradient": [(102, 126, 234), (118, 75, 162)],
        "qr_color": [(102, 126, 234), (118, 75, 162)],
        "text_color": (255, 255, 255),
        "accent_color": (255, 255, 255),
    },
    "elegant": {
        "name": "优雅深蓝",
        "bg_gradient": [(30, 58, 138), (59, 130, 246)],
        "qr_color": [(59, 130, 246), (147, 197, 253)],
        "text_color": (255, 255, 255),
        "accent_color": (191, 219, 254),
    },
    "warm": {
        "name": "温暖橙红",
        "bg_gradient": [(234, 88, 12), (251, 146, 60)],
        "qr_color": [(251, 146, 60), (254, 215, 170)],
        "text_color": (255, 255, 255),
        "accent_color": (255, 237, 213),
    },
    "nature": {
        "name": "自然绿意",
        "bg_gradient": [(22, 101, 52), (74, 222, 128)],
        "qr_color": [(74, 222, 128), (187, 247, 208)],
        "text_color": (255, 255, 255),
        "accent_color": (220, 252, 231),
    },
    "minimal": {
        "name": "简约黑白",
        "bg_gradient": [(30, 30, 30), (60, 60, 60)],
        "qr_color": [(80, 80, 80), (40, 40, 40)],
        "text_color": (255, 255, 255),
        "accent_color": (200, 200, 200),
    },
    "rose": {
        "name": "玫瑰金",
        "bg_gradient": [(190, 95, 120), (255, 182, 193)],
        "qr_color": [(219, 112, 147), (255, 192, 203)],
        "text_color": (255, 255, 255),
        "accent_color": (255, 228, 225),
    },
}


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """获取字体"""
    font_paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except:
                continue
    
    return ImageFont.load_default()


def draw_rounded_rect(draw: ImageDraw, coords: tuple, radius: int, fill, outline=None, width=0):
    """绘制圆角矩形"""
    x1, y1, x2, y2 = coords
    draw.rounded_rectangle(coords, radius=radius, fill=fill, outline=outline, width=width)


def create_decorative_elements(draw: ImageDraw, width: int, height: int, theme: dict):
    """创建装饰元素"""
    accent = theme.get("accent_color", (255, 255, 255))
    
    # 左上角装饰圆
    draw.ellipse(
        [-50, -50, 100, 100],
        fill=(*accent[:3], 30) if len(accent) == 3 else accent,
    )
    
    # 右下角装饰圆
    draw.ellipse(
        [width - 80, height - 80, width + 50, height + 50],
        fill=(*accent[:3], 20) if len(accent) == 3 else accent,
    )
    
    # 小装饰点
    for i in range(5):
        import random
        x = random.randint(20, width - 20)
        y = random.randint(20, height - 20)
        r = random.randint(3, 8)
        opacity = random.randint(10, 40)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(*accent[:3], opacity))


def create_qr_code_v2(
    url: str,
    title: str = None,
    subtitle: str = None,
    logo_path: str = None,
    output_path: str = None,
    theme: str = "gradient",
    size: int = 500,
    add_shadow: bool = True,
    corner_radius: int = 20,
    style: str = "rounded",
) -> str:
    """
    生成美化二维码 V2
    
    Args:
        url: 二维码链接
        title: 主标题
        subtitle: 副标题
        logo_path: Logo路径
        output_path: 输出路径
        theme: 主题名称
        size: 二维码尺寸
        add_shadow: 是否添加阴影
        corner_radius: 圆角半径
        style: 码眼样式
    
    Returns:
        输出文件路径
    """
    
    theme_config = THEMES.get(theme, THEMES["gradient"])
    bg_start, bg_end = theme_config["bg_gradient"]
    qr_start, qr_end = theme_config["qr_color"]
    text_color = theme_config["text_color"]
    accent_color = theme_config["accent_color"]
    
    # ========== 创建二维码 ==========
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # 选择码眼样式
    if style == "rounded":
        module_drawer = RoundedModuleDrawer()
    elif style == "circle":
        module_drawer = CircleModuleDrawer()
    else:
        module_drawer = None
    
    # 创建渐变色二维码
    color_mask = VerticalGradiantColorMask(
        back_color=(255, 255, 255),
        top_color=qr_start,
        bottom_color=qr_end,
    )
    
    qr_img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=module_drawer,
        color_mask=color_mask,
    )
    
    # 获取并调整二维码
    qr_img = qr_img.get_image() if hasattr(qr_img, 'get_image') else qr_img
    qr_img = qr_img.resize((size, size), Image.Resampling.LANCZOS)
    if qr_img.mode != "RGBA":
        qr_img = qr_img.convert("RGBA")
    
    # 嵌入 Logo
    if logo_path and os.path.exists(logo_path):
        qr_img = add_logo(qr_img, logo_path, size)
    
    # ========== 创建画布 ==========
    canvas_width = size + 100
    canvas_height = size + 250 if title else size + 150
    
    canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # ========== 渐变背景 ==========
    for y in range(canvas_height):
        ratio = y / canvas_height
        r = int(bg_start[0] + (bg_end[0] - bg_start[0]) * ratio)
        g = int(bg_start[1] + (bg_end[1] - bg_start[1]) * ratio)
        b = int(bg_start[2] + (bg_end[2] - bg_start[2]) * ratio)
        draw.line([(0, y), (canvas_width, y)], fill=(r, g, b, 255))
    
    # ========== 装饰元素 ==========
    create_decorative_elements(draw, canvas_width, canvas_height, theme_config)
    
    # ========== 标题区域 ==========
    if title:
        # 标题背景
        title_bg_height = 80
        draw_rounded_rect(
            draw,
            (25, 20, canvas_width - 25, 20 + title_bg_height),
            radius=15,
            fill=(*accent_color[:3], 40),
        )
        
        # 主标题
        title_font = get_font(32, bold=True)
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (canvas_width - title_width) // 2
        title_y = 35
        
        # 文字阴影
        draw.text((title_x + 1, title_y + 1), title, fill=(0, 0, 0, 80), font=title_font)
        draw.text((title_x, title_y), title, fill=text_color, font=title_font)
        
        # 副标题
        if subtitle:
            sub_font = get_font(22)
            sub_bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
            sub_width = sub_bbox[2] - sub_bbox[0]
            sub_x = (canvas_width - sub_width) // 2
            sub_y = 70
            draw.text((sub_x, sub_y), subtitle, fill=(*accent_color[:3], 200), font=sub_font)
    
    # ========== 二维码区域 ==========
    qr_x = (canvas_width - size) // 2
    qr_y = 120 if title else 30
    
    # 二维码阴影
    if add_shadow:
        shadow = Image.new("RGBA", (size + 20, size + 20), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(
            (10, 10, size + 10, size + 10),
            radius=corner_radius,
            fill=(0, 0, 0, 60)
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(10))
        canvas.paste(shadow, (qr_x - 10, qr_y - 10), shadow)
    
    # 二维码白色背景
    qr_bg = Image.new("RGBA", (size + 20, size + 20), (255, 255, 255, 255))
    qr_bg_draw = ImageDraw.Draw(qr_bg)
    qr_bg_draw.rounded_rectangle(
        (0, 0, size + 19, size + 19),
        radius=corner_radius,
        fill=(255, 255, 255, 255)
    )
    canvas.paste(qr_bg, (qr_x - 10, qr_y - 10), qr_bg)
    
    # 贴上二维码
    canvas.paste(qr_img, (qr_x, qr_y), qr_img)
    
    # ========== 底部提示 ==========
    tip_y = qr_y + size + 25
    tip_font = get_font(20)
    tip_text = "扫码报名"
    tip_bbox = draw.textbbox((0, 0), tip_text, font=tip_font)
    tip_width = tip_bbox[2] - tip_bbox[0]
    tip_x = (canvas_width - tip_width) // 2
    
    # 提示文字
    draw.text((tip_x + 1, tip_y + 1), tip_text, fill=(0, 0, 0, 60), font=tip_font)
    draw.text((tip_x, tip_y), tip_text, fill=text_color, font=tip_font)
    
    # ========== 保存 ==========
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if not output_path:
        import hashlib
        hash_str = hashlib.md5(url.encode()).hexdigest()[:8]
        output_path = os.path.join(OUTPUT_DIR, f"qr_v2_{hash_str}.png")
    
    canvas.save(output_path, "PNG")
    print(f"✅ 二维码已生成: {output_path}")
    
    return output_path


def add_logo(qr_img: Image.Image, logo_path: str, qr_size: int) -> Image.Image:
    """在二维码中心添加 Logo"""
    try:
        logo = Image.open(logo_path)
        
        logo_size = int(qr_size * 0.22)
        padding = int(logo_size * 0.1)
        
        # 创建白色圆形背景
        mask = Image.new("L", (logo_size, logo_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, logo_size, logo_size), fill=255)
        
        bg = Image.new("RGBA", (logo_size, logo_size), (255, 255, 255, 255))
        bg_circle = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
        bg_circle.paste(bg, mask=mask)
        
        logo = logo.resize((logo_size - padding * 2, logo_size - padding * 2), Image.Resampling.LANCZOS)
        if logo.mode != "RGBA":
            logo = logo.convert("RGBA")
        
        bg_circle.paste(logo, (padding, padding), logo)
        
        pos = ((qr_size - logo_size) // 2, (qr_size - logo_size) // 2)
        qr_img.paste(bg_circle, pos, bg_circle)
        
    except Exception as e:
        print(f"⚠️ Logo 处理失败: {e}")
    
    return qr_img


def main():
    parser = argparse.ArgumentParser(description="二维码美化生成器 V2")
    parser.add_argument("--url", required=True, help="二维码链接")
    parser.add_argument("--title", default=None, help="主标题")
    parser.add_argument("--subtitle", default=None, help="副标题")
    parser.add_argument("--logo", default=None, help="Logo图片路径")
    parser.add_argument("--output", default=None, help="输出路径")
    parser.add_argument("--theme", choices=list(THEMES.keys()), default="gradient", help="主题样式")
    parser.add_argument("--size", type=int, default=500, help="二维码尺寸")
    parser.add_argument("--style", choices=["rounded", "circle", "square"], default="rounded", help="码眼样式")
    parser.add_argument("--list-themes", action="store_true", help="列出所有主题")
    
    args = parser.parse_args()
    
    if args.list_themes:
        print("可用主题:")
        for key, theme in THEMES.items():
            print(f"  {key}: {theme['name']}")
        return
    
    output = create_qr_code_v2(
        url=args.url,
        title=args.title,
        subtitle=args.subtitle,
        logo_path=args.logo,
        output_path=args.output,
        theme=args.theme,
        size=args.size,
        style=args.style,
    )
    
    return output


if __name__ == "__main__":
    main()