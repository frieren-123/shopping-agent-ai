import time
import random
from playwright.sync_api import sync_playwright
from .base import BaseScraper

class DouyinScraper(BaseScraper):
    def search(self, keyword, max_count=10):
        """
        抖音搜索 (用于短视频趋势调研)
        """
        results = []
        print(f"🎵 [抖音] 正在调研: {keyword}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False, # 抖音必须有头，否则无法加载视频流
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars",
                    "--window-size=1280,800"
                ]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            
            # 注入防检测
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page = context.new_page()
            
            try:
                # 抖音搜索页
                url = f"https://www.douyin.com/search/{keyword}"
                page.goto(url, timeout=60000)
                
                # 处理登录弹窗 (抖音经常弹出)
                try:
                    # 等待一会，如果出现登录框，尝试关闭或忽略
                    time.sleep(3)
                    close_btn = page.query_selector(".dy-account-close")
                    if close_btn:
                        close_btn.click()
                        print("   ❎ 关闭了抖音登录弹窗")
                except:
                    pass
                
                # 等待视频列表
                try:
                    page.wait_for_selector(".search-result-card", timeout=15000)
                except:
                    print("   ⚠️ 抖音加载超时或需要验证码")
                
                # 滚动加载
                page.mouse.wheel(0, 1000)
                time.sleep(2)
                
                items = page.query_selector_all(".search-result-card")
                print(f"   🔍 找到 {len(items)} 个短视频")
                
                for item in items[:max_count]:
                    try:
                        # 提取标题/描述
                        # 抖音的结构很复杂，通常在 alt 属性或 textContent 中
                        img = item.query_selector("img")
                        title = ""
                        if img:
                            title = img.get_attribute("alt")
                        
                        if not title:
                            title = item.inner_text().split('\n')[0]
                            
                        # 链接
                        link_el = item.query_selector("a")
                        link = link_el.get_attribute("href") if link_el else ""
                        if link and not link.startswith("http"):
                            link = "https:" + link
                            
                        # 点赞数
                        like_el = item.query_selector(".like-count") # 假设类名
                        likes = like_el.inner_text() if like_el else "未知"

                        if title:
                            results.append({
                                "title": title,
                                "link": link,
                                "source": "Douyin",
                                "snippet": f"抖音热门 (标题: {title})"
                            })
                    except:
                        continue
                        
            except Exception as e:
                print(f"   ⚠️ 抖音调研失败: {e}")
                
            browser.close()
            
        return results

    def get_details(self, item_id):
        pass
