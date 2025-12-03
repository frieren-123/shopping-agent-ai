import sys
import webbrowser
import os
from src.agent import ShoppingAgent
from src.config_loader import CONFIG

def main():
    print("="*50)
    print(f"🛒 {CONFIG.get('app', {}).get('name', 'AI Shopping Agent')} - 全流程启动")
    print("="*50)
    
    agent = ShoppingAgent()

    # 1. 获取用户需求
    keyword = input("🔍 请输入你想购买的商品 (例如 '跑步鞋', '机械键盘'): ").strip()
    
    if not keyword:
        print("❌ 必须输入商品名称")
        return

    # 获取高级参数
    default_max_pages = CONFIG["crawler"]["max_pages"]
    default_top_n = CONFIG["filter"]["top_n"]
    
    max_pages_input = input(f"📄 请输入要抓取的页数 (默认 {default_max_pages}，输入 'all' 可抓取更多): ").strip()
    
    if max_pages_input.lower() == "all":
        max_pages = 20
        print(f"⚠️ 已启用【深度抓取模式】，将尝试抓取前 {max_pages} 页。")
    else:
        max_pages = int(max_pages_input) if max_pages_input.isdigit() else default_max_pages

    top_n_input = input(f"🎯 请输入要筛选的候选商品数量 (默认 {default_top_n}): ").strip()
    top_n = int(top_n_input) if top_n_input.isdigit() else default_top_n

    # 1.5 智能追问
    print("\n🤔 正在思考需要了解哪些细节...")
    questions = agent.ask_clarifying_questions(keyword)
    
    detailed_requirements = keyword
    if questions:
        print(f"👉 为了更精准地为您推荐，请回答以下几个问题（直接回车可跳过）：")
        for q in questions:
            ans = input(f"   ❓ {q}: ").strip()
            if ans:
                detailed_requirements += f" {ans}"
    
    print(f"\n📝 您的最终需求：{detailed_requirements}")

    # 2. 清理环境
    agent.clean_data()

    # 3. 第一阶段：海量抓取
    print("\n" + "-"*30)
    print("🚀 第一阶段：多平台海量搜索")
    print("-"*30)
    
    print("请选择抓取平台：")
    print("1. 仅京东 (JD) - ✅ 推荐，安全免登录")
    print("2. 仅淘宝 (Taobao) - ⚠️ 需要登录，有风控风险")
    print("3. 仅唯品会 (Vipshop) - 🛍️ 品牌特卖")
    print("4. 全平台聚合 (JD + Taobao + Vipshop)")
    print("5. [实验性] 京东 AI 增强版 (Crawl4AI + LLM) - 🤖 更智能")
    platform_choice = input("请输入选项 (默认 1): ").strip()
    
    products = agent.search(keyword, max_pages, platform_choice)
    
    print(f"\n🎉 海量抓取结束！共收集 {len(products)} 个商品信息。")
    
    if not products:
        print("❌ 抓取失败，未生成搜索结果。")
        return

    # 4. 第二阶段：智能初筛
    print("\n" + "-"*30)
    print("🧠 第二阶段：AI 智能初筛")
    print("-"*30)
    top_candidates = agent.filter_products(detailed_requirements, top_n=top_n)
    
    if not top_candidates:
        print("❌ 初筛未选中任何商品，流程终止。")
        return

    # 5. 第三阶段：深度采集
    print("\n" + "-"*30)
    print("🕵️ 第三阶段：深度详情采集")
    print("-"*30)
    agent.get_details()

    # 6. 第四阶段：最终决策
    print("\n" + "-"*30)
    print("📊 第四阶段：生成购买决策报告")
    print("-"*30)
    agent.analyze_products()

    # 7. 清理临时文件
    agent.cleanup()

    print("\n" + "="*50)
    print("🎉 全流程执行完毕！")
    print("👉 最终报告已生成: data/final_report.html")
    
    # 交互式打开报告
    open_choice = input("🌐 是否立即在浏览器中打开报告? (y/n): ").strip().lower()
    if open_choice == 'y':
        report_path = os.path.abspath("data/final_report.html")
        print(f"🚀 正在打开: {report_path}")
        webbrowser.open(f"file://{report_path}")
    
    # 8. 第五阶段：反馈闭环
    print("\n" + "-"*30)
    print("⚡ 第五阶段：Agent 进化 (Feedback Loop)")
    print("-"*30)
    feedback = input("💬 您对本次推荐满意吗？(直接回车结束，或输入反馈意见以训练 AI): ").strip()
    if feedback:
        try:
            from src.analysis.feedback_loop import FeedbackOptimizer
            optimizer = FeedbackOptimizer()
            optimizer.optimize(feedback)
        except Exception as e:
            print(f"⚠️ 反馈处理失败: {e}")

    print("="*50)

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()
