import pyautogui
import pyperclip
import time
import random
import urllib.parse
import os
from src.utils.ocr_adapter import OCRAdapter

class JDScraper:
    def __init__(self):
        # 安全设置：鼠标移动到左上角可强制终止
        pyautogui.FAILSAFE = True
        # 每次操作后的默认暂停时间
        pyautogui.PAUSE = 0.5
        self.ocr = OCRAdapter()

    def search(self, keyword, max_pages=3):
        results = []
        print(f"🚀 [京东] 启动搜索 (视觉 OCR 模式): {keyword}")
        print("⚠️  请注意：程序将接管您的鼠标和键盘，请不要触碰！")
        print("👉 请在 5 秒内切换到 Edge 浏览器窗口，并保持最大化...")
        
        for i in range(5, 0, -1):
            print(f"   ⏳ {i}...")
            time.sleep(1)
            
        print("   🎬 开始执行...")

        # 尝试点击屏幕中央以激活浏览器窗口
        try:
            width, height = pyautogui.size()
            pyautogui.click(width / 2, height / 2)
            time.sleep(0.5)
        except:
            pass

        try:
            for page_num in range(1, max_pages + 1):
                # 1. 正常访问 URL (不再使用 view-source)
                encoded_keyword = urllib.parse.quote(keyword)
                target_url = f"https://search.jd.com/Search?keyword={encoded_keyword}&page={2 * page_num - 1}"
                
                print(f"   🔄 [第 {page_num} 页] 跳转中...")
                
                # 2. 聚焦地址栏并输入
                pyautogui.hotkey('ctrl', 'l')
                time.sleep(0.5)
                pyperclip.copy(target_url)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.5)
                pyautogui.press('enter')
                
                # 3. 等待加载
                print("   ⏳ 等待页面渲染 (5秒)...")
                time.sleep(5) 
                
                # 4. 滚动加载 (京东懒加载)
                print("   🖱️ 滚动加载内容...")
                for _ in range(4):
                    pyautogui.scroll(-800)
                    time.sleep(1)
                
                # 滚回顶部一点点，确保第一排商品可见
                pyautogui.scroll(2000)
                time.sleep(1)

                # 5. 截图并 OCR
                print("   📸 正在截屏并进行 OCR 识别...")
                screenshot_path = f"temp_page_{page_num}.png"
                pyautogui.screenshot(screenshot_path)
                
                # 调用 PaddleOCR
                ocr_items = self.ocr.extract_text(screenshot_path)
                print(f"   🧠 OCR 识别到 {len(ocr_items)} 个文本块")
                
                # 解析 OCR 结果
                page_products = self.ocr.parse_jd_products(ocr_items)
                print(f"   📄 本页提取到 {len(page_products)} 个商品 (OCR)")
                
                results.extend(page_products)

                # 清理截图
                if os.path.exists(screenshot_path):
                    os.remove(screenshot_path)

                # 翻页休息
                if page_num < max_pages:
                    sleep_time = random.uniform(2, 4)
                    print(f"   💤 休息 {sleep_time:.1f} 秒...")
                    time.sleep(sleep_time)

        except pyautogui.FailSafeException:
            print("   🛑 用户触发了安全终止 (鼠标移到了角落)")
        except Exception as e:
            print(f"   ❌ 发生错误: {e}")
            
        return results

    def get_details(self, item_id):
        pass
