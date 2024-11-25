import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from data_providers.data_provider_ioc import DATA_PROVIDER


exchanges_provider = DATA_PROVIDER.exchanges_provider


def draw_line(ohlc: dict[str, pd.DataFrame], column):
    fig = go.Figure()
    for ticker, df in ohlc.items():
        fig.add_trace(
            go.Scatter(x=df.date, y=df[column], name=f"{ticker} [{ column }]")
        )

    st.plotly_chart(fig, use_container_width=True)


def draw_heatmaps(ohlc: dict[str, pd.DataFrame], column):
    tab_df = pd.DataFrame()
    any_key: str = list(ohlc.keys())[0]
    tab_df.index = ohlc[any_key].index
    for ticker, df in ohlc.items():
        tab_df[ticker] = df[column]

    fig = px.imshow(tab_df.corr(method="spearman"), text_auto=True, aspect="auto")

    fig.update_xaxes(side="top")
    st.dataframe(tab_df.corr(method="spearman"), use_container_width=True)
    st.plotly_chart(fig, use_container_width=True)


def draw_total_changes(ohlc: dict[str, pd.DataFrame], column):

    total_diff: dict = {}

    for ticker, df in ohlc.items():
        column_val = df[column]
        b = column_val.iloc[-1]
        a = column_val.iloc[0]
        total_diff[ticker] = (b - a) / a * 100

    tab_df = pd.DataFrame.from_dict(total_diff, orient="index", columns=["total"])
    tab_df["name"] = tab_df.index

    fig = px.bar(
        tab_df,
        x="name",
        y="total",
        color="total",
        labels={"total": "Total percentage change", "name": ""},
        height=800,
    )

    st.plotly_chart(fig, use_container_width=True)


def draw_df(ohlc: dict[str, pd.DataFrame], column):
    tab_df = pd.DataFrame()
    any_key: str = list(ohlc.keys())[0]
    tab_df.index = ohlc[any_key].index
    for ticker, df in ohlc.items():
        tab_df[ticker] = df[column]
    st.dataframe(tab_df)


def draw_ohlc_tabs(ohlc: dict[str, pd.DataFrame]):
    st.markdown("---")

    tabs = ["open", "high", "low", "close", "volume"]

    for tab, name in zip(st.tabs(tabs), tabs):
        with tab:
            draw_df(ohlc, name)
            draw_line(ohlc, name)
            draw_heatmaps(ohlc, name)
            draw_total_changes(ohlc, name)


def draw_return_tabs(ohlc_return: dict[str, pd.DataFrame]):
    st.markdown("---")
    st.markdown("### Changes")

    tabs = ["open", "high", "low", "close", "volume"]

    for tab, name in zip(st.tabs(tabs), tabs):
        with tab:
            draw_df(ohlc_return, name)
            draw_heatmaps(ohlc_return, name)


def calc_returns(df: pd.DataFrame) -> pd.DataFrame:
    for columns in ["open", "high", "low", "close", "volume"]:
        df[columns] = df[columns].pct_change()
    return df


def draw_cross_analyses_tab(
    context,
    selected_exchange: str,
    selected_symbols: str,
    selected_time_frame: str,
):
    all_ohlcv: dict[str, pd.DataFrame] = {}
    all_ohlcv_return: dict[str, pd.DataFrame] = {}

    for selected_symbol in selected_symbols:
        selected_ohlcv: pd.DataFrame = exchanges_provider.get_market_provider(
            selected_exchange,
        ).fetch_ohlcv(selected_symbol, selected_time_frame)

        all_ohlcv[selected_symbol] = selected_ohlcv
        all_ohlcv_return[selected_symbol] = selected_ohlcv.copy()
        all_ohlcv_return[selected_symbol] = calc_returns(
            all_ohlcv_return[selected_symbol]
        )

    with context:
        st.header(f"{selected_exchange}  :blue[[{ ", ".join(selected_symbols) }]]")
        draw_ohlc_tabs(all_ohlcv)

        draw_return_tabs(all_ohlcv_return)
