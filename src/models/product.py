from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List

class Product(BaseModel):
    """
    标准商品数据模型 (参考 Nocobase 的数据驱动设计)
    """
    id: str = Field(..., description="商品唯一ID")
    title: str = Field(..., description="商品标题")
    price: float = Field(..., description="商品价格")
    original_price: Optional[float] = Field(None, description="原价")
    shop: str = Field("未知店铺", description="店铺名称")
    platform: str = Field(..., description="来源平台 (JD, Taobao, Vip)")
    link: str = Field(..., description="商品链接")
    image_url: Optional[str] = Field(None, description="商品图片链接")
    deal_count: str = Field("0", description="销量/热度描述")
    
    # 评分字段
    smart_score: float = Field(0.0, description="智能评分")
    
    # 详细信息 (可选)
    specs: dict = Field(default_factory=dict, description="规格参数")
    reviews: List[str] = Field(default_factory=list, description="精选评论")

    class Config:
        # 允许从 dict 中多余的字段初始化而不报错
        extra = "ignore"

    def get(self, key, default=None):
        """兼容字典的 .get() 方法"""
        return getattr(self, key, default)

    def __getitem__(self, key):
        """兼容字典的 [] 访问"""
        return getattr(self, key)

    def __setitem__(self, key, value):
        """兼容字典的 [] 赋值"""
        setattr(self, key, value)


