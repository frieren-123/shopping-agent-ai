import os
import time
import random
from playwright.sync_api import sync_playwright
from .base import BaseScraper

class ZhihuScraper(BaseScraper):
    def search(self, keyword, max_count=5):
        """
        在知乎搜索关键词，返回热门讨论的标题和摘要
        """
        results = []
        auth_file = "auth_zhihu.json"
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            
            context_args = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "viewport": {"width": 1280, "height": 800}
            }
            
            if os.path.exists(auth_file):
                print("🔑 [知乎] 加载历史登录凭证...")
                context_args["storage_state"] = auth_file
                
            context = browser.new_context(**context_args)
            page = context.new_page()
            
            # 注入防检测脚本
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 搜索 "关键词 推荐" 或 "关键词 测评"
            search_query = f"{keyword} 推荐 测评"
            url = f"https://www.zhihu.com/search?type=content&q={search_query}"
            
            print(f"🧠 [知乎] 正在调研: {search_query}")
            try:
                page.goto(url, timeout=60000)
                
                # 等待页面稳定
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    pass

                title = page.title()
                # print(f"   📄 页面标题: {title}")
                
                # 检查是否被重定向到登录页
                if "signin" in page.url or "login" in page.url or page.query_selector(".SignFlow"):
                    print("🔔 [知乎] 需要登录。")
                    print("⚠️ 检测到登录页面，正在切换到前台模式...")
                    page.close()
                    context.close()
                    browser.close()
                    
                    # 重启为有头模式
                    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
                    context = browser.new_context(**context_args)
                    page = context.new_page()
                    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    
                    print("👉 正在打开登录页，请在浏览器中完成登录...")
                    page.goto(url)
                    
                    # 循环检测登录状态，直到用户登录成功
                    print("⏳ 等待登录完成 (请扫码或输入密码)...")
                    try:
                        # 等待直到 URL 不包含 signin/login 且出现用户头像或特定元素
                        # 或者简单地等待用户按回车，因为知乎登录后 URL 变化可能不明显
                        page.wait_for_selector(".AppHeader-profileAvatar", timeout=300000) # 等待头像出现
                        print("✅ 检测到登录成功！")
                        context.storage_state(path=auth_file)
                        print("💾 知乎登录状态已保存。")
                    except:
                        print("⚠️ 自动检测登录超时，请确认是否已登录。")
                        input("✅ 如果已登录，请按 [回车] 继续...")
                        context.storage_state(path=auth_file)
                
                # 再次确认是否在搜索页
                if "search" not in page.url:
                     # 可能是登录后跳转到了首页，重新去搜索页
                     page.goto(url)
                     page.wait_for_load_state("networkidle")

                # 模拟滚动以触发懒加载
                for _ in range(3):
                    page.mouse.wheel(0, 1000)
                    time.sleep(1)
                
                # 获取搜索结果列表
                elements = page.query_selector_all(".ContentItem-title")
                if not elements:
                     # 备用：尝试找所有的 h2
                     elements = page.query_selector_all("h2")
                
                print(f"   🔍 找到 {len(elements)} 个潜在标题元素")

                for i, el in enumerate(elements[:max_count]):
                    try:
                        title = el.inner_text()
                        # 简单的过滤，确保标题长度足够
                        if len(title) < 4: continue
                        
                        # 广告过滤
                        if "广告" in title or "赞助" in title:
                            print(f"   🗑️ 过滤广告: {title}")
                            continue

                        # 尝试获取链接
                        link_el = el.query_selector("a")
                        link = ""
                        if link_el:
                            href = link_el.get_attribute("href")
                            if href:
                                if href.startswith("//"):
                                    link = "https:" + href
                                elif href.startswith("/"):
                                    link = "https://www.zhihu.com" + href
                                else:
                                    link = href
                        
                        # 尝试获取摘要 (Snippet) 以便 LLM 判断是否为软广
                        snippet = ""
                        try:
                            # 尝试找兄弟节点或父级的兄弟
                            # 这是一个简化的假设
                            parent = el.query_selector("xpath=..")
                            if parent:
                                snippet = parent.inner_text()[:200] # 取前200字
                        except:
                            pass

                        if title:
                            results.append({
                                "title": title,
                                "link": link,
                                "source": "Zhihu",
                                "snippet": snippet
                            })
                            print(f"   📖 发现文章: {title}")
                    except:
                        continue
                
            except Exception as e:
                print(f"   ⚠️ 知乎调研失败: {e}")
            
            browser.close()
            
        if not results:
            print("   ⚠️ 知乎调研未发现有效内容，将跳过趋势分析。")
            
        return results

    def get_details(self, item_id):
        pass
