from abc import ABC, abstractmethod
from typing import List
from src.models.product import Product

class BaseScraper(ABC):
    """
    爬虫基类 (参考 Plugin 架构)
    所有具体的平台爬虫都必须继承此类并实现 search 方法。
    """
    
    @abstractmethod
    def search(self, keyword: str, max_pages: int = 1) -> List[Product]:
        """
        执行搜索
        :param keyword: 搜索关键词
        :param max_pages: 最大页数
        :return: Product 对象列表
        """
        pass

    def normalize_product(self, raw_data: dict, platform: str) -> Product:
        """
        将原始字典数据转换为标准 Product 模型
        """
        # 处理价格
        try:
            price_str = str(raw_data.get('price', '0')).replace('¥', '').replace('￥', '').replace(',', '')
            price = float(price_str)
        except:
            price = 0.0

        return Product(
            id=str(raw_data.get('id', '')),
            title=raw_data.get('title', '未知商品'),
            price=price,
            shop=raw_data.get('shop', '未知店铺'),
            platform=platform,
            link=raw_data.get('link', ''),
            deal_count=str(raw_data.get('deal_count', '0'))
        )

    @abstractmethod
    def get_details(self, *args, **kwargs):
        """
        获取项目的详细信息
        """
        pass

