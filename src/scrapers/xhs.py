import time
import random
import json
import re
import os
from playwright.sync_api import sync_playwright
from .base import BaseScraper

class XiaohongshuScraper(BaseScraper):
    def search(self, keyword, max_count=10):
        """
        小红书搜索 (用于趋势调研)
        """
        results = []
        print(f"📕 [小红书] 正在调研: {keyword}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False, # 小红书对无头模式检测较严
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars",
                    "--window-size=1280,800"
                ]
            )
            
            auth_file = "auth_xhs.json"
            context_args = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "viewport": {"width": 1280, "height": 800},
                "device_scale_factor": 1,
            }
            
            if os.path.exists(auth_file):
                print("🔑 [小红书] 加载历史登录凭证...")
                context_args["storage_state"] = auth_file

            context = browser.new_context(**context_args)
            
            # 注入防检测
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page = context.new_page()
            
            try:
                # 小红书搜索页
                url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes"
                page.goto(url, timeout=60000)
                
                # 检测登录弹窗或强制登录
                try:
                    # 等待一会看是否有登录框
                    time.sleep(3)
                    # 小红书 web 端搜索通常需要登录才能查看完整内容
                    # 检查是否有登录容器
                    if page.query_selector(".login-container") or "login" in page.url:
                        print("🔔 [小红书] 需要登录才能查看更多内容。")
                        
                        # 安全询问
                        print("   ⚠️  安全提示：频繁自动登录可能导致账号风险。")
                        print("   👉 您可以选择 [y] 扫码登录 (将保存凭证)，或 [n] 跳过此平台。")
                        print("\a") # 提示音
                        
                        user_choice = input("   ❓ 是否继续登录？(y/n): ").strip().lower()
                        if user_choice != 'y':
                            print("   ⏭️  用户选择跳过小红书。")
                            browser.close()
                            return []

                        print("👉 请在弹出的浏览器中扫码登录...")
                        
                        # 等待登录成功 (检测头像或特定元素)
                        print("⏳ 正在等待登录成功状态...")
                        try:
                            # 循环检测登录状态，避免单一选择器失效
                            for _ in range(60): # 最多等待 3 分钟
                                if page.query_selector(".user-avatar") or page.query_selector(".avatar") or page.query_selector("#global-header .user") or not page.query_selector(".login-container"):
                                    print("✅ [小红书] 检测到登录成功！")
                                    context.storage_state(path=auth_file)
                                    break
                                time.sleep(3)
                            else:
                                print("⚠️ 自动检测登录超时，将尝试继续抓取...")
                        except:
                            print("⚠️ 登录检测异常，尝试继续...")
                except:
                    pass

                # 等待加载
                try:
                    page.wait_for_selector("section.note-item", timeout=10000)
                except:
                    # 尝试更通用的选择器
                    pass
                
                # 滚动加载
                for _ in range(3):
                    page.mouse.wheel(0, 1000)
                    time.sleep(random.uniform(1, 2))
                
                # 提取笔记
                # 小红书 Web 端通常使用 section.note-item
                notes = page.query_selector_all("section.note-item")
                
                # 如果没找到，尝试找所有带 href 的 a 标签，且 href 包含 /explore/
                if not notes:
                    print("   ⚠️ 未找到标准笔记元素，尝试通用提取...")
                    notes = page.query_selector_all("a[href*='/explore/']")

                print(f"   🔍 找到 {len(notes)} 篇笔记")
                
                for note in notes[:max_count]:
                    try:
                        # 尝试提取标题 (通常在 footer 或 span 中)
                        title = note.inner_text().split('\n')[0]
                        if len(title) > 50: title = title[:50] + "..."
                        
                        # 提取链接
                        link = ""
                        href = note.get_attribute("href")
                        if href:
                            link = href
                        else:
                            # 如果是 section，找里面的 a
                            a_tag = note.query_selector("a")
                            if a_tag:
                                link = a_tag.get_attribute("href")
                        
                        if link and not link.startswith("http"):
                            link = "https://www.xiaohongshu.com" + link
                            
                        # 提取点赞 (尝试找数字)
                        likes = "0"
                        text = note.inner_text()
                        match = re.search(r'(\d+)', text.split('\n')[-1]) # 通常在最后一行
                        if match:
                            likes = match.group(1)

                        if title:
                            results.append({
                                "title": title,
                                "link": link,
                                "source": "Xiaohongshu",
                                "likes": likes,
                                "snippet": f"小红书笔记 (热度: {likes})"
                            })
                    except:
                        continue
                        
            except Exception as e:
                print(f"   ⚠️ 小红书调研失败: {e}")
                
            browser.close()
            
        return results

    def get_details(self, item_id):
        pass
