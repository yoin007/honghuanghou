# -*- coding: utf-8 -*-
"""TimetableRenderer 回归测试。"""

import os
import shutil
import tempfile
import time

import pandas as pd
import pytest
from PIL import Image


@pytest.fixture()
def renderer():
    tmp_dir = tempfile.mkdtemp()
    from models.lesson.timetable_renderer import TimetableRenderer

    r = TimetableRenderer(tmp_dir)
    yield r
    shutil.rmtree(tmp_dir, ignore_errors=True)


def _sample_df():
    periods = [f"第{i}节" for i in range(1, 13)]
    days = ["周一", "周二", "周三", "周四", "周五"]
    return pd.DataFrame(
        {
            "周一": ["高二3-语文", "高二7-数学", "", "高二10-英语", "语文", "-", "高二3-语文", "", "数学", "英语", "", "高二7-数学"],
            "周二": ["", "高二10-英语"] * 6,
            "周三": ["高二7-数学", "", "高二3-语文", "", "高二10-英语", "", "语文", "数学", "", "高二3-语文", "英语", ""],
            "周四": ["高二10-英语", "高二3-语文", "", "高二7-数学"] * 3,
            "周五": ["语文", "数学", "英语", "", "高二3-语文", "", "高二10-英语", "高二7-数学", "", "语文", "", "数学"],
        },
        index=periods,
    )


def test_render_creates_png(renderer):
    paths = renderer.render(_sample_df(), "test.png", title="张三本周的课表")
    assert len(paths) == 1
    assert os.path.exists(paths[0])
    with Image.open(paths[0]) as img:
        assert img.format == "PNG"
        assert img.width > 0 and img.height > 0


def test_render_without_title(renderer):
    paths = renderer.render(_sample_df(), "test.png")
    assert os.path.exists(paths[0])


def test_render_arbitrary_shape(renderer):
    """非 12x5 的课表也能渲染 (列数/节数自适应)"""
    df = pd.DataFrame(
        [["语文", "数学"], ["英语", ""]],
        index=["第1节", "第2节"],
        columns=["周一", "周二"],
    )
    paths = renderer.render(df, "small.png")
    with Image.open(paths[0]) as img:
        assert img.format == "PNG"


def test_render_int_weekday_and_period_labels(renderer):
    """数字星期 (1-5) 应显示为 周一~周五; 节次标签带时间"""
    df = pd.DataFrame(
        [["语文"]],
        index=[1],
        columns=[1],
    )
    paths = renderer.render(df, "int.png", period_labels={1: "第1节\n8:00-8:45", "1": "第1节\n8:00-8:45"})
    assert os.path.exists(paths[0])


def test_render_highlight_cells(renderer):
    """highlight_cells 语义与 ImageRenderer 一致: (行索引值, 列名)"""
    df = _sample_df()
    paths = renderer.render(df, "hl.png", highlight_cells=[("第1节", "周一"), (1, "周二")])
    assert os.path.exists(paths[0])


def test_batch_60_performance(renderer):
    """批量 60 张的性能回归: 本机单张应远快于 matplotlib (~100ms)"""
    df = _sample_df()
    start = time.perf_counter()
    for i in range(60):
        renderer.render(df, f"t{i}.png", title=f"教师{i}本周的课表")
    elapsed = time.perf_counter() - start
    assert elapsed / 60 < 0.5, f"平均单张耗时 {elapsed / 60:.3f}s, 超出预期"
