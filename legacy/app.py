import os
import sys
import datetime
import pandas as pd
import streamlit as st
import akshare as ak
from openai import OpenAI

# -----------------------------------------------------------------------------
# 1. 强制清除 Python 进程内的代理环境变量（防止关闭 VPN 后系统代理残留导致断连）
# -----------------------------------------------------------------------------
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

# -----------------------------------------------------------------------------
# 2. 页面基础属性配置
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="沪深300数据研报看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 3. 数据抓取与异常降级处理（含代理屏蔽与降级UI）
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def load_csi300_data():
    """抓取沪深300成份股全量数据及实时行情"""
    try:
        # 抓取中证指数官网沪深300成份股名单
        cons_df = ak.index_stock_cons_csindex(symbol="000300")
        # 抓取全A股实时行情数据
        spot_df = ak.stock_zh_a_spot_em()
        
        # 补全代码格式
        cons_df['成分券代码'] = cons_df['成分券代码'].astype(str).str.zfill(6)
        spot_df['代码'] = spot_df['代码'].astype(str).str.zfill(6)
        
        # 数据表合并
        merged_df = pd.merge(
            cons_df[['成分券代码', '成分券名称', '交易所']], 
            spot_df, 
            left_on='成分券代码', 
            right_on='代码', 
            how='left'
        )
        
        # 提取目标列
        target_columns = ['代码', '成分券名称', '最新价', '涨跌幅', '涨跌额', '成交量', '成交额', '市盈率-动态', '总市值']
        result_df = merged_df[target_columns].copy()
        result_df.columns = ['股票代码', '公司名称', '最新价(元)', '涨跌幅(%)', '涨跌额(元)', '成交量(手)', '成交额(元)', '市盈率(PE)', '总市值(元)']
        
        # 数值类型清洗
        result_df['涨跌幅(%)'] = pd.to_numeric(result_df['涨跌幅(%)'], errors='coerce').fillna(0.0)
        result_df['最新价(元)'] = pd.to_numeric(result_df['最新价(元)'], errors='coerce').fillna(0.0)
        result_df['总市值(元)'] = pd.to_numeric(result_df['总市值(元)'], errors='coerce').fillna(0.0)
        
        return result_df, "数据更新成功 (数据源: 东方财富实时接口)"
    except Exception as err:
        # 发生网络断开、超时或服务端拒绝时触发离线降级
        fallback_data = pd.DataFrame([
            {"股票代码": "600519", "公司名称": "贵州茅台", "最新价(元)": 1700.00, "涨跌幅(%)": 1.52, "涨跌额(元)": 25.5, "成交量(手)": 32000, "成交额(元)": 5440000000, "市盈率(PE)": 30.2, "总市值(元)": 2130000000000},
            {"股票代码": "000858", "公司名称": "五 粮 液", "最新价(元)": 140.50, "涨跌幅(%)": -0.85, "涨跌额(元)": -1.2, "成交量(手)": 51000, "成交额(元)": 716000000, "市盈率(PE)": 20.5, "总市值(元)": 545000000000},
            {"股票代码": "300750", "公司名称": "宁德时代", "最新价(元)": 192.30, "涨跌幅(%)": 3.15, "涨跌额(元)": 5.8, "成交量(手)": 85000, "成交额(元)": 1630000000, "市盈率(PE)": 24.1, "总市值(元)": 846000000000},
            {"股票代码": "601318", "公司名称": "中国平安", "最新价(元)": 45.10, "涨跌幅(%)": -0.22, "涨跌额(元)": -0.1, "成交量(手)": 92000, "成交额(元)": 414000000, "市盈率(PE)": 9.8, "总市值(元)": 820000000000},
            {"股票代码": "600036", "公司名称": "招商银行", "最新价(元)": 32.80, "涨跌幅(%)": 0.45, "涨跌额(元)": 0.15, "成交量(手)": 78000, "成交额(元)": 255000000, "市盈率(PE)": 5.6, "总市值(元)": 827000000000}
        ])
        return fallback_data, f"网络请求受阻，已启动安全数据模式 (原因: {str(err)})"

# -----------------------------------------------------------------------------
# 4. AI 研报生成模块
# -----------------------------------------------------------------------------
def fetch_ai_report(api_key: str, data_summary: str) -> str:
    if not api_key.strip():
        return "⚠️ 请先在侧边栏输入有效的 DeepSeek API Key。"
    
    try:
        client = OpenAI(
            api_key=api_key.strip(),
            base_url="https://api.deepseek.com"
        )
        prompt = f"基于以下沪深 300 成分股统计数据撰写行情分析报告：\n{data_summary}"
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一位专业的金融分析师。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ AI 研报生成失败: {str(e)}"

# -----------------------------------------------------------------------------
# 5. UI 渲染逻辑
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 系统配置")
    deepseek_key = st.text_input("DeepSeek API Key", type="password")
    st.markdown("---")
    if st.button("🔄 刷新数据"):
        st.cache_data.clear()
        st.rerun()

st.title("📊 沪深 300 成分股自动化数据与研报中心")
st.caption(f"运行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with st.spinner("数据加载中..."):
    df, status_msg = load_csi300_data()

if "数据更新成功" in status_msg:
    st.success(status_msg)
else:
    st.warning(status_msg)

total_count = len(df)
up_count = len(df[df['涨跌幅(%)'] > 0])
down_count = len(df[df['涨跌幅(%)'] < 0])
flat_count = total_count - up_count - down_count
avg_change = df['涨跌幅(%)'].mean()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("监控成分股总数", f"{total_count} 家")
col2.metric("上涨家数", f"{up_count} 家", delta=f"{up_count}")
col3.metric("下跌家数", f"{down_count} 家", delta=f"-{down_count}", delta_color="inverse")
col4.metric("平盘家数", f"{flat_count} 家")
col5.metric("成分股平均涨跌幅", f"{avg_change:.2f}%")

st.markdown("---")

tab_data, tab_ai = st.tabs(["📈 行情列表", "🤖 AI 研报"])

with tab_data:
    st.dataframe(df, use_container_width=True, hide_index=True, height=500)

with tab_ai:
    summary_text = f"总数:{total_count}, 上涨:{up_count}, 下跌:{down_count}, 均幅:{avg_change:.2f}%"
    if st.button("🚀 生成分析报告", type="primary"):
        with st.spinner("研报撰写中..."):
            res = fetch_ai_report(deepseek_key, summary_text)
            st.markdown(res)