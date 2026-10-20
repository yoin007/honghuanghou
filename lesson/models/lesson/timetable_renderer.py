# _*_ coding: utf-8 _*_
"""清新风格课表渲染 (Pillow)。

白卡片布局 + 上午/下午/晚上分组色带 + 班级配色图例, 数据与样式分离。
与 ImageRenderer (matplotlib) 并存, 通过 lesson.yaml 的 timetable_renderer 配置切换。
设计参考 teacher_timetable_package 的通用课表版式。
"""

import hashlib
import math
import os
import re
import time
from typing import Optional

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from utils.fonts import get_chinese_font_path

# ---- 布局常量 ----
CARD_PAD = 46        # 画布边缘到白色卡片的间距
INNER_X = 85         # 卡片内边距
INFO_H = 75          # 信息栏高度
HEADER_H = 64        # 表头高度
ROW_H = 104          # 行高
GROUP_W = 120        # 上午/下午/晚上分组列宽
PERIOD_W = 180       # 节次列宽
DAY_W = 190          # 星期列宽 (列数自适应)

FONT_TITLE = 68
FONT_SUBTITLE = 25
FONT_INFO = 27
FONT_HEADER = 28
FONT_PERIOD = 23
FONT_TIME = 18
FONT_GROUP = 32
FONT_GROUP_COUNT = 20
FONT_CELL = 21       # 单元格色块文字 (过长时自动缩到 13)
FONT_LEGEND = 20
FONT_FOOTER = 23

WEEKDAY_NAMES = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}

# ---- 配色 ----
BLUE = (34, 103, 164)
MUTED = (113, 147, 175)
BORDER = (212, 230, 244)
BG = (244, 250, 255)
CARD_OUTLINE = (220, 235, 246)
INFO_BAR = (234, 245, 253)
HEADER_BLUE = (92, 165, 221)
CELL_WHITE = (251, 253, 255)
EMPTY_GRAY = (181, 199, 217)
HIGHLIGHT_TEXT = (200, 30, 30)

GROUP_STYLE = {
    "上午": ((233, 245, 254), "sun"),
    "下午": ((233, 249, 246), "half"),
    "晚上": ((237, 240, 254), "moon"),
}
DEFAULT_BAND = (241, 247, 253)

# 班级固定配色: 班级名 -> (文字色, 底色)
CLASS_COLORS = {
    "高二3": ((23, 90, 155), (218, 236, 255)),
    "高二7": ((38, 115, 76), (221, 245, 229)),
    "高二10": ((184, 81, 36), (255, 232, 214)),
}

# 未登记班级的兜底色板 (文字色, 底色), 按班级名哈希取色, 保证同一班级颜色固定
FALLBACK_PALETTE = [
    ((23, 90, 155), (218, 236, 255)),    # 蓝
    ((38, 115, 76), (221, 245, 229)),    # 绿
    ((184, 81, 36), (255, 232, 214)),    # 橙
    ((100, 73, 167), (234, 229, 255)),   # 紫
    ((139, 105, 13), (255, 242, 201)),   # 黄
    ((23, 111, 121), (215, 245, 245)),   # 青
    ((153, 82, 118), (251, 228, 239)),   # 粉
    ((176, 55, 55), (255, 226, 226)),    # 珊瑚红
]

EMPTY_MARKERS = {"", "-", "—", "nan", "None"}

_FONT_CACHE = {}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """按字号取缓存字体对象 (字体文件整个进程只解析一次)"""
    key = (size, bold)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(get_chinese_font_path(bold), size)
    return _FONT_CACHE[key]


def _assign_class_colors(df: pd.DataFrame) -> dict:
    """为课表中出现班级分配配色。

    已登记班级用固定色; 未登记班级按名字哈希取兜底色, 若与本表已用底色冲突则顺延取下一个,
    保证同一张表内不同班级不同色, 且同一班级在不同课表中颜色基本固定。
    """
    used_bgs = set()
    result = {}
    for i in range(len(df.index)):
        for j in range(len(df.columns)):
            value = str(df.iloc[i, j]).strip()
            if value in EMPTY_MARKERS:
                continue
            class_key = value.split()[0].split("-")[0]
            if class_key in result:
                continue
            if class_key in CLASS_COLORS:
                pair = CLASS_COLORS[class_key]
            else:
                idx = int(hashlib.md5(class_key.encode("utf-8")).hexdigest(), 16) % len(FALLBACK_PALETTE)
                while FALLBACK_PALETTE[idx][1] in used_bgs and len(used_bgs) < len(FALLBACK_PALETTE):
                    idx = (idx + 1) % len(FALLBACK_PALETTE)
                pair = FALLBACK_PALETTE[idx]
            result[class_key] = pair
            used_bgs.add(pair[1])
    return result


def _group_key(label: str) -> str:
    """按节次标签推断分组: 早读等自成一组, 第N节按序号归入 上午/下午/晚上"""
    if label.startswith("晚"):
        return "晚上"
    m = re.match(r"第\s*(\d+)\s*节", label)
    if m:
        n = int(m.group(1))
        return "上午" if n <= 4 else ("下午" if n <= 8 else "晚上")
    return label


def _draw_group_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, kind: str, color: tuple, band: tuple) -> None:
    """绘制分组图标 (几何图形, 不依赖字体符号): sun=太阳, half=半月, moon=月牙"""
    if kind == "sun":
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
        for k in range(8):
            a = math.radians(k * 45)
            draw.line(
                [cx + (r + 6) * math.cos(a), cy + (r + 6) * math.sin(a),
                 cx + (r + 13) * math.cos(a), cy + (r + 13) * math.sin(a)],
                fill=color, width=3,
            )
    elif kind == "half":
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=3)
        draw.pieslice([cx - r, cy - r, cx + r, cy + r], 90, 270, fill=color)
    elif kind == "moon":
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
        draw.ellipse([cx - r + 8, cy - r - 5, cx + r + 8, cy + r - 5], fill=band)


class TimetableRenderer:
    """清新风格课表渲染器 (Pillow)。"""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def render(
        self,
        df: pd.DataFrame,
        png_name: str = "temp.png",
        title: str = "",
        highlight_cells: Optional[list] = None,
        period_labels: Optional[dict] = None,
    ) -> list:
        """
        将课表 DataFrame 渲染为清新风格 PNG。

        Args:
            df: 课表数据, index 为节次, columns 为星期, 单元格为 "班级-学科" / "班级 学科"
            highlight_cells: 需要高亮的单元格坐标列表, 元素为 ``(行索引值, 列名)``,
                语义与 ImageRenderer.dataframe_to_png 一致 (用于调课提醒标记变化位置)
            period_labels: 节次显示标签, ``{index值: "第1节\\n8:00-8:45"}``, 缺省直接显示 index 值
        Returns:
            包含保存路径的列表, 与 ImageRenderer.dataframe_to_png 返回格式一致
        """
        os.makedirs(self.output_dir, exist_ok=True)

        df = df.copy().fillna("")
        row_lookup = {**{str(k): v for v, k in enumerate(df.index)}, **{k: v for v, k in enumerate(df.index)}}
        col_lookup = {**{str(k): v for v, k in enumerate(df.columns)}, **{k: v for v, k in enumerate(df.columns)}}

        timestamp = str(int(time.time() * 1000))
        name, ext = os.path.splitext(png_name)
        ext = ext or ".png"
        save_path = os.path.join(self.output_dir, f"{name}_{timestamp}{ext}")

        n_periods = len(df.index)
        n_days = len(df.columns)
        grid_x = CARD_PAD + INNER_X
        grid_w = GROUP_W + PERIOD_W + n_days * DAY_W
        width = grid_x + grid_w + INNER_X + CARD_PAD

        info_bottom = 224 + INFO_H if title else 224
        grid_top = info_bottom + 18 + HEADER_H + 4
        classes, total, legend_rows = self._scan_classes(df, grid_w)
        height = grid_top + n_periods * ROW_H + 202 + (legend_rows - 1) * 49

        img = Image.new("RGB", (width, height), BG)
        draw = ImageDraw.Draw(img)

        # 背景装饰 + 白色卡片
        draw.ellipse([-320, -370, 650, 330], fill=(229, 243, 253))
        draw.ellipse([width - 450, -350, width + 250, 280], fill=(230, 244, 255))
        draw.rounded_rectangle(
            [CARD_PAD, 32, width - CARD_PAD, height - CARD_PAD],
            radius=34, fill="white", outline=CARD_OUTLINE, width=2,
        )
        self._draw_title(draw, width)
        if title:
            bar = draw.rounded_rectangle([grid_x, 224, grid_x + grid_w, 224 + INFO_H], radius=16, fill=INFO_BAR)
            draw.text((grid_x + 30, 224 + INFO_H // 2), title,
                      font=_font(FONT_INFO, bold=True), fill=BLUE, anchor="lm")

        # 表头 (数字星期转换为 周一~周日)
        header_y = info_bottom + 18
        draw.rounded_rectangle([grid_x, header_y, grid_x + grid_w, header_y + HEADER_H], radius=12, fill=HEADER_BLUE)
        cx = grid_x + (GROUP_W + PERIOD_W) // 2
        draw.text((cx, header_y + HEADER_H // 2), "时间", font=_font(FONT_HEADER, bold=True),
                  fill="white", anchor="mm")
        for j, col in enumerate(df.columns):
            x = grid_x + GROUP_W + PERIOD_W + j * DAY_W
            draw.text((x + DAY_W // 2, header_y + HEADER_H // 2), self._weekday_name(col),
                      font=_font(FONT_HEADER, bold=True), fill="white", anchor="mm")

        # 单元格
        labels = [self._period_label(p, period_labels) for p in df.index]
        groups = self._build_groups(labels, n_periods)
        self._draw_group_bands(draw, groups, grid_x, grid_top)
        class_colors = _assign_class_colors(df)

        y = grid_top
        for i in range(n_periods):
            band = self._band_color(groups, i)
            label = labels[i]
            # 节次列 (两行: 节次标签 + 时间)
            draw.rectangle([grid_x + GROUP_W, y + 2, grid_x + GROUP_W + PERIOD_W, y + ROW_H - 2], fill=band)
            parts = label.split("\n")
            draw.text((grid_x + GROUP_W + PERIOD_W // 2, y + ROW_H // 2 - 15), parts[0],
                      font=_font(FONT_PERIOD, bold=True), fill=BLUE, anchor="mm")
            if len(parts) > 1:
                draw.text((grid_x + GROUP_W + PERIOD_W // 2, y + ROW_H // 2 + 18), parts[1],
                          font=_font(FONT_TIME), fill=MUTED, anchor="mm")

            for j, day in enumerate(df.columns):
                x = grid_x + GROUP_W + PERIOD_W + j * DAY_W
                highlighted = self._is_highlighted(df.index[i], day, highlight_cells, row_lookup, col_lookup)
                self._draw_cell(draw, x, y, str(df.iloc[i, j]), highlighted, class_colors)
            y += ROW_H

        self._draw_footer(draw, grid_x, grid_w, y, classes, total, class_colors)
        img.save(save_path)
        return [save_path]

    # ---- 布局绘制 ----

    def _draw_title(self, draw, width):
        """大标题 + 副标题"""
        cx = width // 2
        draw.text((cx, 108), "课 程 表", font=_font(FONT_TITLE, bold=True), fill=BLUE, anchor="mm")
        draw.text((cx, 172), "立德树人  ·  以文化人", font=_font(FONT_SUBTITLE), fill=MUTED, anchor="mm")

    def _draw_group_bands(self, draw, groups, grid_x, grid_top):
        """上午/下午/晚上分组色带 + 图标"""
        for group in groups:
            band, icon = GROUP_STYLE.get(group["key"], (DEFAULT_BAND, None))
            top = grid_top + group["start"] * ROW_H + 2
            bottom = grid_top + (group["end"] + 1) * ROW_H - 4
            draw.rounded_rectangle([grid_x, top, grid_x + GROUP_W - 5, bottom], radius=13, fill=band)
            cx = grid_x + GROUP_W // 2 - 2
            cy = (top + bottom) // 2
            n = group["end"] - group["start"] + 1
            if icon and n >= 2:
                _draw_group_icon(draw, cx, cy - 38, 15, icon, BLUE, band)
                draw.text((cx, cy + 10), group["key"], font=_font(FONT_GROUP, bold=True), fill=BLUE, anchor="mm")
                draw.text((cx, cy + 48), f"{n} 节", font=_font(FONT_GROUP_COUNT), fill=MUTED, anchor="mm")
            else:
                draw.text((cx, cy), group["key"], font=_font(FONT_GROUP if n >= 2 else FONT_PERIOD, bold=True),
                          fill=BLUE, anchor="mm")

    def _draw_cell(self, draw, x, y, value, highlighted, class_colors):
        """单个课表单元格: 空课显示 —, 有课绘制班级配色圆角块; 高亮只改文字颜色, 不动背景"""
        rect = [x + 2, y + 2, x + DAY_W - 2, y + ROW_H - 2]
        draw.rectangle(rect, fill=CELL_WHITE, outline=BORDER, width=1)

        value = value.strip()
        if value in EMPTY_MARKERS:
            draw.text((x + DAY_W // 2, y + ROW_H // 2), "—", font=_font(23), fill=EMPTY_GRAY, anchor="mm")
            return

        display = value.replace("-", " ")
        class_key = value.split()[0].split("-")[0]
        fg, bg = class_colors.get(class_key, FALLBACK_PALETTE[-1])
        if highlighted:
            fg = HIGHLIGHT_TEXT

        # 色块内文字过长时自动缩小
        size = FONT_CELL
        max_w = DAY_W - 2 * 9 - 12
        while size > 13 and draw.textbbox((0, 0), display, font=_font(size, bold=True))[2] > max_w:
            size -= 1
        pad = 9
        draw.rounded_rectangle([x + pad, y + 23, x + DAY_W - pad, y + ROW_H - 23], radius=12, fill=bg)
        draw.text((x + DAY_W // 2, y + ROW_H // 2), display, font=_font(size, bold=True), fill=fg, anchor="mm")

    @staticmethod
    def _scan_classes(df, grid_w):
        """扫描课表: 按出现顺序收集班级、统计总课时、预估图例行数 (供画布高度计算)"""
        classes = []
        total = 0
        for i in range(len(df.index)):
            for j in range(len(df.columns)):
                value = str(df.iloc[i, j]).strip()
                if value in EMPTY_MARKERS:
                    continue
                total += 1
                class_key = value.split()[0].split("-")[0]
                if class_key not in classes:
                    classes.append(class_key)
        # 模拟图例排版, 估算换行后的行数
        legend_x = 0
        rows = 1
        f = _font(FONT_LEGEND, bold=True)
        limit = grid_w - 220
        for class_key in classes:
            chip_w = f.getlength(class_key) + 38
            if legend_x + chip_w > limit:
                rows += 1
                legend_x = 0
            legend_x += chip_w + 14
        return classes, total, rows

    def _draw_footer(self, draw, grid_x, grid_w, grid_bottom, classes, total, class_colors):
        """底部分隔线 + 班级图例 + 合计课时 + 标语"""
        y = grid_bottom + 20
        draw.line([grid_x, y, grid_x + grid_w, y], fill=BORDER, width=2)

        # 图例色块
        legend_x = grid_x
        legend_y = y + 30
        for class_key in classes:
            fg, bg = class_colors.get(class_key, FALLBACK_PALETTE[-1])
            f = _font(FONT_LEGEND, bold=True)
            text_w = draw.textbbox((0, 0), class_key, font=f)[2]
            chip_w = text_w + 38
            if legend_x + chip_w > grid_x + grid_w - 220:
                legend_x = grid_x
                legend_y += 49
            draw.rounded_rectangle([legend_x, legend_y, legend_x + chip_w, legend_y + 37], radius=17, fill=bg)
            draw.text((legend_x + chip_w // 2, legend_y + 18), class_key, font=f, fill=fg, anchor="mm")
            legend_x += chip_w + 14

        # 合计课时
        if total:
            draw.text((grid_x + grid_w, y + 48), f"合计 {total} 节课",
                      font=_font(FONT_FOOTER, bold=True), fill=BLUE, anchor="rm")
        draw.text((grid_x + grid_w // 2, legend_y + 80), "教书育人  ·  追求卓越",
                  font=_font(FONT_FOOTER), fill=MUTED, anchor="mm")

    # ---- 分组 ----

    @staticmethod
    def _build_groups(labels, n_periods):
        """按节次标签把行分成若干组 (组内行号连续且 key 相同)"""
        keys = [_group_key(lbl.split("\n")[0]) for lbl in labels]
        groups = []
        start = 0
        for i in range(1, n_periods + 1):
            if i == n_periods or keys[i] != keys[start]:
                groups.append({"key": keys[start], "start": start, "end": i - 1})
                start = i
        return groups

    @staticmethod
    def _band_color(groups, row):
        for g in groups:
            if g["start"] <= row <= g["end"]:
                return GROUP_STYLE.get(g["key"], (DEFAULT_BAND, None))[0]
        return DEFAULT_BAND

    # ---- 工具 ----

    @staticmethod
    def _weekday_name(col) -> str:
        """数字星期 (1-7, int 或 str) 转换为 周一~周日, 其他值原样返回"""
        key = int(col) if isinstance(col, int) or (isinstance(col, str) and col.isdigit()) else None
        return WEEKDAY_NAMES.get(key, str(col))

    @staticmethod
    def _period_label(period, period_labels: Optional[dict]) -> str:
        if not period_labels:
            return str(period)
        return period_labels.get(period, period_labels.get(str(period), str(period)))

    @staticmethod
    def _is_highlighted(period, day, highlight_cells, row_lookup, col_lookup) -> bool:
        if not highlight_cells:
            return False
        for row_key, col_key in highlight_cells:
            r = row_lookup.get(row_key, row_lookup.get(str(row_key)))
            c = col_lookup.get(col_key, col_lookup.get(str(col_key)))
            if r is None or c is None:
                continue
            period_pos = row_lookup.get(period, row_lookup.get(str(period)))
            day_pos = col_lookup.get(day, col_lookup.get(str(day)))
            if period_pos == r and day_pos == c:
                return True
        return False
