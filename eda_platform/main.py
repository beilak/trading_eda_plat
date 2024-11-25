import copy
import typing as tp

import pandas as pd
import streamlit as st
import altair as alt
import plotly.graph_objects as go
import plotly.express as px

from scipy.stats import normaltest


from cross_analyses_tab import draw_cross_analyses_tab

from data_providers.data_provider_ioc import DATA_PROVIDER
from data_providers.provider import MarketProvider


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


def make_column_hist(df: pd.DataFrame, column: str):
    normal_text = make_normal_test_text(df, column)

    fig = px.histogram(df, x=column)
    fig.update_traces(textposition="inside", textfont_size=8)
    fig.update_layout(title=dict(text=normal_text))
    return fig


def make_column_boxplot(df: pd.DataFrame, column):
    fig = go.Figure()
    fig.add_trace(go.Box(x=df[column], name=column))
    return fig


def make_return(df: pd.DataFrame, column: str):
    returns = df.copy()
    returns[column] = returns[column].pct_change()
    returns = returns.dropna()
    return returns[["date", column]]


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


def draw_ohlc_tabs(df: pd.DataFrame, context):
    tabs = ["open", "high", "low", "close", "volume"]

    for tab, name in zip(context.tabs(tabs), tabs):
        tab_col_0, tab_col_1 = tab.columns((1, 1), gap="small")

        tab_col_0.plotly_chart(make_column_hist(df, name), use_container_width=True)
        tab_col_1.plotly_chart(make_column_boxplot(df, name), use_container_width=True)

        returns = make_return(df, name)
        tab_col_0.plotly_chart(
            make_return_line(returns, name), use_container_width=True
        )
        tab_col_1.plotly_chart(
            make_column_hist(returns, name), use_container_width=True
        )

        tab.plotly_chart(make_total_changes(df, name), use_container_width=True)
        # make_total_changes(df, name, tab)


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
        draw_ohlc_tabs(selected_ohlcv, tab_selected_symbol)
        tab_selected_symbol.markdown("---")

    if len(selected_symbols) > 1:
        cross_analyses_tab = main_tabs[-1]
        draw_cross_analyses_tab(
            cross_analyses_tab, selected_exchange, selected_symbols, selected_time_frame
        )
