import time
import random
from playwright.sync_api import sync_playwright
from .base import BaseScraper

class VipScraper(BaseScraper):
    def search(self, keyword, max_pages=3):
        results = []
        print(f"🛍️ [唯品会] 启动搜索: {keyword}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
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
            
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page = context.new_page()
            
            try:
                # 唯品会搜索 URL
                url = f"https://category.vip.com/suggest.php?keyword={keyword}"
                page.goto(url, timeout=40000)
                
                # 等待商品列表
                try:
                    page.wait_for_selector(".c-goods-item", timeout=10000)
                except:
                    print("   ⚠️ 唯品会未找到商品或加载超时")
                
                # 滚动加载
                for _ in range(5):
                    page.mouse.wheel(0, 1000)
                    time.sleep(0.5)
                
                items = page.query_selector_all(".c-goods-item")
                print(f"   📄 唯品会发现 {len(items)} 个商品")
                
                for item in items:
                    try:
                        # 标题
                        title_el = item.query_selector(".c-goods-item__name")
                        title = title_el.inner_text().strip() if title_el else ""
                        
                        # 价格
                        price_el = item.query_selector(".c-goods-item__sale-price")
                        price = price_el.inner_text().replace("¥", "").strip() if price_el else "0"
                        
                        # 折扣/原价
                        market_price_el = item.query_selector(".c-goods-item__market-price")
                        market_price = market_price_el.inner_text().strip() if market_price_el else ""
                        
                        # 链接
                        link_el = item.query_selector("a")
                        link = link_el.get_attribute("href") if link_el else ""
                        if link and not link.startswith("http"):
                            link = "https:" + link
                            
                        if title:
                            results.append({
                                "id": link.split('/')[-1].split('.')[0] if link else str(random.randint(10000,99999)),
                                "title": f"[唯品会] {title} {market_price}",
                                "price": price,
                                "shop": "唯品会自营",
                                "deal_count": "热销中", # 唯品会不常显示具体销量
                                "link": link,
                                "platform": "Vipshop"
                            })
                    except:
                        continue
                        
            except Exception as e:
                print(f"   ❌ 唯品会抓取异常: {e}")
                
            browser.close()
            
        return results

    def get_details(self, item_id):
        pass
