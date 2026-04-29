# _*_ coding: utf-8 _*_
"""课表图片渲染。

该模块只负责把 DataFrame 渲染成图片，不读取课表、不发送通知。
"""

import os
import time

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
    ) -> list:
        """
        将 DataFrame 转换为 PNG 图片。

        Returns:
            包含保存路径的列表，兼容旧的 Lesson.df_to_png 返回格式。
        """
        os.makedirs(self.output_dir, exist_ok=True)

        df = df.copy().fillna("")
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

        fig.tight_layout()
        canvas.print_figure(
            save_path,
            dpi=200,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )

        return [save_path]
