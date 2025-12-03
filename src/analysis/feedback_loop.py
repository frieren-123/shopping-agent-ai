import json
import os
from src.llm_analyzer import get_llm_client
from src.context.context_manager import ContextManager

class FeedbackOptimizer:
    def __init__(self):
        self.ctx_mgr = ContextManager()
        self.client = get_llm_client()

    def optimize(self, user_feedback):
        """
        Agent Lightning 理念：通过反馈优化 Agent 的行为策略 (Profile)。
        """
        print("⚡ [Agent Lightning] 正在根据您的反馈优化 Agent 记忆...")
        
        current_profile = self.ctx_mgr.profile
        
        prompt = f"""
        你是一个 Agent 优化师。你的目标是根据用户的反馈，更新用户的“购物偏好配置文件”。
        
        === 当前配置文件 ===
        {json.dumps(current_profile, ensure_ascii=False, indent=2)}
        
        === 用户反馈 ===
        "{user_feedback}"
        
        === 任务 ===
        请分析用户的反馈，判断需要对配置文件做哪些修改。
        你可以：
        1. 添加新的购物原则到 "shopping_constitution" (例如用户说"太贵了"，可以添加"优先考虑性价比"或具体的预算限制)。
        2. 添加关键词到 "blacklisted_keywords" (例如用户说"不要某品牌")。
        3. 添加成分到 "disliked_ingredients" (例如用户说"过敏")。
        4. 添加成分到 "preferred_ingredients"。
        
        请返回一个 JSON 对象，包含需要**新增**或**修改**的字段。不要返回整个文件，只返回变更部分。
        例如：
        {{
            "shopping_constitution": ["新增的原则..."],
            "blacklisted_keywords": ["新增的黑名单词"]
        }}
        如果不需要修改，返回 {{}}。
        """
        
        try:
            model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个负责优化 AI 行为配置的专家。只输出 JSON。"},
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "")
            
            updates = json.loads(content)
            
            if not updates:
                print("   ℹ️ 反馈未触发配置更新。")
                return

            # 应用更新
            changed = False
            for key, new_items in updates.items():
                if key in current_profile and isinstance(new_items, list):
                    # 简单的去重添加
                    original_set = set(current_profile[key])
                    for item in new_items:
                        if item not in original_set:
                            current_profile[key].append(item)
                            print(f"   ✅ [{key}] 新增规则: {item}")
                            changed = True
            
            if changed:
                # 保存回文件
                with open(self.ctx_mgr.profile_path, 'w', encoding='utf-8') as f:
                    json.dump(current_profile, f, ensure_ascii=False, indent=2)
                print("   💾 用户画像已更新！下次搜索将更懂你。")
            else:
                print("   ℹ️ 没有产生实质性的规则变更。")
                
        except Exception as e:
            print(f"   ⚠️ 优化失败: {e}")
