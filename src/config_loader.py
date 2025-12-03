import yaml
import os

def load_config():
    config_path = "config/config.yaml"
    if not os.path.exists(config_path):
        # 默认配置
        return {
            "crawler": {"max_pages": 3},
            "filter": {"top_n": 5}
        }
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

CONFIG = load_config()
