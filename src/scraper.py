import os
import time
import random
import json
import re
from playwright.sync_api import sync_playwright

# 全局变量，确保数据不会丢失
GLOBAL_PRODUCTS = []

def handle_response(response):
    global GLOBAL_PRODUCTS
    
    # 放宽拦截条件：只要是 API 请求或者包含 search 关键字
    # 排除图片、CSS、JS 等静态资源
    resource_type = response.request.resource_type
    if resource_type in ["xhr", "fetch", "script"]:
        try:
            # 检查 Content-Type
            content_type = response.headers.get("content-type", "")
            if "json" in content_type or "javascript" in content_type:
                text = response.text()
                
                # 关键特征匹配：淘宝搜索结果通常包含 raw_title 或 view_price
                if '"raw_title"' in text or '"view_price"' in text or '"title":' in text:
                    # 排除一些无关的 API
                    if "suggest" in response.url: return 

                    print(f"   ⚡ 捕获到疑似商品数据: {response.url[:60]}...")
                    
                    # 尝试多种字段名匹配
                    # 方案 A: raw_title (常见于 mtop 接口)
                    titles = re.findall(r'"raw_title":"([^"]+)"', text)
                    if not titles:
                        # 方案 B: title (常见于 pc 接口)
                        titles = re.findall(r'"title":"([^"]+)"', text)
                    
                    prices = re.findall(r'"view_price":"([^"]+)"', text)
                    nids = re.findall(r'"nid":"([^"]+)"', text)
                    
                    # 销量 (view_sales)
                    sales = re.findall(r'"view_sales":"([^"]+)"', text)
                    
                    # 店铺名 (nick)
                    shops = re.findall(r'"nick":"([^"]+)"', text)

                    if titles and len(titles) > 0:
                        print(f"   ✅ 成功提取到 {len(titles)} 条记录")
                        for i in range(len(titles)):
                            # 尽可能多地匹配字段
                            price = prices[i] if i < len(prices) else "未知"
                            nid = nids[i] if i < len(nids) else ""
                            sale = sales[i] if i < len(sales) else "0"
                            shop = shops[i] if i < len(shops) else "未知店铺"
                            
                            if nid and not any(p['id'] == nid for p in GLOBAL_PRODUCTS):
                                GLOBAL_PRODUCTS.append({
                                    "id": nid,
                                    "title": titles[i],
                                    "price": price,
                                    "link": f"https://item.taobao.com/item.htm?id={nid}",
                                    "shop": shop,
                                    "deal_count": sale
                                })
                        print(f"   📈 当前全局列表总数: {len(GLOBAL_PRODUCTS)}")
        except Exception as e:
            pass # 忽略解析错误
        except Exception as e:
            pass # 忽略解析错误

def run_scraper(keyword=None, max_pages=None):
    global GLOBAL_PRODUCTS
    GLOBAL_PRODUCTS = [] # 重置
    
    with sync_playwright() as p:
        # 启动有头浏览器，方便用户扫码
        # 添加反爬虫绕过参数
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        
        # 注入脚本以进一步隐藏自动化特征
        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # 开启监听
        page.on("response", handle_response)

        print("🚀 正在打开淘宝首页，请准备扫码登录...")
        page.goto("https://www.taobao.com")
        
        # 等待用户登录
        print("🔔 [请注意]：淘宝必须登录才能查看详情。")
        print("👉 请在弹出的浏览器中完成扫码登录。")
        # 只有在没有提供关键词时才暂停等待用户确认，或者如果提供了关键词但为了确保登录成功，也可以等待
        # 为了自动化流畅，如果提供了关键词，我们假设用户会在脚本启动后的短时间内完成登录，或者我们可以检测登录状态
        # 这里保留手动确认，因为扫码登录很难自动化检测完全
        input("✅ 登录完成后，请在控制台按 [回车] 键继续...")

        # 确保保存目录存在
        os.makedirs("data", exist_ok=True)

        # 改为输入关键词，进行批量搜索
        if not keyword:
            keyword = input("🔍 请输入搜索关键词 (例如 '机械键盘'): ").strip()
        
        if not keyword:
            print("❌ 关键词不能为空！")
            return
            
        if not max_pages:
            max_pages_input = input("📄 请输入要抓取的页数 (默认 5): ").strip()
            max_pages = int(max_pages_input) if max_pages_input.isdigit() else 5

        for page_num in range(1, max_pages + 1):
            # 构造淘宝搜索链接 (淘宝搜索页翻页通常是 s 参数，每页 44 个商品)
            # page 1: s=0, page 2: s=44, page 3: s=88
            offset = (page_num - 1) * 44
            search_url = f"https://s.taobao.com/search?q={keyword}&s={offset}"
            
            print(f"🚀 [第 {page_num}/{max_pages} 页] 正在访问: {search_url}")
            
            try:
                page.goto(search_url, timeout=60000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(random.uniform(3, 5)) # 等待动态内容加载
                
                # 模拟滚动到底部以触发懒加载 (这会触发更多 API 请求)
                for _ in range(5):
                    page.mouse.wheel(0, 1000)
                    time.sleep(1)
                
                # 随机等待，防封
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                print(f"   ❌ 本页抓取失败: {e}")

        # 移除监听
        page.remove_listener("response", handle_response)

        # 保存结果
        output_file = "data/search_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(GLOBAL_PRODUCTS, f, ensure_ascii=False, indent=2)
            
        print(f"\n🎉 海量抓取结束！共收集 {len(GLOBAL_PRODUCTS)} 个商品信息。")
        print(f"📁 结果已保存至: {output_file}")
        print("👉 下一步：请运行分析器进行初筛。")
        
        browser.close()

# 全局变量，用于存储详情页抓取到的数据
GLOBAL_DETAILS = {}

def handle_detail_response(response):
    """
    专门处理详情页的 API 响应
    """
    global GLOBAL_DETAILS
    
    try:
        url = response.url
        # 拦截评论接口 (rate) 和详情接口 (detail)
        if "rate" in url or "detail" in url or "mtop" in url:
            content_type = response.headers.get("content-type", "")
            if "json" in content_type or "javascript" in content_type:
                text = response.text()
                
                # 提取 JSONP 中的 JSON
                if text.strip().startswith("mtopjsonp") or text.strip().startswith("jsonp"):
                    match = re.search(r'\((.*)\)', text)
                    if match:
                        text = match.group(1)
                
                # 尝试解析 JSON
                try:
                    data = json.loads(text)
                    
                    # 识别评论数据
                    if "rateList" in text or "rateDetail" in text:
                        # 找到当前页面的商品 ID (从 URL 或 Referer 中推断，这里简化处理，假设只有一个页面在活动)
                        # 更好的方式是把数据暂存，最后统一关联
                        # 这里我们简单地把所有捕获到的 rateList 存起来
                        if "rateList" not in GLOBAL_DETAILS:
                            GLOBAL_DETAILS["rateList"] = []
                        
                        # 提取评论列表
                        # 结构通常是 data -> rateDetail -> rateList
                        rate_list = data.get("data", {}).get("rateDetail", {}).get("rateList", [])
                        if rate_list:
                            print(f"   💬 捕获到 {len(rate_list)} 条评论数据")
                            GLOBAL_DETAILS["rateList"].extend(rate_list)

                    # 识别商品参数数据
                    if "item" in text and "props" in text:
                         if "itemProps" not in GLOBAL_DETAILS:
                             GLOBAL_DETAILS["itemProps"] = {}
                         
                         # 尝试提取 props
                         props = data.get("data", {}).get("item", {}).get("props", [])
                         if props:
                             print(f"   📝 捕获到商品参数数据")
                             GLOBAL_DETAILS["itemProps"] = props

                except:
                    pass
    except:
        pass

def run_deep_scraper():
    """
    第三阶段：精准深度采集 (升级版：使用网络拦截)
    读取 data/top_candidates.json，抓取详情页
    """
    global GLOBAL_DETAILS
    
    input_file = "data/top_candidates.json"
    if not os.path.exists(input_file):
        print(f"❌ 文件 {input_file} 不存在，请先运行初筛。")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    if not candidates:
        print("⚠️ 候选列表为空。")
        return

    print(f"🚀 开始深度采集 {len(candidates)} 个精选商品 (网络拦截模式)...")
    os.makedirs("data/details", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # 开启监听
        page.on("response", handle_detail_response)

        # 登录检查
        print("🚀 正在打开淘宝首页，请准备扫码登录...")
        page.goto("https://www.taobao.com")
        print("🔔 [请注意]：淘宝必须登录才能查看详情。")
        print("👉 请在弹出的浏览器中完成扫码登录。")
        input("✅ 登录完成后，请在控制台按 [回车] 键继续...")

        for i, item in enumerate(candidates):
            # 重置当前商品的抓取数据
            GLOBAL_DETAILS = {"rateList": [], "itemProps": []}
            
            url = item['link']
            print(f"🔄 [{i+1}/{len(candidates)}] 正在深度抓取: {item['title'][:20]}...")
            
            try:
                if not url.startswith("http"):
                    url = "https:" + url
                
                page.goto(url, timeout=60000)
                page.wait_for_load_state("domcontentloaded")
                
                # 模拟深度浏览
                print("   正在加载详情和评论 (触发 API)...")
                for _ in range(5):
                    page.mouse.wheel(0, 1000)
                    time.sleep(1.5)
                
                # 尝试点击“累计评价”
                try:
                    page.click("text=累计评价", timeout=2000)
                    time.sleep(3) # 等待评论 API 加载
                except:
                    pass
                
                # 保存抓取到的 JSON 数据，而不是 HTML
                detail_data = {
                    "id": item['id'],
                    "title": item['title'],
                    "price": item['price'],
                    "shop": item['shop'],
                    "captured_reviews": GLOBAL_DETAILS.get("rateList", []),
                    "captured_props": GLOBAL_DETAILS.get("itemProps", [])
                }
                
                file_name = f"data/details/{item['id']}.json"
                with open(file_name, "w", encoding="utf-8") as f:
                    json.dump(detail_data, f, ensure_ascii=False, indent=2)
                
                print(f"   ✅ 已保存详情数据: {file_name} (评论数: {len(detail_data['captured_reviews'])})")
                
                time.sleep(random.uniform(3, 5))
                
            except Exception as e:
                print(f"   ❌ 抓取失败: {e}")

        print("🎉 深度采集结束！")
        browser.close()

if __name__ == "__main__":
    print("1. 运行海量列表抓取 (Scraper)")
    print("2. 运行精准深度采集 (Deep Scraper - 需先有 top_candidates.json)")
    choice = input("请选择 (1/2): ").strip()
    
    if choice == "1":
        run_scraper()
    elif choice == "2":
        run_deep_scraper()
    else:
        print("无效选择")
