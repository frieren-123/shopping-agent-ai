import math

class SmartScorer:
    def __init__(self, products):
        self.products = products
        self.stats = self._calculate_global_stats()

    def _parse_price(self, price_str):
        if isinstance(price_str, (int, float)):
            return float(price_str)
        try:
            # 移除常见货币符号和千分位
            clean_str = str(price_str).replace('¥', '').replace('￥', '').replace(',', '').strip()
            return float(clean_str)
        except:
            return 0.0

    def _parse_sales(self, sales_str):
        if isinstance(sales_str, (int, float)):
            return float(sales_str)
        try:
            # 处理京东的 "2000+条评价" 或 "20万+"
            s = str(sales_str).replace('条评价', '').replace('人付款', '').replace('+', '').strip()
            if '万' in s:
                return float(s.replace('万', '')) * 10000
            return float(s)
        except:
            return 0.0


    def _calculate_global_stats(self):
        prices = [self._parse_price(p.get('price', '0')) for p in self.products]
        sales = [self._parse_sales(p.get('deal_count', '0')) for p in self.products]
        
        # Filter out zeros for meaningful stats
        valid_prices = [p for p in prices if p > 0]
        
        if not valid_prices:
            return {"avg_price": 0, "std_price": 1, "avg_sales": 0}

        avg_price = sum(valid_prices) / len(valid_prices)
        
        # Standard Deviation for Price
        variance = sum((x - avg_price) ** 2 for x in valid_prices) / len(valid_prices)
        std_price = math.sqrt(variance) if variance > 0 else 1.0
        
        avg_sales = sum(sales) / len(sales) if sales else 0
        
        return {
            "avg_price": avg_price,
            "std_price": std_price,
            "avg_sales": avg_sales
        }

    def calculate_score(self, product):
        """
        Calculate a composite score based on Price Z-Score, Sales Volume, and Shop Quality.
        Score = w1 * PriceScore + w2 * SalesScore + w3 * ShopScore + w4 * Relevance
        """
        price = self._parse_price(product.get('price', '0'))
        sales = self._parse_sales(product.get('deal_count', '0'))
        shop_name = product.get('shop', '')
        title = product.get('title', '')
        
        # 1. Price Score (Modified Z-Score)
        # We prefer "Value for Money": slightly below average is better than exactly average.
        # Shift the target mean to 0.8 * avg_price
        target_price = self.stats['avg_price'] * 0.8
        if self.stats['std_price'] > 0:
            z_score = (price - target_price) / self.stats['std_price']
        else:
            z_score = 0
            
        # Gaussian scoring: Peak at target_price
        # Penalize extremely low prices (potential fake/accessories) more than high prices
        if price < self.stats['avg_price'] * 0.2: # Too cheap (e.g. accessory)
            price_score = 20
        else:
            price_score = math.exp(-(z_score ** 2) / 2) * 100
        
        # 2. Sales Score (Logarithmic scale)
        if self.stats['avg_sales'] > 0:
            sales_ratio = sales / self.stats['avg_sales']
            sales_score = min(sales_ratio, 3.0) * 33 # Cap at 3x average, max 100
        else:
            sales_score = 0

        # 3. Shop Quality Score (New)
        shop_score = 50 # Base score
        if '自营' in shop_name:
            shop_score += 50 # Huge bonus for self-operated
        elif '旗舰' in shop_name:
            shop_score += 30 # Bonus for flagship
        elif '专营' in shop_name:
            shop_score += 10

        # 4. Title Relevance (Simple keyword density)
        relevance_score = 100 if len(title) > 10 else 50

        # Weighted Sum
        # Price: 30%, Sales: 30%, Shop: 25%, Relevance: 15%
        final_score = (0.30 * price_score) + (0.30 * sales_score) + (0.25 * shop_score) + (0.15 * relevance_score)
        
        return round(final_score, 2)

    def rank_products(self):
        for p in self.products:
            p['smart_score'] = self.calculate_score(p)
        
        # Sort by score descending
        return sorted(self.products, key=lambda x: x['smart_score'], reverse=True)
