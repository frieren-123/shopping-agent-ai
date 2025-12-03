import os
import json

def parse_taobao_json(json_file_path):
    """
    解析新的 JSON 格式详情数据
    """
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    parsed = {
        "title": data.get("title", "未知标题"),
        "price": data.get("price", "未知价格"),
        "shop_name": data.get("shop", "未知店铺"),
        "source_file": os.path.basename(json_file_path),
        "comments": [],
        "specs": []
    }

    # 提取评论
    raw_reviews = data.get("captured_reviews", [])
    for review in raw_reviews:
        # 尝试提取评论内容，结构可能多变
        content = review.get("rateContent") or review.get("content") or ""
        if content:
            parsed["comments"].append(content)
    
    # 提取规格参数
    raw_props = data.get("captured_props", [])
    # props 可能是 list 或 dict
    if isinstance(raw_props, list):
        for prop in raw_props:
            name = prop.get("name")
            value = prop.get("value")
            if name and value:
                parsed["specs"].append(f"{name}: {value}")
    elif isinstance(raw_props, dict):
        for k, v in raw_props.items():
             parsed["specs"].append(f"{k}: {v}")

    # 限制数量
    parsed["comments"] = parsed["comments"][:15]
    parsed["specs"] = parsed["specs"][:20]
    
    return parsed

def parse_all(input_dir="data/details"):
    results = []
    if not os.path.exists(input_dir):
        print(f"目录 {input_dir} 不存在")
        return []

    for filename in os.listdir(input_dir):
        if filename.endswith(".json"):
            path = os.path.join(input_dir, filename)
            print(f"正在解析: {filename} ...")
            try:
                item_data = parse_taobao_json(path)
                results.append(item_data)
            except Exception as e:
                print(f"解析失败 {filename}: {e}")
    
    # 保存解析结果
    with open("data/parsed.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 解析完成，共 {len(results)} 个商品，结果已保存至 data/parsed.json")
    return results

if __name__ == "__main__":
    parse_all()
