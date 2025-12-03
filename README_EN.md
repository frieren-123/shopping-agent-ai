# 🛒 AI Shopping Agent

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B)
![Playwright](https://img.shields.io/badge/Playwright-Web%20Scraping-green)
![OpenAI](https://img.shields.io/badge/AI-Powered-orange)

> **Cross-platform price comparison, AI-driven decision making.**  
> An intelligent shopping assistant powered by Large Language Models (LLMs) that searches across major e-commerce platforms (JD, Taobao, Vipshop), extracts product details using AI, and generates objective buying advice reports.

[🇨🇳 中文文档](README.md) | [🇺🇸 English Docs](README_EN.md)

---

## ✨ Key Features

- **🤖 Multi-Platform Aggregation**: Supports major Chinese e-commerce platforms like JD.com (Crawl4AI/OCR), Taobao (Playwright), and Vipshop.
- **🧠 AI Intelligence**:
  - **Parameter Extraction**: Automatically extracts specs from complex product pages, filtering out marketing fluff.
  - **Smart Scorer**: Calculates a cost-performance ratio based on price, sales volume, and shop reputation.
- **📊 Decision Reports**: Generates HTML reports with pros/cons analysis and recommendations for specific user groups.
- **🖥️ Modern UI**: Built with Streamlit for a clean, interactive user experience.
- **🛡️ Anti-Scraping**: Built-in strategies including isolated browser contexts, random delays, and redirect detection.

## 📸 Preview

*(Please upload a screenshot here)*

## 🛠️ Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/frieren-123/shopping-agent-ai.git
cd shopping-agent-ai
```

### 2. Install dependencies
Using Conda or a virtual environment is recommended:
```bash
pip install -r requirements.txt
playwright install  # Install browser drivers
```

### 3. Configuration
Create a `.env` file in the root directory and add your LLM API Key:
```ini
LLM_API_KEY=sk-xxxxxx
LLM_BASE_URL=https://api.deepseek.com  # Or other OpenAI-compatible endpoints
LLM_MODEL=gpt-3.5-turbo
```

### 4. Run
```bash
streamlit run app.py
```

## 📂 Project Structure

```
shopping-agent-ai/
├── app.py                 # Streamlit Entry Point
├── src/
│   ├── agent.py           # Core Agent Logic
│   ├── scrapers/          # Platform Scrapers (JD, Taobao, etc.)
│   ├── analysis/          # Scoring & Analysis Logic
│   ├── llm_analyzer.py    # LLM Interaction & Report Gen
│   └── models/            # Pydantic Data Models
├── data/                  # Data Storage (Auto-generated)
└── requirements.txt       # Dependencies
```

## 🤝 Contributing

Issues and Pull Requests are welcome!
If you find a scraper is broken (which is common as e-commerce sites update frequently), feel free to submit a fix.

## 📜 License

MIT License
