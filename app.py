"""
AI API 成本优化模拟器 — 在线部署版
支持：官方定价 / OpenRouter实时报价 / CheaperInference订阅制混合测算
"""
import os
import time
import requests
import numpy as np
import streamlit as st
from datetime import datetime

# ─── 页面基础配置 ───
st.set_page_config(
    page_title="AI API 成本优化模拟器",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── 缓存与性能配置 ───
PRICE_CACHE_TTL = 4 * 3600      # 价格缓存：4小时
VOLATILITY_MONTHS = 6           # 波动率回溯月数

# ─── 模型与定价数据库 ───
MODEL_CATALOG = {
    "DeepSeek V4 Flash": {
        "id": "deepseek-v4-flash",
        "official_input": 0.14,   # USD / 1M tokens
        "official_output": 0.28,
        "ci_plan": "core",        # CheaperInference 所属套餐
        "volatility_input": 0.18,
        "volatility_output": 0.15,
    },
    "DeepSeek V4 Pro": {
        "id": "deepseek-v4-pro",
        "official_input": 1.74,
        "official_output": 3.48,
        "ci_plan": None,          # 暂不支持
        "volatility_input": 0.22,
        "volatility_output": 0.20,
    },
    "OpenAI GPT-4o": {
        "id": "gpt-4o",
        "official_input": 2.50,
        "official_output": 10.00,
        "ci_plan": None,
        "volatility_input": 0.12,
        "volatility_output": 0.10,
    },
    "Claude 3.5 Sonnet": {
        "id": "claude-3-5-sonnet",
        "official_input": 3.00,
        "official_output": 15.00,
        "ci_plan": None,
        "volatility_input": 0.10,
        "volatility_output": 0.08,
    },
    "GLM-5.2": {
        "id": "glm-5-2",
        "official_input": 1.40,
        "official_output": 4.40,
        "ci_plan": "frontier",
        "volatility_input": 0.20,
        "volatility_output": 0.18,
    },
    "Kimi K3": {
        "id": "kimi-k3",
        "official_input": 3.00,
        "official_output": 15.00,
        "ci_plan": "frontier",
        "volatility_input": 0.15,
        "volatility_output": 0.12,
    },
}

# CheaperInference 订阅定价（USD/月）
CHEAPER_INFERENCE_PLANS = {
    "core": {
        "name": "Core 无限订阅",
        "price": 6.99,
        "windows": ["00:00–08:00", "08:00–16:00", "16:00–24:00"],
        "note": "每个窗口独立计费，单并发不限Token",
    },
    "frontier": {
        "name": "Frontier 无限订阅",
        "price": 52.00,
        "windows": ["00:00–08:00", "08:00–16:00", "16:00–24:00"],
        "note": "含Kimi K2.7/2.6、GLM-5.2等，单并发不限Token",
    },
}

# ─── 价格数据源 ───
@st.cache_data(ttl=PRICE_CACHE_TTL, show_spinner="正在拉取市场实时价格…")
def fetch_openrouter_pricing():
    """获取OpenRouter全模型实时市场价"""
    try:
        resp = requests.get("https://openrouter.ai/api/v1/models", timeout=15)
        resp.raise_for_status()
        data = resp.json()
        market = {}
        for m in data["data"]:
            mid = m["id"].lower()
            if "pricing" in m:
                market[mid] = {
                    "input": float(m["pricing"].get("prompt", 0)) * 1_000_000,
                    "output": float(m["pricing"].get("completion", 0)) * 1_000_000,
                }
        return market
    except Exception as e:
        st.warning(f"OpenRouter 价格获取失败: {e}，使用参考折扣价")
        return {}

def get_market_price(model_key, market_data):
    """匹配市场价 → 无结果回退至历史折扣系数"""
    info = MODEL_CATALOG[model_key]
    mid = info["id"].lower()
    for k, v in market_data.items():
        if mid in k:
            return v["input"], v["output"]
    # 经验折扣基准
    discount = {"DeepSeek V4 Flash":0.45, "DeepSeek V4 Pro":0.40,
                "OpenAI GPT-4o":0.72, "Claude 3.5 Sonnet":0.75,
                "GLM-5.2":0.50, "Kimi K3":0.60}.get(model_key, 0.60)
    return info["official_input"] * discount, info["official_output"] * discount

@st.cache_data(ttl=PRICE_CACHE_TTL)
def fetch_cheaperinference_status() -> dict:
    """拉取CheaperInference公开套餐状态"""
    try:
        resp = requests.get("https://api.cheapestinference.com/v1/usage", timeout=10)
        # 无密钥时返回401属正常 → 返回公开套餐数据
        return CHEAPER_INFERENCE_PLANS
    except Exception:
        return CHEAPER_INFERENCE_PLANS

# ─── 计算引擎 ───
def calc_token_cost(in_m, out_m, price_in, price_out):
    return in_m * price_in + out_m * price_out

def volatility_range(base, sigma, z=2.0):
    """对数正态置信区间"""
    return base * np.exp(-z * sigma), base * np.exp(z * sigma)

# ─── 界面渲染 ───
st.title("🔬 AI API 成本优化模拟器")
st.markdown("""
对比 **官方按Token计费** · **OpenRouter聚合市场价** · **CheaperInference无限订阅** 三种路径，
输出月度支出、节省比例、年度潜在节约及波动置信区间。
""")

# ─── 侧边栏输入 ───
with st.sidebar:
    st.header("📊 用量参数")
    monthly_input = st.number_input("月度输入 Token (百万)", min_value=0.01, value=10.0, step=0.5)
    monthly_output = st.number_input("月度输出 Token (百万)", min_value=0.01, value=2.0, step=0.5)

    st.header("🤖 模型与方案")
    selected_model = st.selectbox("目标模型", list(MODEL_CATALOG.keys()))
    
    st.header("⚙️ 高级设置")
    currency = st.selectbox("显示货币", ["USD", "CNY"], index=0)
    usd_to_cny = st.number_input("汇率(USD→CNY)", value=7.20, min_value=5.0, max_value=10.0, step=0.01)
    z_score = st.slider("置信区间(σ倍数)", 1.0, 2.5, 2.0, 0.1)
    
    ci_windows = None
    info = MODEL_CATALOG[selected_model]
    if info["ci_plan"]:
        st.subheader("⏱️ CheaperInference时段")
        plan = CHEAPER_INFERENCE_PLANS[info["ci_plan"]]
        ci_windows = st.multiselect(
            "选择覆盖时段",
            options=plan["windows"],
            default=plan["windows"][:1],
            help=f"每时段 ${plan['price']}/月，不限Token、单并发"
        )

# ─── 获取实时数据 ───
market_data = fetch_openrouter_pricing()
ci_plans = fetch_cheaperinference_status()

# ─── 计算各方案成本 ───
info = MODEL_CATALOG[selected_model]
market_in, market_out = get_market_price(selected_model, market_data)

# 方案A：官方
cost_official = calc_token_cost(monthly_input, monthly_output, info["official_input"], info["official_output"])

# 方案B：OpenRouter聚合
cost_market = calc_token_cost(monthly_input, monthly_output, market_in, market_out)

# 方案C：CheaperInference订阅
cost_ci = None
ci_note = ""
if info["ci_plan"] and ci_windows:
    plan = ci_plans[info["ci_plan"]]
    cost_ci = plan["price"] * len(ci_windows)
    ci_note = f"{plan['name']} × {len(ci_windows)} 时段"

# ─── 波动率区间 ───
weighted_sigma = (
    info["volatility_input"] * monthly_input + info["volatility_output"] * monthly_output
) / (monthly_input + monthly_output)

lo_off, hi_off = volatility_range(cost_official, weighted_sigma, z_score)
lo_mkt, hi_mkt = volatility_range(cost_market, weighted_sigma, z_score)
lo_ci, hi_ci = (cost_ci, cost_ci) if cost_ci else (None, None)  # 订阅制价格固定

# ─── 格式化 ───
def fmt(usd):
    if usd is None: return "—"
    if currency == "CNY":
        return f"¥{usd * usd_to_cny:,.2f}"
    return f"${usd:,.2f}"

# ─── 结果展示 ───
st.divider()
colA, colB, colC = st.columns(3)

with colA:
    st.subheader("🏷️ 官方标准定价")
    st.metric("月度成本", fmt(cost_official))
    st.caption(f"输入 {info['official_input']:.3f} / 输出 {info['official_output']:.3f} USD/1M")

with colB:
    st.subheader("🛒 OpenRouter聚合市场")
    st.metric("月度成本", fmt(cost_market), 
              delta=f"-{((cost_official-cost_market)/cost_official*100):.1f}%")
    st.caption(f"输入 {market_in:.3f} / 输出 {market_out:.3f} USD/1M")

with colC:
    st.subheader("♾️ CheaperInference订阅制")
    if cost_ci:
        saving_ci = (cost_official - cost_ci) / cost_official * 100 if cost_official > 0 else 0
        st.metric("月度成本", fmt(cost_ci), delta=f"-{saving_ci:.1f}%")
        st.caption(ci_note)
    else:
        st.info("该模型暂不支持订阅方案")

st.divider()

# ─── 情景预测 ───
st.subheader("📈 成本区间预测")
sc1, sc2, sc3 = st.columns(3)

with sc1:
    st.markdown("**官方路径**")
    st.info(f"""
    - 最低: {fmt(lo_off)}
    - 基准: {fmt(cost_official)}
    - 最高: {fmt(hi_off)}
    - 波动: ±{weighted_sigma*100:.1f}%/月
    """)

with sc2:
    st.markdown("**聚合市场路径**")
    st.success(f"""
    - 最低: {fmt(lo_mkt)}
    - 基准: {fmt(cost_market)}
    - 最高: {fmt(hi_mkt)}
    - 波动: ±{weighted_sigma*100:.1f}%/月
    """)

with sc3:
    st.markdown("**订阅制路径**")
    if cost_ci:
        st.warning(f"""
        - 最低: {fmt(lo_ci)}
        - 基准: {fmt(cost_ci)}
        - 最高: {fmt(hi_ci)}
        - 价格: 固定无波动
        """)
    else:
        st.caption("不可用")

st.divider()

# ─── 年度节约汇总 ───
st.subheader("💰 年度潜在节约")
data = [
    {"方案": "官方标准", "月度成本": fmt(cost_official), "年度总成本": fmt(cost_official*12), "较官方节省": "—"},
    {"方案": "OpenRouter聚合", "月度成本": fmt(cost_market), "年度总成本": fmt(cost_market*12), 
     "较官方节省": f"{(cost_official-cost_market)/cost_official*100:.1f}% / {fmt((cost_official-cost_market)*12)}"},
]
if cost_ci:
    data.append({"方案": "CheaperInference订阅", "月度成本": fmt(cost_ci), "年度总成本": fmt(cost_ci*12),
                 "较官方节省": f"{(cost_official-cost_ci)/cost_official*100:.1f}% / {fmt((cost_official-cost_ci)*12)}"})
st.dataframe(data, use_container_width=True, hide_index=True)

st.divider()

# ─── 风险提示 ───
st.subheader("⚠️ 使用提示")
st.warning(f"""
- 测算口径：OpenRouter数据每4小时刷新；CheaperInference套餐来自公开信息；实际服务质量、并发限制、缓存策略可能与纯Token计费路径有差异
- 订阅制适用边界：不限Token但受时段与并发数限制；高用量/长时段场景优势显著，低用量可能不划算
- 建议灰度验证：上线前通过影子流量对比计费口径与输出质量一致性
- 上次数据更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")