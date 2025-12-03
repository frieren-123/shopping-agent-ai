import json
import os

class ContextManager:
    def __init__(self, profile_path="src/context/user_profile.json"):
        # 确保路径是绝对路径或相对于工作区的正确路径
        if not os.path.isabs(profile_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.profile_path = os.path.join(base_dir, profile_path)
        else:
            self.profile_path = profile_path
            
        self.profile = self._load_profile()

    def _load_profile(self):
        if not os.path.exists(self.profile_path):
            # 默认配置
            return {
                "shopping_constitution": [],
                "blacklisted_keywords": [],
                "preferred_ingredients": [],
                "disliked_ingredients": []
            }
        try:
            with open(self.profile_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ 加载用户配置文件失败: {e}")
            return {}

    def get_critical_thinking_prompt(self):
        """
        生成基于用户购物宪法的 Prompt 片段。
        这是 MineContext 理念的核心：主动注入用户上下文。
        """
        constitution = self.profile.get("shopping_constitution", [])
        blacklist = self.profile.get("blacklisted_keywords", [])
        disliked = self.profile.get("disliked_ingredients", [])
        
        prompt = "\n\n=== 🛡️ 用户核心购物宪法 (User Context) ===\n"
        prompt += "⚠️ 重要指令：你必须优先遵循以下用户设定的原则，这比通用标准更重要：\n"
        
        for rule in constitution:
            prompt += f"- [原则] {rule}\n"
            
        if blacklist:
            prompt += f"\n- [黑名单关键词] 如商品包含以下词汇，直接降级: {', '.join(blacklist)}"
            
        if disliked:
            prompt += f"\n- [成分避雷] 用户反感以下成分，发现请高亮警告: {', '.join(disliked)}"
            
        prompt += "\n==========================================\n"
            
        return prompt
