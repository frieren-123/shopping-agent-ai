# AI Shopping Agent (AI 购物助手)

这是一个基于 Python 的智能购物助手，集成了多平台爬虫（京东、淘宝、唯品会）和 LLM（大语言模型）分析能力，旨在帮助用户做出更明智的购买决策。

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
