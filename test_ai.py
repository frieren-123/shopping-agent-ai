from src.scrapers.jd_crawl4ai import JDCrawl4AIScraper
import asyncio

if __name__ == "__main__":
    scraper = JDCrawl4AIScraper()
    print("🤖 正在测试 Crawl4AI 抓取...")
    # 搜索 "机械键盘"，只抓 1 页测试
    results = scraper.search_sync("机械键盘", max_pages=1)
    
    print(f"\n🎉 抓取结果: {len(results)} 个")
    for item in results[:5]:
        print(f"- {item.get('title', '无标题')} (¥{item.get('price', '未知')})")
