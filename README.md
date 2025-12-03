# AI Shopping Agent (AI 购物助手)

# 🛒 AI Shopping Agent (AI 智能购物助手)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B)
![Playwright](https://img.shields.io/badge/Playwright-Web%20Scraping-green)
![OpenAI](https://img.shields.io/badge/AI-Powered-orange)

> **全网比价，AI 决策。**  
> 一个基于大语言模型 (LLM) 的智能购物助手，能够跨平台（京东、淘宝、唯品会）搜索商品，利用 AI 帮你阅读复杂的参数和评论，生成客观的购买建议报告。

---

## ✨ 核心功能

- **🤖 多平台聚合搜索**：支持京东 (Crawl4AI/OCR)、淘宝 (Playwright)、唯品会等主流电商平台。
- **🧠 AI 智能分析**：
  - 自动提取商品参数，不再被详情页的营销话术迷惑。
  - 智能打分系统 (Smart Scorer)：基于价格、销量、店铺信誉计算性价比。
- **📊 决策报告生成**：生成包含优缺点分析、适用人群建议的 HTML 购买报告。
- **🖥️ 现代化 UI**：基于 Streamlit 的交互式界面，操作简单直观。
- **🛡️ 反爬虫对抗**：内置多种反爬策略（独立浏览器环境、随机延迟、重定向检测）。

## 📸 界面预览

*<img width="1848" height="892" alt="image" src="https://github.com/user-attachments/assets/a7a3806b-7f63-4253-b282-4a3d64f3cee5" />
*

## 🛠️ 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/frieren-123/shopping-agent-ai.git
cd shopping-agent-ai
```

### 2. 安装依赖
建议使用 Conda 或虚拟环境：
```bash
pip install -r requirements.txt
playwright install  # 安装浏览器驱动
```

### 3. 配置环境
在项目根目录创建 `.env` 文件，填入你的 LLM API Key：
```ini
LLM_API_KEY=sk-xxxxxx
LLM_BASE_URL=https://api.deepseek.com  # 或其他 OpenAI 兼容接口
LLM_MODEL=gpt-3.5-turbo
```

### 4. 运行
```bash
streamlit run app.py
```

## 📂 项目结构

```
shopping-agent-ai/
├── app.py                 # Streamlit 入口文件
├── src/
│   ├── agent.py           # 核心调度 Agent
│   ├── scrapers/          # 各平台爬虫实现 (JD, Taobao, etc.)
│   ├── analysis/          # 打分与分析逻辑
│   ├── llm_analyzer.py    # LLM 调用与报告生成
│   └── models/            # Pydantic 数据模型
├── data/                  # 抓取数据存储 (自动生成)
└── requirements.txt       # 依赖列表
```

## 🤝 贡献指南

欢迎提交 Issue 或 Pull Request！
如果你发现某个平台的爬虫失效了（这很正常，电商反爬更新很快），欢迎提交修复代码。

## 📜 许可证

MIT License
集成了多平台爬虫（京东、淘宝、唯品会）和 LLM（大语言模型）分析能力，旨在帮助用户做出更明智的购买决策。

## ✨ 功能特性

- **多平台支持**: 
  - 京东 (支持 AI 增强版 Crawl4AI 和 视觉 OCR 版)
  - 淘宝 (基础搜索)
  - 唯品会
- **智能分析**:
  - 利用 LLM (OpenAI/DeepSeek) 对商品进行深度点评。
  - 自动生成购买决策报告 (HTML/Markdown)。
- **现代化界面**:
  - 提供 Streamlit Web 图形界面，操作简单直观。
- **抗反爬虫**:
  - 内置多种反爬虫策略 (OCR, 模拟浏览器行为)。

## 🛠️ 安装指南

1. **克隆项目**
   ```bash
   git clone <repository_url>
   cd shopping-agent
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   复制 `.env.example` (如果有) 或直接创建 `.env` 文件，填入您的 LLM API Key：
   ```ini
   LLM_API_KEY=sk-xxxxxx
   LLM_BASE_URL=https://api.deepseek.com/v1
   LLM_MODEL=deepseek-chat
   ```

## 🚀 快速开始

### 方式 A: Web 图形界面 (推荐)
```bash
streamlit run app.py
```

### 方式 B: 命令行模式
```bash
python main.py
```

## 📂 项目结构

- `app.py`: Streamlit Web 入口
- `main.py`: CLI 入口
- `src/`: 核心代码
  - `agent.py`: 智能代理核心逻辑
  - `scrapers/`: 各平台爬虫实现
  - `analysis/`: 数据分析与打分
  - `llm_analyzer.py`: LLM 调用与 Prompt 管理
  - `utils/`: 工具类 (如 OCR)

## 📝 许可证

MIT License
