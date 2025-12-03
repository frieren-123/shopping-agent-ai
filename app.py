import streamlit as st
import os
import json
import pandas as pd
from src.agent import ShoppingAgent

st.set_page_config(page_title="AI 购物助手", page_icon="🛒", layout="wide")

st.title("🛒 AI 智能购物助手")
st.markdown("---")

# 初始化 Agent
if 'agent' not in st.session_state:
    st.session_state.agent = ShoppingAgent()

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 设置")
    platform_choice = st.selectbox(
        "选择抓取平台",
        options=["1", "2", "3", "4", "5", "6"],
        format_func=lambda x: {
            "1": "仅京东 (JD) - 推荐",
            "2": "仅淘宝 (Taobao)",
            "3": "仅唯品会 (Vipshop)",
            "4": "全平台聚合",
            "5": "京东 AI 增强版 (Crawl4AI)",
            "6": "京东视觉 OCR 版 (PaddleOCR)"
        }[x]
    )
    max_pages = st.number_input("抓取页数", min_value=1, max_value=20, value=1)
    top_n = st.number_input("筛选数量", min_value=1, max_value=10, value=3)
    
    if st.button("🧹 清理旧数据"):
        st.session_state.agent.clean_data()
        st.success("数据已清理")

# 主界面
keyword = st.text_input("🔍 请输入你想购买的商品", placeholder="例如: 跑步鞋, 机械键盘")

if keyword:
    # 智能追问
    if 'questions' not in st.session_state or st.session_state.last_keyword != keyword:
        with st.spinner("🤔 正在思考需要了解哪些细节..."):
            st.session_state.questions = st.session_state.agent.ask_clarifying_questions(keyword)
            st.session_state.last_keyword = keyword
    
    answers = {}
    if st.session_state.questions:
        st.info("👉 为了更精准地为您推荐，请回答以下几个问题（可选）：")
        for q in st.session_state.questions:
            answers[q] = st.text_input(f"❓ {q}")

    if st.button("🚀 开始搜索"):
        detailed_requirements = keyword
        for q, a in answers.items():
            if a:
                detailed_requirements += f" {a}"
        
        st.write(f"📝 您的最终需求：{detailed_requirements}")
        
        # 1. 搜索
        with st.status("🔍 正在全网搜索...", expanded=True) as status:
            st.write("正在清理环境...")
            st.session_state.agent.clean_data()
            
            st.write(f"正在 {platform_choice} 平台上搜索 '{keyword}'...")
            products = st.session_state.agent.search(keyword, max_pages, platform_choice)
            
            if not products:
                status.update(label="❌ 搜索未找到结果", state="error")
                st.error("未找到相关商品，请尝试更换关键词或平台。")
            else:
                status.update(label=f"✅ 搜索完成，共找到 {len(products)} 个商品", state="complete")
                
                # 显示搜索结果概览
                df = pd.DataFrame(products)
                if not df.empty:
                    st.dataframe(df[['title', 'price', 'shop', 'platform', 'smart_score']], use_container_width=True)

                # 2. 筛选
                with st.spinner("🧠 正在进行 AI 智能初筛..."):
                    top_candidates = st.session_state.agent.filter_products(detailed_requirements, top_n)
                
                if not top_candidates:
                    st.error("❌ 初筛未选中任何商品。")
                else:
                    st.success(f"✅ AI 已筛选出 {len(top_candidates)} 个最佳候选商品")
                    
                    # 3. 详情采集
                    with st.spinner("🕵️ 正在采集商品详情..."):
                        st.session_state.agent.get_details()
                    
                    # 4. 分析报告
                    with st.spinner("📊 正在生成最终购买建议..."):
                        report_path = st.session_state.agent.analyze_products()
                    
                    st.balloons()
                    st.success("🎉 购买决策报告已生成！")
                    
                    # 读取并显示 HTML 报告
                    if os.path.exists("data/final_report.html"):
                        with open("data/final_report.html", "r", encoding="utf-8") as f:
                            html_content = f.read()
                        st.components.v1.html(html_content, height=800, scrolling=True)
                        
                        with open("data/final_report.html", "rb") as f:
                            st.download_button(
                                label="📥 下载完整报告",
                                data=f,
                                file_name="shopping_report.html",
                                mime="text/html"
                            )

