import time
import random
from playwright.sync_api import sync_playwright
from .base import BaseScraper

class BilibiliScraper(BaseScraper):
    def search(self, keyword, max_count=10):
        """
        B站搜索 (用于硬核测评调研)
        """
        results = []
        print(f"📺 [Bilibili] 正在调研: {keyword}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, # B站对无头模式相对宽容
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            
            page = context.new_page()
            
            try:
                # B站搜索页
                url = f"https://search.bilibili.com/all?keyword={keyword}&search_source=nav_search_new"
                page.goto(url, timeout=30000)
                
                # 等待列表加载
                try:
                    page.wait_for_selector(".video-list-item", timeout=10000)
                except:
                    pass
                
                items = page.query_selector_all(".video-list-item")
                if not items:
                     # 备用选择器 (B站改版频繁)
                     items = page.query_selector_all(".bili-video-card")

                print(f"   🔍 找到 {len(items)} 个相关视频")
                
                for item in items[:max_count]:
                    try:
                        # 提取标题
                        title_el = item.query_selector("h3") or item.query_selector(".bili-video-card__info--tit")
                        title = title_el.inner_text().strip() if title_el else ""
                        
                        # 提取播放量 (热度)
                        play_el = item.query_selector(".bili-video-card__stats--item") or item.query_selector(".so-icon-watch-num")
                        play_count = play_el.inner_text().strip() if play_el else "0"
                        
                        # 链接
                        link_el = item.query_selector("a")
                        link = link_el.get_attribute("href") if link_el else ""
                        if link and not link.startswith("http"):
                            link = "https:" + link
                            
                        if title:
                            results.append({
                                "title": title,
                                "link": link,
                                "source": "Bilibili",
                                "snippet": f"B站测评 (播放量: {play_count})"
                            })
                    except:
                        continue
                        
            except Exception as e:
                print(f"   ⚠️ B站调研失败: {e}")
                
            browser.close()
            
        return results

    def get_details(self, item_id):
        pass
