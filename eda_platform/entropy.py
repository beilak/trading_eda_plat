from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import entropy


def calculate_shannon_entropy(series: pd.Series, window: int) -> pd.Series:
    """
    Вычисляет энтропию Шеннона для бинаризованного временного ряда (рост/падение) по скользящему окну.
    """
    # 1. Квантизация: рост = 1, падение = 0
    binary = (series.diff() > 0).astype(int)

    result = []
    for i in range(len(binary)):
        if i < window:
            result.append(np.nan)
        else:
            window_slice = binary.iloc[i - window : i]
            p_counts = window_slice.value_counts(normalize=True)
            ent = entropy(p_counts, base=2)
            result.append(ent)

    return pd.Series(result, index=series.index, name="entropy")


import plotly.express as px
import plotly.graph_objects as go


def make_entropy_timeseries(
    df: pd.DataFrame, column: str, entropy_col: str = "entropy"
) -> go.Figure:
    fig = px.line(
        df,
        x=df.index,
        y=entropy_col,
        title=f"Энтропия Шеннона по скользящему окну {column}",
    )
    fig.update_traces(mode="lines+markers")
    fig.update_layout(yaxis_title="Entropy", xaxis_title="Date")
    return fig


def make_entropy_distribution(
    df: pd.DataFrame,
    column: str,
    entropy_col: str = "entropy",
) -> go.Figure:
    fig = px.histogram(
        df.dropna(),
        x=entropy_col,
        nbins=30,
        title=f"Распределение энтропии Шеннона {column}",
    )
    fig.update_traces(textposition="inside", textfont_size=8)
    fig.update_layout(xaxis_title="Entropy", yaxis_title="Частота")
    return fig


def summarize_entropy(df: pd.DataFrame, entropy_col: str = "entropy") -> dict:
    entropy_series = df[entropy_col].dropna()
    return {
        "current_entropy": round(entropy_series.iloc[-1], 4),
        "mean_entropy": round(entropy_series.mean(), 4),
        "min_entropy": round(entropy_series.min(), 4),
        "max_entropy": round(entropy_series.max(), 4),
        "entropy_25pct": round(entropy_series.quantile(0.25), 4),
        "entropy_75pct": round(entropy_series.quantile(0.75), 4),
    }


import plotly.graph_objects as go


def color_for_entropy(value, thresholds=(0.85, 1.0)):
    """
    Простая функция выбора цвета.
    Если энтропия ниже 0.85 — зеленый,
    между 0.85 и 0.95 — желтый,
    выше 0.95 — красный.
    """
    low, high = thresholds
    if value < low:
        return "green"
    elif value < high:
        return "orange"
    else:
        return "red"


def make_entropy_indicator(value, title, suffix="", thresholds=(0.85, 1.0)):
    color = color_for_entropy(value, thresholds)
    fig = go.Figure()
    fig.add_trace(
        go.Indicator(
            mode="number",
            value=value,
            number={"suffix": suffix, "font": {"size": 40}},
            title={"text": title, "font": {"size": 18}},
            domain={"x": [0, 1], "y": [0, 1]},
            number_font_color=color,
        )
    )
    return fig


def make_entropy_summary_indicators(entropy_stats: dict):
    figs = {}
    figs["current"] = make_entropy_indicator(
        entropy_stats["current_entropy"], "Текущая энтропия", suffix=" бит"
    )
    figs["mean"] = make_entropy_indicator(
        entropy_stats["mean_entropy"], "Средняя энтропия", suffix=" бит"
    )
    figs["min"] = make_entropy_indicator(
        entropy_stats["min_entropy"], "Минимальная энтропия", suffix=" бит"
    )
    figs["max"] = make_entropy_indicator(
        entropy_stats["max_entropy"],
        "Максимальная энтропия",
        suffix=" бит",
        thresholds=(0.0, 0.5),
    )  # Максимум — лучше чтобы был низким, но обычно высокий — плохо, тут цвет наоборот
    figs["25pct"] = make_entropy_indicator(
        entropy_stats["entropy_25pct"], "25-й процентиль", suffix=" бит"
    )
    figs["75pct"] = make_entropy_indicator(
        entropy_stats["entropy_75pct"], "75-й процентиль", suffix=" бит"
    )
    return figs


def get_entropy_simple_text_renderer(entropy_stats):
    def render(container):
        def label_and_color(val):
            if val > 0.9:
                return "хаос (трудно предсказать)", "red"
            elif val > 0.8:
                return "средне (осторожно)", "orange"
            else:
                return "структура (можно торговать)", "green"

        current_lbl, current_color = label_and_color(entropy_stats["current_entropy"])
        mean_lbl, mean_color = label_and_color(entropy_stats["mean_entropy"])
        min_lbl, min_color = label_and_color(entropy_stats["min_entropy"])

        container.markdown(
            f"<span style='color:{current_color}; font-weight:bold;'>Текущая энтропия: {entropy_stats['current_entropy']:.3f} — {current_lbl}</span>",
            unsafe_allow_html=True,
        )
        container.markdown(
            f"<span style='color:{mean_color}; font-weight:bold;'>Средняя энтропия: {entropy_stats['mean_entropy']:.3f} — {mean_lbl}</span>",
            unsafe_allow_html=True,
        )
        container.markdown(
            f"<span style='color:{min_color}; font-weight:bold;'>Минимальная энтропия: {entropy_stats['min_entropy']:.3f} — {min_lbl}</span>",
            unsafe_allow_html=True,
        )

    return render


def make_shannon_entropy(
    df: pd.DataFrame, column: str, window=20
) -> tuple[go.Figure, go.Figure, dict, Any]:
    df["entropy"] = calculate_shannon_entropy(df[column], window)

    # 2. Визуализации
    fig_line = make_entropy_timeseries(
        df,
        column=column,
    )
    fig_hist = make_entropy_distribution(df, column=column)
    entropy_stats = summarize_entropy(df)
    fig_summ = make_entropy_summary_indicators(entropy_stats)
    renderer = get_entropy_simple_text_renderer(entropy_stats)

    return fig_line, fig_hist, fig_summ, renderer
