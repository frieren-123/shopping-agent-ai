import asyncio
import re
import sys
import os

# 添加 src 目录到路径，以便导入
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
try:
    from src.llm_analyzer import extract_info_from_markdown
except ImportError:
    # Fallback if import fails
    def extract_info_from_markdown(text):
        print("   ⚠️ 无法导入 LLM 提取器，使用空列表")
        return []

class JDCrawl4AIScraper:
    def __init__(self):
        pass

    def search_sync(self, keyword, max_pages=1):
        """同步包装器，方便 main.py 调用"""
        return asyncio.run(self.search(keyword, max_pages))

    async def search(self, keyword, max_pages=1):
        results = []
        print(f"🚀 [Crawl4AI] 启动智能搜索: {keyword}")
        
        # 1. 配置浏览器 (使用独立的用户数据目录，不影响日常使用)
        # 我们会创建一个新的目录，专门给爬虫用，但使用 Edge 内核
        
        # 创建一个独立的爬虫专用目录
        crawler_data_dir = os.path.join(os.getcwd(), "browser_data_edge_crawler")
        if not os.path.exists(crawler_data_dir):
            os.makedirs(crawler_data_dir, exist_ok=True)

        print(f"   🌐 使用独立环境 (不影响日常浏览器)...")
        print(f"   📂 数据目录: {crawler_data_dir}")

        browser_config = BrowserConfig(
            headless=False, 
            verbose=True,
            browser_type="chromium",
            user_data_dir=crawler_data_dir,
            # ✅ 增加反爬虫策略 (Stealth)
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            # 尝试传递给 Playwright 的启动参数
            # args=["--disable-blink-features=AutomationControlled", "--no-sandbox"] 
        )
        
        # 2. 定义滚动脚本 (京东是懒加载，必须滚动到底部)
        js_code = """
            const scrollStep = 500;
            const delay = 500;
            let lastHeight = document.body.scrollHeight;
            
            while (true) {
                window.scrollBy(0, scrollStep);
                await new Promise(resolve => setTimeout(resolve, delay));
                
                let newHeight = document.body.scrollHeight;
                if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight) {
                    break;
                }
            }
        """

        run_config = CrawlerRunConfig(
            js_code=js_code,
            cache_mode=CacheMode.BYPASS,
            page_timeout=60000,
            # ✅ 增加随机延迟，模拟人类行为
            delay_before_return_html=2.0,
            # ✅ 关键：等待商品列表元素加载，确保不是空页面或首页
            wait_for="css:#J_goodsList", 
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            for page in range(1, max_pages + 1):
                try:
                    # 京东分页逻辑
                    jd_page_param = 2 * page - 1
                    url = f"https://search.jd.com/Search?keyword={keyword}&page={jd_page_param}"
                    
                    print(f"   🔄 [第 {page} 页] AI 正在阅读页面...")
                    print("   ⏳ 如果弹出登录窗口，请在 60秒内 完成扫码登录...")
                    
                    # 智能重试循环：处理登录
                    max_retries = 12 # 12 * 5s = 60秒等待时间
                    is_login = False
                    result = None
                    
                    for attempt in range(max_retries):
                        try:
                            result = await crawler.arun(url=url, config=run_config)
                            
                            # 检查是否被重定向到了首页
                            if result.url and "www.jd.com" in result.url and "search" not in result.url:
                                print("   🚨 检测到被重定向回首页，可能是反爬虫拦截！")
                                print("   👉 请尝试手动在浏览器中搜索一次，或检查登录状态。")
                                is_login = True # 视为登录/验证失败
                            # 检查是否是登录页 (内容过短 或 包含特定关键词)
                            elif result.markdown:
                                is_login = len(result.markdown) < 800 or "请登录" in result.markdown or "扫码登录" in result.markdown
                            else:
                                is_login = True
                            
                            if is_login:
                                print(f"   🚨 [第 {attempt+1}/{max_retries} 次检测] 似乎还在登录页或首页，请扫码/验证...")
                                print("      (登录成功后，程序会自动跳转，无需手动操作)")
                                await asyncio.sleep(5) # 等待用户操作
                            else:
                                # 成功获取到内容
                                break
                        except Exception as e:
                            print(f"   ⚠️ 尝试读取失败: {e}")
                            await asyncio.sleep(5)
                    
                    if result and result.success and not is_login:
                        print(f"   ✅ 页面读取成功 (长度: {len(result.markdown)} 字符)")
                        
                        # 如果页面太短，可能是被验证码拦截了
                        if len(result.markdown) < 5000:
                            print("   ⚠️ 警告：页面内容过短，可能触发了验证码或未加载成功。")
                            print(f"   👀 页面预览: {result.markdown[:200]}...")
                        
                        # --- 智能解析 (使用 LLM 提取数据) ---
                        print("   🧠 正在调用 DeepSeek/GPT 提取商品信息...")
                        # 使用 to_thread 避免阻塞异步循环
                        items = await asyncio.to_thread(extract_info_from_markdown, result.markdown)
                        
                        print(f"   📄 本页提取到 {len(items)} 个商品")
                        
                        if len(items) == 0:
                            print("   ⚠️ 警告：未提取到商品，正在保存调试文件...")
                            with open("debug_jd_markdown.md", "w", encoding="utf-8") as f:
                                f.write(result.markdown)
                            print("   💾 页面 Markdown 已保存至 debug_jd_markdown.md")

                        results.extend(items)
                        
                    else:
                        err_msg = result.error_message if result else "Unknown Error"
                        print(f"   ❌ 抓取失败: {err_msg}")
                
                except Exception as e:
                    print(f"   ❌ 页面 {page} 处理发生严重错误: {e}")
                    continue # 继续下一页
                    
        print("   🛑 正在关闭爬虫浏览器...")
        # async with 块结束时会自动关闭浏览器，这里只是打印状态
        
        return results
