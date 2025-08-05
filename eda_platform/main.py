import copy
import typing as tp

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
import plotly.graph_objects as go
import plotly.express as px

from scipy.stats import normaltest
from scipy import stats


from cross_analyses_tab import draw_cross_analyses_tab

from data_providers.data_provider_ioc import DATA_PROVIDER
from data_providers.provider import MarketProvider
from adtk.detector import QuantileAD

from entropy import make_shannon_entropy

# from eda_platform.entropy import make_shannon_entropy

st.set_page_config(
    page_title="EDA platform",
    page_icon="🏂",  # ToDo Find correct icon
    layout="wide",
    initial_sidebar_state="expanded",
)
alt.theme.enable("dark")

exchanges_provider = DATA_PROVIDER.exchanges_provider

TIME_FRAMES: tp.Final = [
    "1h",
    "4h",
    "8h",
    "12h",
    "1d",
    "3d",
    "1w",
    "1M",
]  # ToDo replace to class


with st.sidebar:
    st.title("🏂 EDA Platform")

    st.subheader("Select")

    exchanges: list[str] = exchanges_provider.exchanges
    selected_exchange = st.selectbox("Exchange", exchanges)

    market_provider: tp.Final[MarketProvider] = exchanges_provider.get_market_provider(
        selected_exchange
    )
    symbols: list[set] = market_provider.symbols
    #

    selected_symbols = st.multiselect(
        "Symbol",
        symbols,
    )
    # selected_symbol = selected_symbols[0]

    # selected_symbol = st.selectbox('Symbol', symbols)
    #
    # selected_time_frame = st.selectbox('TimeFrame', market_provider.time_frame)
    selected_time_frame = st.selectbox("TimeFrame", TIME_FRAMES, index=4)

    # selected_ohlcv: pd.DataFrame = exchanges_provider.get_market_provider(
    #     selected_exchange,
    # ).fetch_ohlcv(selected_symbol, selected_time_frame)


def make_ohlc(df: pd.DataFrame) -> go.Figure:
    return go.Figure(
        data=go.Ohlc(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
        ),
    )


def draw_data_describe(df: pd.DataFrame, context) -> None:
    describe: pd.DataFrame = df[["open", "high", "low", "close", "volume"]].describe()
    context.subheader("Describe")
    context.dataframe(describe, use_container_width=True)


def draw_ohlc_head(df: pd.DataFrame, context) -> None:
    context.subheader("Data example")
    context.dataframe(
        df.tail(),
        use_container_width=True,
        column_order=["date", "open", "high", "low", "close", "volume"],
        hide_index=True,
    )


def make_normal_test_text(df: pd.DataFrame, column):
    stat, p = normaltest(df[column])
    text = "NOT Normal distribution"
    if p > 0.05:
        text = "Normal distribution"
    text += f" [ p_value = { p } ]"
    return text


def make_column_hist(df: pd.DataFrame, column: str) -> go.Figure:
    normal_text = make_normal_test_text(df, column)

    fig = px.histogram(df, x=column)
    fig.update_traces(textposition="inside", textfont_size=8)
    fig.update_layout(title=dict(text=normal_text))
    return fig


def make_column_boxplot(df: pd.DataFrame, column) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Box(x=df[column], name=column))
    return fig


def make_return(df: pd.DataFrame, column: str):
    returns = df.copy()
    returns[column] = returns[column].pct_change()
    returns = returns.dropna()
    return returns[["date", column]]

def make_rolling_volatility(returns, column: str, rolling_volatility_candle_count) -> go.Figure:
    rolling_volatility = returns.copy()
    rolling_volatility[column] = returns[column].rolling(window=rolling_volatility_candle_count).std() * np.sqrt(252)
    rolling_volatility = rolling_volatility.dropna()
    return rolling_volatility[["date", column]]


def make_norm_distribution(df: pd.DataFrame, column: str) -> go.Figure:
    # 3. Применяем преобразование к одному столбцу, например 'Close'
    df_lock = df.copy()
    df_lock[column], best_lambda = stats.boxcox(df_lock[column])
    fig = px.histogram(df_lock, x=column)
    fig.update_traces(textposition="inside", textfont_size=8)
    fig.update_layout(title=f"BoxCox transformed distribution. λ = { best_lambda } [{column}]")

    return fig

def make_return_line(returns: pd.DataFrame, column: str):
    fig = px.line(returns, x="date", y=column, title=f"Return [{column}]")
    return fig


def make_total_changes(df: pd.DataFrame, column):
    column_val = df[column]
    b = column_val.iloc[-1]
    a = column_val.iloc[0]
    fig = go.Figure()
    fig.add_trace(
        go.Indicator(
            mode="delta",
            value=b,
            delta={"reference": a, "relative": True},
            title={"text": f"Total percentage change [ { column } ]"},
        )
    )
    return fig


def make_rolling_volatility_line(rolling_volatility, column: str) -> go.Figure:
    fig = px.line(rolling_volatility, x="date", y=column, title=f"Rolling volatility [{column}]")
    return fig


def make_anomaly_detection(df: pd.DataFrame, column: str,  anomaly_detect_low_perc, anomaly_detect_high_perc) -> go.Figure:
    price_series = df[["date",column]].copy()
    price_series.date = pd.to_datetime(price_series.date)
    price_series.set_index("date", inplace=True)

    quantile_ad_price = QuantileAD(high=anomaly_detect_high_perc, low=anomaly_detect_low_perc)
    # Находим аномалии
    price_anomalies = quantile_ad_price.fit_detect(price_series)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=price_series.index, y=price_series[column], mode="lines", name="TS"
        )
    )

    anomaly_points = price_series[price_anomalies]

    fig.add_trace(
        go.Scatter(
            x=anomaly_points.index,
            y=anomaly_points[column],
            mode="markers",
            name="Аномалия",
            marker=dict(color="red", size=10, symbol="x"),
        )
    )

    fig.update_layout(
        title="Anomaly detections",
        xaxis_title="Date",
        yaxis_title=f"[{column}]",
        xaxis_rangeslider_visible=True,
        template="plotly_white",  # Используем чистую белую тему !!!!
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
        ),
    )
    return fig







def draw_ohlc_tabs(df: pd.DataFrame, context, selected_symbol):
    tabs = ["open", "high", "low", "close", "volume"]

    for tab, name in zip(context.tabs(tabs), tabs):
        tab_col_0, tab_col_1 = tab.columns((1, 1), gap="small")

        tab_col_0.title(f"Distribution of [{name}]")
        tab_col_0.plotly_chart(make_column_hist(df, name), use_container_width=True)

        tab_col_1.title(f"Distribution BoxPlot of [{name}]")
        tab_col_1.plotly_chart(make_column_boxplot(df, name), use_container_width=True)

        returns = make_return(df, name)
        tab_col_0.title(f"Return [{name}]")
        tab_col_0.plotly_chart(
            make_return_line(returns, name), use_container_width=True
        )

        tab_col_1.title(f"Distribution returns of [{name}]")
        tab_col_1.plotly_chart(
            make_column_hist(returns, name), use_container_width=True
        )

        try:
            tab_col_1.plotly_chart(
                make_norm_distribution(df, name), use_container_width=True
            )
        except Exception:
            ...

        rolling_volatility_candle_count = tab_col_0.number_input(
            key=f"rolling_volatility_candle_count_{selected_symbol}_{name}",
            label="Rolling volatility bur candle",
            min_value=1,
            max_value=365,
            value=30,
            step=1,
        )
        rolling_volatility = make_rolling_volatility(returns, name, rolling_volatility_candle_count)
        tab_col_0.plotly_chart(
            make_rolling_volatility_line(rolling_volatility, name), use_container_width=True
        )

        tab.plotly_chart(make_total_changes(df, name), use_container_width=True)
        # make_total_changes(df, name, tab)


        anomaly_detect_low_perc = tab.number_input(
            key=f"anomaly_detect_low_{selected_symbol}_{name}",
            label="Low percentile",
            min_value=0.00,
            max_value=1.00,
            value=0.05,
            step=0.01,
        )
        anomaly_detect_high_perc = tab.number_input(
            key=f"anomaly_detect_high_{selected_symbol}_{name}",
            label="High percentile",
            min_value=0.00,
            max_value=1.00,
            value=0.95,
            step=0.01,
        )
        tab.plotly_chart(
            make_anomaly_detection(df, name, anomaly_detect_low_perc, anomaly_detect_high_perc), use_container_width=True
        )


        shannon_entropy_window = tab.number_input(
            key=f"shannon_entropy_window_{selected_symbol}_{name}",
            label="Shannon entropy window",
            min_value=2,
            max_value=100,
            value=20,
            step=1,
        )

        entropy_line, entropy_hist, entropy_summ, render = make_shannon_entropy(selected_ohlcv, name, window=shannon_entropy_window)
        tab.plotly_chart(entropy_line)
        tab.plotly_chart(entropy_hist)
        cols = tab.columns(len(entropy_summ))

        for i, (idc, fig) in enumerate(entropy_summ.items()):
            cols[i].plotly_chart(fig, use_container_width=True, key=f"idc_{selected_symbol}_{idc}_{name}")

        render(tab)

# col = st.columns((5, 1), gap='medium')

if selected_symbols:
    main_tabs_names = copy.deepcopy(selected_symbols)
    if len(selected_symbols) > 1:
        main_tabs_names.append("Cross Analyses")
    main_tabs = st.tabs(main_tabs_names)
    # with col[0]:
    for tab_selected_symbol, selected_symbol in zip(main_tabs, selected_symbols):

        selected_ohlcv: pd.DataFrame = exchanges_provider.get_market_provider(
            selected_exchange,
        ).fetch_ohlcv(selected_symbol, selected_time_frame)

        tab_selected_symbol.header(
            f"{selected_exchange }  :blue[[{ selected_symbol }]]"
        )
        tab_selected_symbol.markdown("---")
        tab_selected_symbol.subheader(f"OHLC  :blue[[{ selected_time_frame }]]")
        ohlc_figur: go.Figure = make_ohlc(selected_ohlcv)
        tab_selected_symbol.plotly_chart(ohlc_figur, use_container_width=True)

        draw_data_describe(selected_ohlcv, tab_selected_symbol)
        draw_ohlc_head(selected_ohlcv, tab_selected_symbol)

        tab_selected_symbol.markdown("---")
        draw_ohlc_tabs(selected_ohlcv, tab_selected_symbol, selected_symbol)
        tab_selected_symbol.markdown("---")


    if len(selected_symbols) > 1:
        cross_analyses_tab = main_tabs[-1]
        draw_cross_analyses_tab(
            cross_analyses_tab, selected_exchange, selected_symbols, selected_time_frame
        )
