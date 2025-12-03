import os
import base64
from src.llm_analyzer import get_llm_client

class VisualDebugger:
    def __init__(self):
        self.client = None
        try:
            self.client = get_llm_client()
        except:
            pass

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def analyze_failure(self, image_path):
        """
        使用 VLM (视觉大模型) 分析错误截图。
        模拟 Skyvern 的视觉感知能力。
        """
        if not self.client:
            return None
            
        # 获取当前配置的模型
        model = os.getenv("LLM_MODEL", "gpt-3.5-turbo") 
        
        # 简单的模型能力判断
        # DeepSeek-V3 (deepseek-chat) 目前仅支持文本，不支持视觉
        if "deepseek" in model or "gpt-3.5" in model:
            return f"当前配置的模型 ({model}) 不支持视觉分析，已跳过。建议使用 GPT-4o 或 Gemini Pro Vision。"

        try:
            base64_image = self.encode_image(image_path)
            
            print(f"   🧠 正在请求 AI ({model}) 分析截图内容...")
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个网页自动化调试专家。请分析这张屏幕截图，判断为什么爬虫没有找到商品列表。"
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请看这张截图。页面上发生了什么？\n1. 是否有验证码（滑块、文字点选）？\n2. 是否有登录框？\n3. 是否显示'无搜索结果'？\n请简短总结原因。"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            # 很多时候是因为模型不支持视觉，或者 API 格式不同
            return f"视觉分析尝试失败 (可能是模型不支持视觉功能): {str(e)[:100]}..."
