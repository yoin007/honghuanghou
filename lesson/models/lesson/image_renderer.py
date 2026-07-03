# _*_ coding: utf-8 _*_
"""课表图片渲染。

该模块只负责把 DataFrame 渲染成图片，不读取课表、不发送通知。
"""

import os
import time
from typing import Optional

import pandas as pd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from utils.fonts import get_cached_chinese_font


class ImageRenderer:
    """DataFrame 图片渲染器。"""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def dataframe_to_png(
        self,
        df: pd.DataFrame,
        png_name: str = "temp.png",
        title: str = "",
        index_name: str = "节次\\星期",
        highlight_cells: Optional[list] = None,
    ) -> list:
        """
        将 DataFrame 转换为 PNG 图片。

        Args:
            highlight_cells: 需要高亮的单元格坐标列表，元素为 ``(行索引值, 列名)``。
                行索引值按 DataFrame 原始 index（重置前）匹配，列名按原始列名匹配。
                用于在课表调整通知中突出被调整的课。

        Returns:
            包含保存路径的列表，兼容旧的 Lesson.df_to_png 返回格式。
        """
        os.makedirs(self.output_dir, exist_ok=True)

        df = df.copy().fillna("")
        # 保留原始 index / columns，用于把 highlight_cells 的 (行值, 列名) 换算成表格坐标
        row_key_to_index = {key: pos for pos, key in enumerate(df.index.tolist())}
        col_key_to_index = {key: pos for pos, key in enumerate(df.columns.tolist())}

        df.index.name = index_name
        df.reset_index(inplace=True)

        timestamp = str(int(time.time() * 1000))
        name, ext = os.path.splitext(png_name)
        ext = ext or ".png"
        save_path = os.path.join(self.output_dir, f"{name}_{timestamp}{ext}")

        n_rows = len(df)
        n_cols = len(df.columns)

        fig = Figure(figsize=(min(n_cols * 1.1, 18), n_rows * 0.18 + 1))
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)
        ax.axis("off")

        if title:
            fig.suptitle(title, fontsize=12, fontweight="bold", y=0.95, color="#000000")

        table = ax.table(
            cellText=df.values,
            colLabels=df.columns,
            loc="center",
            cellLoc="center",
        )

        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(0.9, 1.1)

        for key, cell in table.get_celld().items():
            row, _ = key
            cell.set_edgecolor("#000000")
            cell.set_linewidth(0.5)
            cell.set_text_props(fontfamily=get_cached_chinese_font())

            if row == 0:
                cell.set_facecolor("#4A90E2")
                cell.set_text_props(color="white", fontweight="bold", fontsize=10)
                cell.set_edgecolor("#2E5C8A")
            elif row == 1:
                cell.set_facecolor("#FFFFFF")
            else:
                group = (row - 2) // 4
                cell.set_facecolor("#E8F4FF" if group % 2 == 0 else "#FFFFFF")
                cell.set_text_props(color="#000000", fontsize=10)

        for col_idx in range(len(df.columns)):
            table[(0, col_idx)].set_height(0.1)

        # 高亮被调整的单元格：reset_index 后原 index 成为首列，所以表格坐标要 +1；表头占第 0 行，同样 +1
        if highlight_cells:
            # 同时按原值和字符串建立索引，兼容 Excel 加载后 int/str 混用的情况
            row_lookup = {**{str(k): v for k, v in row_key_to_index.items()}, **row_key_to_index}
            col_lookup = {**{str(k): v for k, v in col_key_to_index.items()}, **col_key_to_index}
            for row_key, col_key in highlight_cells:
                row_pos = row_lookup.get(row_key, row_lookup.get(str(row_key)))
                col_pos = col_lookup.get(col_key, col_lookup.get(str(col_key)))
                if row_pos is None or col_pos is None:
                    continue
                table_row = row_pos + 1
                table_col = col_pos + 1
                cell = table[(table_row, table_col)]
                cell.set_facecolor("#FFCDD2")
                cell.set_edgecolor("#C62828")
                cell.set_linewidth(1.2)
                cell.set_text_props(
                    color="#B71C1C",
                    fontweight="bold",
                    fontfamily=get_cached_chinese_font(),
                )

        fig.tight_layout()
        canvas.print_figure(
            save_path,
            dpi=200,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )

        return [save_path]
