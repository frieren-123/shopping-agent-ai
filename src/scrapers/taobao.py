import os
import time
import random
import json
import re
from playwright.sync_api import sync_playwright
from .base import BaseScraper

class TaobaoScraper(BaseScraper):
    def __init__(self):
        self.global_products = []
        self.global_details = {}
        self.keyword = "" # Store keyword for filtering

    def _handle_search_response(self, response):
        # 放宽拦截条件：只要是 API 请求或者包含 search 关键字
        resource_type = response.request.resource_type
        if resource_type in ["xhr", "fetch", "script"]:
            try:
                content_type = response.headers.get("content-type", "")
                if "json" in content_type or "javascript" in content_type:
                    text = response.text()
                    
                    # 尝试解析 mtopjsonp
                    if text.strip().startswith("mtopjsonp") or text.strip().startswith("jsonp"):
                        match = re.search(r'\((.*)\)', text)
                        if match:
                            text = match.group(1)

                    if '"raw_title"' in text or '"view_price"' in text or '"title":' in text:
                        if "suggest" in response.url: return 

                        # print(f"   ⚡ 捕获到疑似商品数据: {response.url[:60]}...")
                        
                        # 尝试直接 JSON 解析 (更准确)
                        try:
                            data = json.loads(text)
                            # 淘宝 API 结构多变，尝试几种常见路径
                            # 1. mods.itemlist.data.auctions
                            itemlist = data.get("mods", {}).get("itemlist", {}).get("data", {}).get("auctions", [])
                            if not itemlist:
                                # 2. itemsArray
                                itemlist = data.get("itemsArray", [])
                            
                            if itemlist:
                                count = 0
                                seen_ids = set(p['id'] for p in self.global_products)
                                for item in itemlist:
                                    nid = item.get("nid") or item.get("item_id")
                                    if not nid or nid in seen_ids: continue
                                    
                                    title = item.get("raw_title") or item.get("title", "")
                                    price = item.get("view_price") or item.get("price", "0")
                                    sales = item.get("view_sales") or item.get("sold", "0")
                                    link = item.get("detail_url") or item.get("url", "")
                                    
                                    # 移除严格的关键词过滤，信任淘宝的搜索结果
                                    # if self.keyword[:1] not in title: continue
                                    
                                    # 识别天猫
                                    shop_name = item.get("nick", "淘宝店铺")
                                    is_tmall = False
                                    if "旗舰店" in shop_name or "专卖店" in shop_name or item.get("user_type") == "1": # user_type 1 通常是天猫
                                        is_tmall = True
                                        shop_name = "🔴 [天猫] " + shop_name
                                    
                                    self.global_products.append({
                                        "id": nid,
                                        "title": title,
                                        "price": price,
                                        "link": link if link.startswith("http") else "https:" + link,
                                        "shop": shop_name,
                                        "deal_count": sales,
                                        "platform": "Tmall" if is_tmall else "Taobao"
                                    })
                                    seen_ids.add(nid)
                                    count += 1
                                if count > 0:
                                    print(f"   ✅ 通过 API 拦截解析了 {count} 个商品")
                                    return
                        except:
                            pass

                        # 如果 JSON 解析失败，回退到正则提取
                        titles = re.findall(r'"raw_title":"([^"]+)"', text)
                        if not titles:
                            titles = re.findall(r'"title":"([^"]+)"', text)
                        
                        prices = re.findall(r'"view_price":"([^"]+)"', text)
                        nids = re.findall(r'"nid":"([^"]+)"', text)
                        sales = re.findall(r'"view_sales":"([^"]+)"', text)
                        shops = re.findall(r'"nick":"([^"]+)"', text)

                        if titles and len(titles) > 0:
                            # print(f"   ✅ 成功提取到 {len(titles)} 条记录")
                            for i in range(len(titles)):
                                price = prices[i] if i < len(prices) else "未知"
                                nid = nids[i] if i < len(nids) else ""
                                sale = sales[i] if i < len(sales) else "0"
                                shop = shops[i] if i < len(shops) else "未知店铺"
                                title = titles[i]

                                # 简单过滤：标题必须包含关键词的一部分 (避免完全不相关的推荐)
                                # 如果关键词很长，取前两个字
                                # filter_key = self.keyword[:2] if len(self.keyword) >= 2 else self.keyword
                                # if filter_key and filter_key not in title:
                                #    continue

                                if nid and not any(p['id'] == nid for p in self.global_products):
                                    self.global_products.append({
                                        "id": nid,
                                        "title": title,
                                        "price": price,
                                        "link": f"https://item.taobao.com/item.htm?id={nid}",
                                        "shop": shop,
                                        "deal_count": sale
                                    })

            except Exception:
                pass

    def _extract_from_dom(self, page):
        """
        备用方案：直接从页面 DOM 提取商品信息
        """
        print("   ⚠️ 网络拦截数据不足，尝试从页面元素提取...")
        try:
            # 调试：打印页面内容的一小部分，看看是否加载了验证码或者空页面
            content = page.content()
            if "验证码" in content or "baxia-dialog" in content:
                print("   🚨 检测到验证码拦截！")
            elif "没有找到相关宝贝" in content:
                print("   ⚠️ 页面显示没有找到相关宝贝")
            
            # 查找所有包含 item.htm 的链接 (这是淘宝商品的特征)
            # 淘宝的商品卡片通常包含一个指向 item.htm 的链接
            # 尝试更宽泛的选择器
            items = page.query_selector_all('a')
            
            # 去重 ID
            seen_ids = set(p['id'] for p in self.global_products)
            
            count = 0
            for item in items:
                try:
                    href = item.get_attribute("href")
                    if not href or "item.htm" not in href: continue
                    
                    # 提取 ID
                    match = re.search(r'id=(\d+)', href)
                    if not match: continue
                    nid = match.group(1)
                    
                    if nid in seen_ids: continue
                    
                    # 尝试获取标题
                    # 策略1: 图片的 alt 属性
                    title = ""
                    img = item.query_selector("img")
                    if img:
                        title = img.get_attribute("alt")
                    
                    # 策略2: 链接本身的文本
                    if not title:
                        title = item.inner_text().strip()
                        
                    # 策略3: 尝试找附近的标题元素 (向上找父级再找文本)
                    if not title or len(title) < 5:
                        # 这是一个简化的假设，实际可能需要更复杂的遍历
                        pass

                    # 价格提取 (尝试在父级文本中找 ¥)
                    price = "未知"
                    try:
                        # 向上找几层，直到找到包含价格的容器
                        parent = item
                        for _ in range(5):
                            parent = parent.query_selector("xpath=..")
                            if not parent: break
                            parent_text = parent.inner_text()
                            if "¥" in parent_text:
                                price_match = re.search(r'¥\s*([\d\.]+)', parent_text)
                                if price_match:
                                    price = price_match.group(1)
                                    break
                    except:
                        pass

                    # 过滤
                    filter_key = self.keyword[:2] if len(self.keyword) >= 2 else self.keyword
                    # 宽松过滤：只要包含关键词的一个字，或者标题很长且包含相关词
                    # 这里我们稍微放宽一点，因为 DOM 提取的标题可能不完整
                    # if filter_key and filter_key not in title:
                        # 尝试更宽松的匹配
                        # if len(self.keyword) > 0 and self.keyword[0] in title:
                             # pass # 允许
                        # else:
                             # print(f"   🗑️ 过滤掉无关商品: {title}")
                             # continue

                    if title:
                        link = href if href.startswith("http") else "https:" + href
                        self.global_products.append({
                            "id": nid,
                            "title": title,
                            "price": price,
                            "link": link,
                            "shop": "淘宝店铺", # DOM 难提取，暂且默认
                            "deal_count": "未知"
                        })
                        seen_ids.add(nid)
                        count += 1
                except:
                    continue
            
            if count > 0:
                print(f"   ✅ 通过页面元素补充了 {count} 个商品")
            else:
                print("   ❌ DOM 提取也未找到商品，可能是页面结构变化或反爬虫")
                # 尝试打印页面上的所有链接，看看有没有 item.htm
                # links = [l.get_attribute("href") for l in items if l.get_attribute("href") and "item.htm" in l.get_attribute("href")]
                # print(f"   🔍 页面上包含 item.htm 的链接数: {len(links)}")
                
        except Exception as e:
            print(f"   ❌ DOM 提取失败: {e}")

    def search(self, keyword, max_pages=3):
        self.global_products = []
        self.keyword = keyword
        
        with sync_playwright() as p:
            # ⚠️ 严重警告：淘宝对 Headless 模式检测极严，必须使用有头模式 (headless=False)
            # 否则极易触发风控，导致账号被限制
            browser = p.chromium.launch(
                headless=False, 
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars",
                    "--window-size=1280,800",
                    "--disable-extensions"
                ],
                ignore_default_args=["--enable-automation"]
            )
            
            auth_file = "auth.json"
            context_args = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "viewport": {"width": 1280, "height": 800},
                "device_scale_factor": 1,
            }
            
            # 1. 登录持久化逻辑优化
            if os.path.exists(auth_file):
                print("🔑 [系统] 加载历史登录凭证...")
                context_args["storage_state"] = auth_file
            
            context = browser.new_context(**context_args)
            
            # 注入强力防检测脚本
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.navigator.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            """)
            
            page = context.new_page()
            # 开启请求拦截，用于获取 API 数据
            page.on("response", self._handle_search_response)

            print("🚀 [淘宝] 正在连接...")
            try:
                page.goto("https://www.taobao.com/", timeout=30000)
            except:
                print("   ⚠️ 首页加载超时，尝试直接搜索...")

            # 2. 智能登录检测
            # 如果跳转到了 login.taobao.com 或者页面上有登录框
            if "login.taobao.com" in page.url or page.query_selector(".login-btn") or page.query_selector("a.h-login"):
                print("🔔 [需要登录] 凭证已过期或不存在。")
                print("👉 请在弹出的浏览器中扫码登录。")
                
                try:
                    # 等待直到不再是登录页
                    page.wait_for_url(lambda u: "login" not in u, timeout=300000) # 5分钟等待时间
                    print("✅ 检测到登录成功！")
                    # 保存新的凭证
                    context.storage_state(path=auth_file)
                    print("💾 新的登录状态已保存。")
                except:
                    print("❌ 登录超时，程序可能无法获取数据。")

            for page_num in range(1, max_pages + 1):
                # 🛡️ 安全延迟：每页之间随机暂停，模拟人类行为，防止触发风控
                if page_num > 1:
                    sleep_time = random.uniform(3, 6)
                    print(f"   💤 休息 {sleep_time:.1f} 秒以防检测...")
                    time.sleep(sleep_time)

                offset = (page_num - 1) * 44
                search_url = f"https://s.taobao.com/search?q={keyword}&s={offset}"
                
                print(f"🚀 [第 {page_num}/{max_pages} 页] 正在搜索: {keyword}")
                
                try:
                    page.goto(search_url, timeout=60000)
                    
                    # 3. 反爬虫检测 (滑块/验证码/风控)
                    content = page.content()
                    if "baxia-dialog" in content or "验证码" in content or "punish" in page.url:
                        print("🚨 [严重警告] 触发了淘宝风控验证！")
                        print("👉 请手动在浏览器中完成滑块验证或解除限制...")
                        # 播放提示音 (Windows)
                        print("\a") 
                        input("✅ 验证完成后，请务必按 [回车] 继续...")
                    
                    # 等待商品列表加载
                    try:
                        # 尝试等待商品容器
                        page.wait_for_selector("div[class*='Content--contentInner']", timeout=10000)
                    except:
                        pass

                    # 模拟快速浏览 (触发懒加载)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                    time.sleep(1)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1)
                    
                    # 4. 多重数据提取策略
                    current_count = len(self.global_products)
                    
                    # 策略 A: 网络拦截 (已通过 page.on 自动执行)
                    
                    # 策略 B: 页面脚本数据提取 (最快，最全)
                    if len(self.global_products) == current_count:
                        self._extract_from_script_data(page)
                    
                    # 策略 C: DOM 暴力提取 (兜底)
                    if len(self.global_products) == current_count:
                        self._extract_from_dom_desktop(page)
                        
                    new_count = len(self.global_products) - current_count
                    print(f"   📊 本页新增: {new_count} 个商品")
                    
                except Exception as e:
                    print(f"   ❌ 本页抓取异常: {e}")

            page.remove_listener("response", self._handle_search_response)
            browser.close()
            
        return self.global_products

    def _extract_from_script_data(self, page):
        """
        从页面嵌入的 JSON 数据中提取 (g_page_config)
        这是淘宝最快的数据源，不需要解析 DOM
        """
        print("   ⚡ 尝试从页面脚本提取数据...")
        try:
            # 尝试执行 JS 获取 g_page_config
            data = page.evaluate("() => { return window.g_page_config; }")
            if data and "mods" in data:
                itemlist = data["mods"].get("itemlist", {}).get("data", {}).get("auctions", [])
                count = 0
                seen_ids = set(p['id'] for p in self.global_products)
                
                for item in itemlist:
                    nid = item.get("nid")
                    if not nid or nid in seen_ids: continue
                    
                    title = item.get("raw_title", "")
                    price = item.get("view_price", "0")
                    sales = item.get("view_sales", "0")
                    pic = item.get("pic_url", "")
                    link = item.get("detail_url", "")
                    
                    # 过滤
                    # if self.keyword[:2] not in title: continue
                    
                    self.global_products.append({
                        "id": nid,
                        "title": title,
                        "price": price,
                        "link": link if link.startswith("http") else "https:" + link,
                        "shop": item.get("nick", "淘宝店铺"),
                        "deal_count": sales
                    })
                    seen_ids.add(nid)
                    count += 1
                
                if count > 0:
                    print(f"   ✅ 通过脚本数据提取了 {count} 个商品")
                    return
        except:
            pass

    def _extract_from_dom_desktop(self, page):
        """
        桌面端 DOM 提取 (通用兜底版)
        """
        print("   ⚠️ 尝试通用 DOM 提取...")
        
        # 调试信息：如果页面异常，打印出来
        title = page.title()
        if "登录" in title or "验证" in title:
             print(f"   🚨 页面状态异常: {title}")
        
        try:
            # 寻找所有带 item.htm 的链接
            items = page.query_selector_all("a[href*='item.htm']")
            if not items:
                 print(f"   🔍 未找到商品链接。当前页面标题: {title}")
                 # 尝试打印页面文本的前 100 个字符
                 # print(f"   📄 页面内容摘要: {page.inner_text()[:100]}")

            seen_ids = set(p['id'] for p in self.global_products)
            count = 0
            
            for item in items:
                try:
                    href = item.get_attribute("href")
                    # 提取 ID
                    match = re.search(r'id=(\d+)', href)
                    if not match: continue
                    nid = match.group(1)
                    if nid in seen_ids: continue
                    
                    # 尝试获取包含该链接的整个卡片容器
                    # 向上找 3-4 层
                    card = item
                    found_price = False
                    price = "未知"
                    title = ""
                    
                    # 简单的向上查找逻辑
                    for _ in range(5):
                        parent = card.query_selector("xpath=..")
                        if not parent: break
                        card = parent
                        text = card.inner_text()
                        if "¥" in text or "￥" in text:
                            found_price = True
                            # 提取价格
                            p_match = re.search(r'[¥￥]\s*([\d\.]+)', text)
                            if p_match: price = p_match.group(1)
                            
                            # 提取标题 (排除价格后的最长文本)
                            lines = text.split('\n')
                            valid_lines = [l for l in lines if len(l) > 5 and '¥' not in l]
                            if valid_lines:
                                title = max(valid_lines, key=len)
                            break
                    
                    if not found_price: continue
                    
                    # 宽松过滤
                    # if self.keyword[:1] not in title: continue

                    self.global_products.append({
                        "id": nid,
                        "title": title,
                        "price": price,
                        "link": href if href.startswith("http") else "https:" + href,
                        "shop": "淘宝店铺",
                        "deal_count": "未知"
                    })
                    seen_ids.add(nid)
                    count += 1
                except:
                    continue
            
            if count > 0:
                print(f"   ✅ 通过 DOM 提取了 {count} 个商品")
                
        except Exception as e:
            print(f"   ❌ DOM 提取失败: {e}")

    def _handle_detail_response(self, response):
        try:
            url = response.url
            if "rate" in url or "detail" in url or "mtop" in url:
                content_type = response.headers.get("content-type", "")
                if "json" in content_type or "javascript" in content_type:
                    text = response.text()
                    
                    if text.strip().startswith("mtopjsonp") or text.strip().startswith("jsonp"):
                        match = re.search(r'\((.*)\)', text)
                        if match:
                            text = match.group(1)
                    
                    try:
                        data = json.loads(text)
                        
                        if "rateList" in text or "rateDetail" in text:
                            if "rateList" not in self.global_details:
                                self.global_details["rateList"] = []
                            
                            rate_list = data.get("data", {}).get("rateDetail", {}).get("rateList", [])
                            if rate_list:
                                print(f"   💬 捕获到 {len(rate_list)} 条评论数据")
                                self.global_details["rateList"].extend(rate_list)

                        if "item" in text and "props" in text:
                             if "itemProps" not in self.global_details:
                                 self.global_details["itemProps"] = {}
                             
                             props = data.get("data", {}).get("item", {}).get("props", [])
                             if props:
                                 print(f"   📝 捕获到商品参数数据")
                                 self.global_details["itemProps"] = props

                    except:
                        pass
        except:
            pass

    def get_details(self, candidates):
        """
        深度采集 (桌面端)
        """
        if not candidates:
            return

        print(f"🚀 开始深度采集 {len(candidates)} 个精选商品 (桌面端模式)...")
        os.makedirs("data/details", exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars",
                    "--window-size=1280,800",
                    "--disable-extensions"
                ],
                ignore_default_args=["--enable-automation"]
            )
            
            auth_file = "auth.json"
            context_args = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "viewport": {"width": 1280, "height": 800},
                "device_scale_factor": 1,
            }
            
            if os.path.exists(auth_file):
                context_args["storage_state"] = auth_file
                
            context = browser.new_context(**context_args)
            
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.navigator.chrome = { runtime: {} };
            """)

            page = context.new_page()
            page.on("response", self._handle_detail_response)

            # 检查登录
            try:
                page.goto("https://www.taobao.com/")
                time.sleep(2)
                if "login" in page.url or page.query_selector(".login-btn") or page.query_selector("a.h-login"):
                     print("🔔 [请注意]：详情页采集也需要登录。")
                     input("✅ 登录完成后，请在控制台按 [回车] 键继续...")
                     context.storage_state(path=auth_file)
            except:
                pass

            for i, item in enumerate(candidates):
                self.global_details = {"rateList": [], "itemProps": []}
                
                url = item['link']
                print(f"🔄 [{i+1}/{len(candidates)}] 正在深度抓取: {item['title'][:20]}...")
                
                try:
                    if not url.startswith("http"):
                        url = "https:" + url
                    
                    page.goto(url, timeout=60000)
                    time.sleep(3)
                    
                    # 模拟滚动
                    page.mouse.wheel(0, 1000)
                    time.sleep(1)
                    
                    # 尝试点击“累计评价” (桌面端)
                    try:
                        # 寻找包含“评价”的 Tab
                        # 淘宝桌面端通常是 <a ...>累计评价 <span ...>...</span></a>
                        page.click("a:has-text('累计评价')", timeout=3000)
                        time.sleep(2)
                    except:
                        pass
                    
                    # DOM 提取参数 (桌面端)
                    captured_props = self.global_details.get("itemProps", [])
                    if not captured_props:
                        try:
                            # 桌面端参数通常在 ul.attributes-list
                            props_el = page.query_selector("ul.attributes-list")
                            if props_el:
                                items = props_el.query_selector_all("li")
                                captured_props = [{"name": "参数", "value": li.inner_text()} for li in items]
                            else:
                                # 备用：尝试找 .tm-table-view (天猫)
                                items = page.query_selector_all(".tm-table-view tr")
                                for tr in items:
                                    text = tr.inner_text().replace('\n', ':')
                                    captured_props.append({"name": "参数", "value": text})
                        except:
                            pass

                    # DOM 提取评论 (桌面端)
                    captured_reviews = self.global_details.get("rateList", [])
                    if not captured_reviews:
                        try:
                            # 尝试提取评论文本
                            # 淘宝评论通常在 .tm-rate-content
                            reviews = page.query_selector_all(".tm-rate-content, .review-content")
                            for r in reviews[:10]:
                                captured_reviews.append({"content": r.inner_text()})
                        except:
                            pass

                    detail_data = {
                        "id": item['id'],
                        "title": item['title'],
                        "price": item['price'],
                        "shop": item['shop'],
                        "captured_reviews": captured_reviews,
                        "captured_props": captured_props
                    }
                    
                    file_name = f"data/details/{item['id']}.json"
                    with open(file_name, "w", encoding="utf-8") as f:
                        json.dump(detail_data, f, ensure_ascii=False, indent=2)
                    
                    print(f"   ✅ 已保存详情数据: {file_name}")
                    
                except Exception as e:
                    print(f"   ❌ 抓取失败: {e}")

            browser.close()
