# 🔬 AI API 成本优化模拟器

对比 **官方按 Token 计费** · **OpenRouter 聚合市场价** · **CheaperInference 无限订阅** 三种路径，
输出月度支出、节省比例、年度潜在节约及价格波动置信区间，帮你把 AI 调用成本算明白。

> 在线版（Streamlit 部署后即可访问）。本地运行见下方「快速开始」。

---

## ✨ 功能特性

- **三方案同屏对比**：官方标准定价 / OpenRouter 实时聚合市场价 / CheaperInference 订阅制，三个卡片并排，差异一眼可见。
- **实时市场价拉取**：自动从 OpenRouter 公开 API 获取全模型实时报价（每 4 小时缓存），失败则回退到内置参考折扣价。
- **波动置信区间**：基于各模型历史波动率，用对数正态模型输出成本的最低 / 基准 / 最高区间（σ 倍数可调）。
- **年度节约汇总表**：直接给出各方案年度总成本与「较官方节省」金额 / 比例。
- **多币种**：USD / CNY 一键切换，汇率可手动微调。
- **内置模型库**：DeepSeek V4 / GPT-4o / Claude 3.5 Sonnet / GLM-5.2 / Kimi K3 等，含官方价、市场折扣、订阅套餐映射。

---

## 📊 三种计费路径说明

| 路径 | 计费方式 | 适合场景 |
| --- | --- | --- |
| 🏷️ 官方标准 | 按输入/输出 Token 单价 × 用量 | 用量小、追求稳定 SLA、需要官方支持 |
| 🛒 OpenRouter 聚合 | 聚合多家供应商市场价，通常低于官方 | 想省钱、可接受的供应商切换 |
| ♾️ CheaperInference 订阅 | 按时段月费（不限 Token、单并发） | 高用量 / 长时段场景，成本可控 |

> 订阅制适用边界：不限 Token 但受**时段**与**并发数**限制；高用量优势显著，低用量可能不划算。

---

## 🚀 快速开始（本地运行）

要求 **Python ≥ 3.10**。

```bash
# 1. 克隆仓库
git clone git@github.com:0xf4vul/ai-api-cost-simulator.git
cd ai-api-cost-simulator

# 2. 创建虚拟环境（可选但推荐）
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动
streamlit run app.py
```

启动后浏览器自动打开 `http://localhost:8501`。

---

## ☁️ 部署到 Streamlit Cloud

1. 将本仓库推到 GitHub（已完成 ✅）。
2. 打开 [Streamlit Community Cloud](https://share.streamlit.io/) → **New app** → 选择本仓库。
3. 设置：
   - **Main file path**：`app.py`
   - **Python version**：3.10+
   - **Requirements**：自动读取 `requirements.txt`
4. 点击 **Deploy**。无需任何密钥，价格数据通过公开 API 拉取。

> 也可一键部署到 Hugging Face Spaces（选择 Streamlit SDK）或任意支持 `streamlit run` 的 PaaS。

---

## ⚙️ 配置

### 页面配置 `.streamlit/config.toml`

```toml
[theme]
# 可在此自定义主题色，详见 Streamlit 文档
```

### 环境变量（可选）

`python-dotenv` 已在依赖中，可选 `.env` 文件存放密钥。当前版本无需密钥即可运行
（OpenRouter / CheaperInference 均使用公开接口，无密钥时返回参考值）。

---

## 🗂️ 项目结构

```
ai-api-cost-simulator/
├── app.py                 # 主程序（Streamlit 单文件应用）
├── requirements.txt       # Python 依赖
├── .streamlit/
│   └── config.toml        # Streamlit 页面/主题配置
├── .gitignore
├── LICENSE
└── README.md
```

---

## 📝 模型与定价数据库

模型与定价集中在 `app.py` 的 `MODEL_CATALOG` 字典中，结构如下：

```python
"DeepSeek V4 Flash": {
    "id": "deepseek-v4-flash",     # OpenRouter 匹配用的模型 id
    "official_input": 0.14,        # 官方输入价 USD / 1M tokens
    "official_output": 0.28,       # 官方输出价 USD / 1M tokens
    "ci_plan": "core",             # CheaperInference 套餐 key（None=不支持）
    "volatility_input": 0.18,      # 输入价波动率（历史 σ）
    "volatility_output": 0.15,     # 输出价波动率（历史 σ）
}
```

添加新模型只需在 `MODEL_CATALOG` 追加一项，并在 `CHEAPER_INFERENCE_PLANS` 中维护对应套餐即可。

---

## ⚠️ 使用提示

- 测算口径：OpenRouter 数据每 4 小时刷新；CheaperInference 套餐来自公开信息。
- 实际服务质量、并发限制、缓存策略可能与纯 Token 计费路径存在差异。
- 订阅制价格固定无波动；Token 计费路径受市场波动影响。
- 建议上线前用影子流量对比计费口径与输出质量一致性。

---

## 📄 许可证

本项目基于 `LICENSE` 文件中的条款发布。
