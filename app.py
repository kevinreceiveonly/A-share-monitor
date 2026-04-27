import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ----------------------------- 页面配置 -----------------------------
st.set_page_config(page_title="沪深300/创业板指比价监控", layout="wide")
st.title("📊 沪深300 vs 创业板指 比价走势")
st.markdown("""
**说明：**  
- 比价 = 沪深300指数收盘价 ÷ 创业板指数收盘价  
- 比值 **上升** → 沪深300相对走强  
- 比值 **下降** → 创业板相对走强  
- 数据起始于 **2010年6月1日**（创业板指数发布日）  
""")

# ----------------------------- 数据获取函数 -----------------------------
@st.cache_data(ttl=3600 * 12)  # 缓存12小时，避免频繁请求
def fetch_index_data(symbol: str, name: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    使用 akshare 获取指数日线数据，并筛选日期范围。
    symbol: 如 'sh000300'、'sz399006'
    name: 用于列名标识，如 'hs300'、'cyb'
    """
    try:
        # 获取历史日线，columns 示例：date, open, close, high, low, volume
        df = ak.stock_zh_index_daily(symbol=symbol)

        if df is None or df.empty:
            st.error(f"获取{name}数据为空，请检查指数代码或网络。")
            return pd.DataFrame()

        # 统一列名为小写，方便处理
        df.columns = [c.lower() for c in df.columns]

        if "date" not in df.columns:
            st.error(f"{name}数据缺少日期列，无法使用。")
            return pd.DataFrame()

        # 格式化日期
        df["date"] = pd.to_datetime(df["date"])
        # 筛选指定区间
        mask = (df["date"] >= start_date) & (df["date"] <= end_date)
        df = df.loc[mask].copy()

        if "close" not in df.columns:
            st.error(f"{name}数据缺少收盘价列。")
            return pd.DataFrame()

        # 只保留日期和收盘价，并重命名收盘价列
        return df[["date", "close"]].rename(columns={"close": f"{name}_close"})

    except Exception as e:
        st.error(f"获取{name}数据时出错：{e}")
        return pd.DataFrame()

# ----------------------------- 主逻辑 -----------------------------
# 日期范围：创业板指数发布日 2010-06-01 至今日
start_dt = datetime(2010, 6, 1)
end_dt = datetime.now()

end_date_str = end_dt.strftime("%Y%m%d")
start_date_str = start_dt.strftime("%Y%m%d")

# 获取两个指数的收盘价数据
df_hs300 = fetch_index_data("sh000300", "hs300", start_date_str, end_date_str)
df_cyb = fetch_index_data("sz399006", "cyb", start_date_str, end_date_str)

# 如果数据都获取成功，则进行后续处理
if not df_hs300.empty and not df_cyb.empty:
    # 按日期对齐
    merged = pd.merge(df_hs300, df_cyb, on="date", how="inner")

    if merged.empty:
        st.warning("两个指数在指定周期内没有共同的交易日，无法计算比价。")
    else:
        # 按日期升序排列
        merged = merged.sort_values("date").reset_index(drop=True)

        # 计算比值
        merged["ratio"] = merged["hs300_close"] / merged["cyb_close"]

        # ------------------------- Plotly 交互式折线图 -------------------------
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=merged["date"],
                y=merged["ratio"],
                mode="lines",
                name="沪深300 / 创业板指",
                line=dict(color="#1f77b4", width=2),
                hovertemplate="日期: %{x|%Y-%m-%d}<br>比值: %{y:.4f}<extra></extra>",
            )
        )
        fig.update_layout(
            title="沪深300指数 / 创业板指数 比价走势（自2010年6月1日至今）",
            xaxis_title="日期",
            yaxis_title="比值",
            hovermode="x unified",
            template="plotly_white",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

        # ------------------------- 最新比值与变化 -------------------------
        latest = merged.iloc[-1]
        prev = merged.iloc[-2] if len(merged) > 1 else None

        current_ratio = latest["ratio"]
        latest_date = latest["date"].strftime("%Y-%m-%d")

        if prev is not None:
            change = current_ratio - prev["ratio"]
            st.metric(
                label=f"📅 最新比值 ({latest_date})",
                value=f"{current_ratio:.4f}",
                delta=f"{change:.4f}",
            )
            if change > 0:
                direction = "📈 比值上升，沪深300相对走强"
            elif change < 0:
                direction = "📉 比值下降，创业板相对走强"
            else:
                direction = "➡️ 比值持平"
            st.caption(f"较前一交易日变化：{direction}")
        else:
            st.metric(
                label=f"📅 最新比值 ({latest_date})",
                value=f"{current_ratio:.4f}",
            )
else:
    st.warning("数据获取失败，请检查网络连接或稍后再试。")

# ----------------------------- 页脚 -----------------------------
st.markdown("---")
st.caption("数据来源：东方财富 (通过 AKShare)  |  仅供学习参考，不构成任何投资建议。")
