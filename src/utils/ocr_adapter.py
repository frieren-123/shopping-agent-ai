import os
import logging
import re

# 抑制 PaddleOCR 的日志输出
os.environ['FLAGS_minloglevel'] = '2'

class OCRAdapter:
    _instance = None
    _ocr = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OCRAdapter, cls).__new__(cls)
        return cls._instance

    def initialize(self):
        """懒加载 PaddleOCR，避免启动过慢"""
        if self._ocr is None:
            try:
                print("   🧠 正在初始化 PaddleOCR 引擎 (首次运行可能需要下载模型)...")
                from paddleocr import PaddleOCR
                # use_angle_cls=True 自动纠正方向, lang="ch" 支持中文
                self._ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
                print("   ✅ PaddleOCR 初始化完成")
            except ImportError:
                print("   ❌ 无法导入 paddleocr，请确保已安装: pip install paddlepaddle paddleocr")
                self._ocr = None
            except Exception as e:
                print(f"   ❌ PaddleOCR 初始化失败: {e}")
                self._ocr = None

    def extract_text(self, image_path):
        """从图片路径提取文本"""
        if self._ocr is None:
            self.initialize()
        
        if self._ocr is None:
            return []

        try:
            # result = [[[[x1,y1],[x2,y2]...], ("text", conf)], ...]
            result = self._ocr.ocr(image_path, cls=True)
            if not result or result[0] is None:
                return []
            
            # 展平结果
            flat_result = []
            for line in result[0]:
                # line format: [box, (text, confidence)]
                text = line[1][0]
                box = line[0] # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                # 计算中心 Y 坐标，用于后续排序
                center_y = sum([p[1] for p in box]) / 4
                flat_result.append({
                    "text": text,
                    "box": box,
                    "center_y": center_y
                })
            
            return flat_result
        except Exception as e:
            print(f"   ⚠️ OCR 识别出错: {e}")
            return []

    def parse_jd_products(self, ocr_results):
        """
        针对京东搜索结果页面的 OCR 结果进行解析
        策略：寻找价格格式 (￥xxx)，然后关联附近的文本作为标题
        """
        products = []
        # 按 Y 坐标排序，模拟从上到下的阅读顺序
        sorted_lines = sorted(ocr_results, key=lambda x: x['center_y'])
        
        # 价格正则：￥123.00 或 ¥123
        price_pattern = re.compile(r'[￥¥]\s*(\d+(?:\.\d+)?)')
        
        for i, line in enumerate(sorted_lines):
            text = line['text']
            price_match = price_pattern.search(text)
            
            if price_match:
                price = price_match.group(1)
                
                # 寻找标题：通常在价格的上方或紧邻的下方
                # 简单策略：取价格前 1-2 行中字数较长的作为标题
                title = "未知商品"
                
                # 向前回溯找标题
                for j in range(i - 1, max(-1, i - 4), -1):
                    prev_text = sorted_lines[j]['text']
                    # 排除干扰词
                    if "评价" in prev_text or "自营" in prev_text or len(prev_text) < 5:
                        continue
                    title = prev_text
                    break
                
                # 如果向前没找到，可能标题在价格后面（某些布局）
                if title == "未知商品" and i + 1 < len(sorted_lines):
                    next_text = sorted_lines[i+1]['text']
                    if len(next_text) > 5:
                        title = next_text

                # 寻找店铺：通常包含 "店" 或 "自营"
                shop = "京东卖家"
                for j in range(i + 1, min(len(sorted_lines), i + 5)):
                    cand_text = sorted_lines[j]['text']
                    if "店" in cand_text or "自营" in cand_text:
                        shop = cand_text
                        break

                products.append({
                    "title": title,
                    "price": price,
                    "shop": shop,
                    "platform": "JD (OCR)",
                    "link": "" # OCR 无法获取链接
                })
                
        return products
