import os
import shutil
import json
import asyncio
from src.scrapers.taobao import TaobaoScraper
from src.scrapers.jd_gui import JDScraper # ✅ 视觉 OCR 爬虫
from src.scrapers.jd_crawl4ai import JDCrawl4AIScraper # ✅ AI 增强版爬虫
from src.scrapers.vip import VipScraper
from src.scrapers.zhihu import ZhihuScraper
from src.analysis.scorer import SmartScorer
from src.llm_analyzer import filter_products, analyze_products, ask_clarifying_questions
from src.config_loader import CONFIG
from src.report_engine import ReportEngine # ✅ 新增报告引擎

class ShoppingAgent:
    def __init__(self):
        self.config = CONFIG
        self.products = []
        self.top_candidates = []
        self.reporter = ReportEngine() # ✅ 初始化报告引擎

    def clean_data(self):
        """清理旧数据，为新任务做准备"""
        print("🧹 正在清理旧数据...")
        if os.path.exists("data"):
            for filename in os.listdir("data"):
                file_path = os.path.join("data", filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"⚠️ 删除 {file_path} 失败: {e}")
        else:
            os.makedirs("data")
        
        os.makedirs("data/details", exist_ok=True)
        print("✅ 数据清理完成")

    def ask_clarifying_questions(self, keyword):
        return ask_clarifying_questions(keyword)

    def search(self, keyword, max_pages=None, platform_choice="1"):
        """同步入口 (兼容旧代码)"""
        import sys
        # 修复 Windows 下 Playwright 的 NotImplementedError
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
        return asyncio.run(self.search_async(keyword, max_pages, platform_choice))

    async def search_async(self, keyword, max_pages=None, platform_choice="1"):
        """异步搜索核心逻辑"""
        if max_pages is None:
            max_pages = self.config["crawler"]["max_pages"]
        
        self.products = []
        refined_keyword = keyword 

        tasks = []

        # 淘宝 (目前仍为同步，放入线程池或直接调用)
        if platform_choice == "2" or platform_choice == "4":
            print("\n📦 正在启动淘宝抓取...")
            # 简单的同步调用包装
            try:
                taobao_scraper = TaobaoScraper()
                # 注意：这里如果是耗时操作，建议用 run_in_executor，但为了简单先直接调用
                tb_products = taobao_scraper.search(keyword=refined_keyword, max_pages=max_pages)
                self.products.extend(tb_products)
            except Exception as e:
                print(f"⚠️ 淘宝抓取失败: {e}")

        # 唯品会
        if platform_choice == "3" or platform_choice == "4":
            print("\n🛍️ 正在启动唯品会抓取...")
            try:
                vip_scraper = VipScraper()
                vip_products = vip_scraper.search(keyword=refined_keyword, max_pages=max_pages)
                self.products.extend(vip_products)
            except Exception as e:
                print(f"⚠️ 唯品会抓取失败: {e}")

        # 京东 (默认或全选) - 切换为 Crawl4AI 异步版
        if platform_choice == "1" or platform_choice == "4" or platform_choice == "5" or (platform_choice not in ["2", "3", "4", "5", "6"]):
            print("\n🤖 正在启动京东 AI 增强版抓取 (Crawl4AI)...")
            try:
                ai_scraper = JDCrawl4AIScraper()
                # 直接 await 异步方法
                jd_products = await ai_scraper.search(keyword=refined_keyword, max_pages=max_pages)
                self.products.extend(jd_products)
            except Exception as e:
                print(f"⚠️ 京东 AI 抓取失败: {e}")

        # 京东 OCR 版
        if platform_choice == "6":
            print("\n📸 正在启动京东视觉 OCR 抓取 (PaddleOCR)...")
            try:
                # OCR 爬虫目前是同步的，直接调用
                ocr_scraper = JDScraper()
                jd_products = ocr_scraper.search(keyword=refined_keyword, max_pages=max_pages)
                self.products.extend(jd_products)
            except Exception as e:
                print(f"⚠️ OCR 抓取失败: {e}")
        
        # 智能打分与排序
        if self.products:
            print("\n🧮 正在应用智能打分算法 (Bayesian + Z-Score)...")
            scorer = SmartScorer(self.products)
            self.products = scorer.rank_products()
            
            # ✅ 使用新的报告引擎打印 CLI 摘要
            self.reporter.print_cli_summary(self.products[:10])
            
            # 保存结果
            output_file = "data/search_results.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(self.products, f, ensure_ascii=False, indent=2)
        
        return self.products

    def filter_products(self, detailed_requirements, top_n=None):
        if top_n is None:
            top_n = self.config["filter"]["top_n"]
            
        self.top_candidates = filter_products(detailed_requirements, top_n=top_n)
        return self.top_candidates

    def get_details(self):
        # 分离不同平台的商品
        tb_candidates = [p for p in self.top_candidates if p.get('platform') not in ['JD', 'Vipshop']]
        other_candidates = [p for p in self.top_candidates if p.get('platform') in ['JD', 'Vipshop']]
        
        if tb_candidates:
            print(f"📦 正在采集 {len(tb_candidates)} 个淘宝商品详情...")
            try:
                taobao_scraper = TaobaoScraper()
                taobao_scraper.get_details(tb_candidates)
            except Exception as e:
                print(f"⚠️ 淘宝详情采集失败: {e}")
            
        if other_candidates:
            print(f"✨ 其他平台商品 ({len(other_candidates)} 个) 已在搜索阶段获取了足够信息，跳过深度采集。")
            os.makedirs("data/details", exist_ok=True)
            for item in other_candidates:
                platform_name = "京东" if item.get('platform') == 'JD' else "唯品会"
                detail_data = {
                    "id": item['id'],
                    "title": item['title'],
                    "price": item['price'],
                    "shop": item['shop'],
                    "captured_reviews": [{"content": f"{platform_name}热度/销量: " + str(item.get('deal_count', '未知'))}], 
                    "captured_props": [{"name": "来源", "value": f"{platform_name}自营/品牌店"}]
                }
                with open(f"data/details/{item['id']}.json", "w", encoding="utf-8") as f:
                    json.dump(detail_data, f, ensure_ascii=False, indent=2)

    def analyze_products(self):
        return analyze_products()

    def cleanup(self):
        """清理临时文件"""
        try:
            if os.path.exists("data/details"):
                shutil.rmtree("data/details")
            if os.path.exists("data/search_results.json"):
                os.remove("data/search_results.json")
            if os.path.exists("data/top_candidates.json"):
                os.remove("data/top_candidates.json")
            print("✅ 临时文件已清理。")
        except Exception as e:
            print(f"⚠️ 清理失败: {e}")
