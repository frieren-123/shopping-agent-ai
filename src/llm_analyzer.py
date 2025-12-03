import os
import json
import sys
from openai import OpenAI
from dotenv import load_dotenv

# 尝试导入 ContextManager
try:
    from src.context.context_manager import ContextManager
except ImportError:
    # 如果直接运行此脚本，可能需要调整路径
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from src.context.context_manager import ContextManager
    except ImportError:
        print("⚠️ 无法导入 ContextManager，将使用默认配置")
        ContextManager = None

# 加载环境变量
load_dotenv()

def get_llm_client():
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    
    if not api_key or "xxxx" in api_key:
        raise ValueError("请先在 .env 文件中配置正确的 LLM_API_KEY")
    
    # 初始化客户端
    return OpenAI(api_key=api_key, base_url=base_url)

def ask_clarifying_questions(product_name):
    """
    根据商品名称生成 3 个关键的澄清问题，以便更精准地筛选。
    """
    client = get_llm_client()
    model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    
    prompt = f"""
    用户想要购买："{product_name}"。
    为了帮用户筛选出最合适的商品，请提出 3 个最重要的澄清问题（例如预算、具体功能、使用场景等）。
    
    请直接返回一个 JSON 字符串数组，格式如下：
    ["问题1", "问题2", "问题3"]
    不要包含任何其他文字。
    """
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个专业的购物顾问。"},
                {"role": "user", "content": prompt}
            ]
        )
        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "")
        questions = json.loads(content)
        return questions
    except Exception as e:
        print(f"⚠️ 生成问题失败: {e}")
        return []

def filter_products(user_requirements, top_n=5):
    """
    第一阶段：智能初筛
    读取 search_results.json，根据用户需求筛选出 Top N
    """
    input_file = "data/search_results.json"
    if not os.path.exists(input_file):
        print(f"文件 {input_file} 不存在，请先运行爬虫抓取列表。")
        return []

    with open(input_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    if not products:
        print("商品列表为空。")
        return []

    print(f"正在对 {len(products)} 个商品进行初筛，需求：{user_requirements}，目标数量：{top_n}")
    
    client = get_llm_client()
    model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    # 简化数据以节省 Token
    products_summary = []
    for p in products[:100]: # 限制前 100 个，避免 token 溢出
        products_summary.append({
            "id": p.get("id"),
            "title": p.get("title"),
            "price": p.get("price"),
            "sales": p.get("deal_count"),
            "shop": p.get("shop")
        })

    # 获取用户上下文 (MineContext)
    user_context_prompt = ""
    if ContextManager:
        ctx_mgr = ContextManager()
        user_context_prompt = ctx_mgr.get_critical_thinking_prompt()

    prompt = f"""
    {user_context_prompt}

    你是一个专业的电商选品专家。用户想买："{user_requirements}"。
    
    下面是抓取到的商品列表（JSON格式）：
    {json.dumps(products_summary, ensure_ascii=False)}
    
    请根据用户的预算和需求，筛选出最值得深入研究的 {top_n} 个商品。
    
    ### 思考步骤 (Chain of Thought):
    1. **分析需求**: 用户的核心痛点是什么？预算范围是多少？
    2. **排除法**: 剔除明显不符合预算、评分过低或与关键词不符的商品。
    3. **优选法**: 在剩余商品中，寻找性价比最高、品牌口碑好或有独特卖点的商品。
    4. **防坑检查**: 检查是否有虚假宣传或“网红”溢价过高的迹象。

    ### 输出要求:
    请返回一个 JSON 数组，只包含这 {top_n} 个商品的 ID。
    格式严格如下：
    ["id1", "id2", "id3", "id4", "id5"]
    
    **注意**: 不要返回任何 Markdown 标记（如 ```json），不要返回任何解释文字，只返回纯 JSON 字符串。
    """

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个只输出 JSON 的助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2 # 降低随机性，提高 JSON 格式稳定性
        )
        
        content = response.choices[0].message.content.strip()
        # 清理可能的 markdown 标记
        content = content.replace("```json", "").replace("```", "").strip()
        
        print(f"🔍 LLM 原始响应: {content[:100]}...") # Debug log

        try:
            top_ids = json.loads(content)
        except json.JSONDecodeError:
            print("⚠️ LLM 返回的不是有效的 JSON，尝试修复...")
            # 尝试简单的正则提取
            import re
            top_ids = re.findall(r'"(\d+)"', content)
        
        # 转换为字符串以确保匹配
        top_ids = [str(i) for i in top_ids]
        
        print(f"LLM 选中的 ID: {top_ids}")
        
        top_products = [p for p in products if str(p.get("id")) in top_ids]
        
        # --- Fallback 机制 ---
        if not top_products:
            print("⚠️ LLM 未选中任何商品 (或 ID 匹配失败)。")
            print("🔄 启动自动兜底机制：按销量和价格排序选出 Top 5...")
            
            # 简单的排序逻辑：销量高优先
            def sort_key(p):
                try:
                    return int(p.get("deal_count", "0").replace("+", "").replace("万", "0000"))
                except:
                    return 0
            
            sorted_products = sorted(products, key=sort_key, reverse=True)
            top_products = sorted_products[:top_n]
            print(f"✅ 兜底选中 {len(top_products)} 个商品")
        # ---------------------

        with open("data/top_candidates.json", "w", encoding="utf-8") as f:
            json.dump(top_products, f, ensure_ascii=False, indent=2)
            
        print(f"初筛完成！选出 {len(top_products)} 个候选商品。")
        for p in top_products:
            print(f"   - {p['title']} (¥{p['price']})")
            
        return top_products

    except Exception as e:
        print(f"初筛失败: {e}")
        # 发生异常时也进行兜底
        print("🔄 异常兜底：按默认顺序选取前 5 个")
        top_products = products[:top_n]
        with open("data/top_candidates.json", "w", encoding="utf-8") as f:
            json.dump(top_products, f, ensure_ascii=False, indent=2)
        return top_products

def analyze_products():
    """
    第二阶段：深度分析
    1. 调用 parser 解析 data/details/ 下的 HTML
    2. 调用 LLM 生成最终报告
    """
    # 1. 先运行解析器
    print("正在解析详情页数据...")
    # 动态导入以避免循环依赖
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from product_parser import parse_all
        # 注意：这里我们复用 product_parser.py，让它去解析 data/details 目录
        products = parse_all(input_dir="data/details")
    except ImportError as e:
        print(f"导入解析器失败: {e}")
        return

    if not products:
        print("没有解析到详情数据，请检查 data/details/ 目录下是否有 JSON 文件。")
        return

    # 加载原始链接信息
    url_map = {}
    if os.path.exists("data/top_candidates.json"):
        with open("data/top_candidates.json", "r", encoding="utf-8") as f:
            candidates = json.load(f)
            for c in candidates:
                url_map[str(c.get("id"))] = c.get("link")

    # 将链接注入到解析后的数据中
    for p in products:
        # source_file 格式如 "123456.json"
        p_id = p.get("source_file", "").replace(".json", "")
        if p_id in url_map:
            p["url"] = url_map[p_id]
        else:
            # 如果找不到，尝试构造默认链接
            p["url"] = f"https://item.taobao.com/item.htm?id={p_id}"

    client = get_llm_client()
    model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    print(f"正在调用大模型 ({model}) 进行深度分析，请稍候...")

    # 获取用户上下文 (MineContext)
    user_context_prompt = ""
    if ContextManager:
        ctx_mgr = ContextManager()
        user_context_prompt = ctx_mgr.get_critical_thinking_prompt()

    # 构建 Prompt
    products_str = json.dumps(products, ensure_ascii=False, indent=2)
    
    prompt = f"""
    {user_context_prompt}

    你是一个专业的电商购物顾问。我们已经经过了初筛，现在进入决赛圈。
    以下是 5 个候选商品的详细数据（包含评论、参数等）：
    
    {products_str}
    
    请生成一份详细的购买决策报告，包含以下部分：
    
    ## 1. 候选商品概览
    （列出这几个商品的基本信息，做一个简单的 Markdown 表格对比价格、销量、店铺。**重要：请在表格中的商品名称上加上超链接，格式为 [商品名](URL)**）
    
    ## 2. 深度点评
    （对每个商品进行点评，重点分析：
    - **优点**：基于评论和参数。
    - **缺点/风险**：基于差评或参数短板。
    - **适合人群**：谁应该买它？）
    
    ## 3. 最终推荐 (Winner)
    - **首选推荐**：综合性价比最高的那个。（**请务必附上购买链接**）
    - **备选推荐**：如果有特定需求（如预算更低或性能更强）的选择。（**请务必附上购买链接**）
    - **理由**：为什么选它？
    
    请用 Markdown 格式输出。
    """

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个客观、犀利、不说废话的购物决策助手。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        report = response.choices[0].message.content
        
        # 保存报告
        with open("data/final_report.md", "w", encoding="utf-8") as f:
            f.write(report)
            
        # 生成 HTML 报告
        generate_html_report(report)
            
        print("\n" + "="*30)
        print("最终购买报告生成成功！")
        print("="*30 + "\n")
        print(report)
        print("\n" + "="*30)
        print("报告已保存至 data/final_report.md 和 data/final_report.html")

    except Exception as e:
        print(f"调用大模型失败: {e}")

def generate_html_report(markdown_content):
    """
    将 Markdown 报告转换为美观的 HTML 页面
    """
    html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 购物决策报告</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max_width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }
        .container {
            background-color: #fff;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1, h2, h3 {
            color: #2c3e50;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }
        h1 { text-align: center; border-bottom: none; color: #e67e22; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            border: 1px solid #ddd;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        tr:nth-child(even) { background-color: #f8f8f8; }
        a {
            color: #3498db;
            text-decoration: none;
        }
        a:hover { text-decoration: underline; }
        blockquote {
            border-left: 4px solid #e67e22;
            padding-left: 15px;
            color: #7f8c8d;
            background-color: #fff5e6;
            padding: 10px;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            font-size: 0.8em;
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🛒 AI 购物决策报告</h1>
        <div id="content"></div>
        <div class="footer">
            Generated by AI Shopping Agent
        </div>
    </div>
    <script>
        const markdown = `MARKDOWN_PLACEHOLDER`;
        document.getElementById('content').innerHTML = marked.parse(markdown);
    </script>
</body>
</html>
    """
    
    # Escape backticks in markdown content to avoid breaking JS string
    safe_markdown = markdown_content.replace("`", "\\`").replace("${", "\\${")
    
    html_content = html_template.replace("MARKDOWN_PLACEHOLDER", safe_markdown)
    
    with open("data/final_report.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def analyze_trends(zhihu_data, original_keyword):
    """
    根据知乎的调研结果，优化搜索关键词
    """
    if not zhihu_data:
        return original_keyword
        
    client = get_llm_client()
    model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    
    data_str = json.dumps(zhihu_data, ensure_ascii=False, indent=2)
    
    prompt = f"""
    用户想买："{original_keyword}"。
    我先在知乎/小红书上调研了一下，找到了以下热门文章标题和摘要：
    {data_str}
    
    请执行以下操作：
    1. **批判性思维**：请警惕软文广告（Soft Ads）。如果所有文章都一面倒地推荐某个品牌，这可能是营销攻势。
    2. **提取真实需求**：从用户的讨论中，提取出他们真正关心的**核心参数**（如“成分安全”、“无硅油”），而不是盲目跟随品牌。
    3. **生成关键词**：结合原始需求，生成一个更精准的淘宝/京东搜索关键词。
       - **必须简短**：不要超过 3 个词（例如 "手机 骁龙8Gen3" 而不是 "2024年最新款搭载骁龙8Gen3处理器的手机"）。
       - **去除非关键词**：去掉 "推荐"、"求购"、"怎么样"、"全价位" 等无意义词汇。
       - 如果你觉得热门品牌有营销嫌疑，请生成一个**基于功能/成分**的关键词（如“氨基酸洗发水 敏感肌”），而不是品牌词。
       - 如果热门品牌确实口碑好，可以包含品牌名。
    
    例如：
    - 原需求："洗发水" -> 输出："弱酸性洗发水 控油"
    - 原需求："高性价比手机" -> 输出："手机 骁龙8Gen2"
    
    请直接返回关键词，不要包含任何解释。
    """
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个搜索优化专家。"},
                {"role": "user", "content": prompt}
            ]
        )
        refined_keyword = response.choices[0].message.content.strip()
        print(f"🧠 AI 优化后的搜索词: {refined_keyword}")
        return refined_keyword
    except Exception as e:
        print(f"⚠️ 关键词优化失败: {e}")
        return original_keyword

def extract_info_from_markdown(markdown_text):
    """
    使用 LLM 从 Markdown 文本中提取结构化的商品信息。
    """
    client = get_llm_client()
    model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    
    # 截取前 50000 个字符，避免 Token 溢出 (通常商品列表在前部)
    truncated_text = markdown_text[:50000]
    
    prompt = f"""
    以下是电商搜索结果页面的 Markdown 内容：
    
    {truncated_text}
    
    请从中提取商品列表信息。
    请返回一个 JSON 数组，每个元素包含以下字段：
    - "title": 商品标题 (字符串)
    - "price": 价格 (字符串，如 "299.00")
    - "shop": 店铺名称 (字符串，如果找不到则填 "未知")
    - "link": 商品链接 (字符串，如果找不到则填 "")
    
    只提取前 10 个最相关的商品即可。
    请直接返回 JSON 数组，不要包含 Markdown 标记或其他文字。
    """
    
    try:
        print(f"   ...向 LLM 发送请求 (长度: {len(truncated_text)} chars)...")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个数据提取专家，只输出 JSON。"},
                {"role": "user", "content": prompt}
            ],
            timeout=60  # 设置 60 秒超时
        )
        
        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        
        products = json.loads(content)
        
        if not products:
            print(f"   ⚠️ LLM 返回了空列表。原始响应: {content[:200]}...")

        # 简单的后处理：确保 ID 存在
        for p in products:
            if "id" not in p:
                # 尝试从链接提取 ID
                import re
                link = p.get("link", "")
                id_match = re.search(r'(\d+)\.html', link)
                if id_match:
                    p["id"] = id_match.group(1)
                else:
                    # 随机生成一个 ID 防止报错
                    import random
                    p["id"] = str(random.randint(100000, 999999))
            
            p["platform"] = "JD (AI)"
            p["deal_count"] = "未知" # 列表页通常难提取销量
            
        return products
        
    except Exception as e:
        print(f"⚠️ AI 提取失败: {e}")
        return []

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "filter":
            req = sys.argv[2] if len(sys.argv) > 2 else "高性价比商品"
            filter_products(req)
        elif cmd == "analyze":
            analyze_products()
        else:
            print("未知命令。用法: python src/llm_analyzer.py [filter <需求> | analyze]")
    else:
        print("1. 运行智能初筛 (Filter)")
        print("2. 运行深度分析 (Analyze - 需先有 details HTML)")
        choice = input("请选择 (1/2): ").strip()
        
        if choice == "1":
            req = input("请输入你的具体需求 (如 '100元以内降噪耳机'): ").strip()
            filter_products(req)
        elif choice == "2":
            analyze_products()
        else:
            print("无效选择")
