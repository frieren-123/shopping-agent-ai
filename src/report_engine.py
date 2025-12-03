import os
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

class ReportEngine:
    """
    报告生成引擎 (参考 BettaFish 的 ReportEngine)
    负责将结构化数据渲染为 CLI 视图或 HTML 报告
    """
    
    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def print_cli_summary(self, products):
        """在终端打印漂亮的表格"""
        if not products:
            console.print("[bold red]❌ 没有商品数据可显示[/bold red]")
            return

        table = Table(title=f"🔍 搜索结果概览 (Top {len(products)})", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim", width=8)
        table.add_column("商品标题", width=40)
        table.add_column("价格", justify="right", style="green")
        table.add_column("店铺", style="cyan")
        table.add_column("平台", style="yellow")
        table.add_column("评分", justify="right")

        for p in products:
            # 兼容 dict 或 Product 对象
            if hasattr(p, 'dict'):
                p_dict = p.dict()
            else:
                p_dict = p
                
            table.add_row(
                str(p_dict.get('id', ''))[:8],
                p_dict.get('title', '')[:38] + "...",
                f"¥{p_dict.get('price', 0)}",
                p_dict.get('shop', ''),
                p_dict.get('platform', ''),
                f"{p_dict.get('smart_score', 0):.1f}"
            )
        
        console.print(table)

    def generate_html_report(self, products, llm_analysis, filename="shopping_report.html"):
        """生成包含图表和分析的 HTML 报告"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 简单的 HTML 模板
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI 购物分析报告 - {timestamp}</title>
            <style>
                body {{ font-family: sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }}
                .header {{ text-align: center; border-bottom: 2px solid #eee; padding-bottom: 20px; }}
                .analysis {{ background: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .score {{ font-weight: bold; color: #e67e22; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🛒 AI 购物决策报告</h1>
                <p>生成时间: {timestamp}</p>
            </div>

            <div class="analysis">
                <h2>🧠 AI 深度点评</h2>
                <div>{llm_analysis.replace(chr(10), '<br>')}</div>
            </div>

            <h2>📊 商品详细对比</h2>
            <table>
                <thead>
                    <tr>
                        <th>商品</th>
                        <th>价格</th>
                        <th>店铺</th>
                        <th>平台</th>
                        <th>智能评分</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for p in products:
            if hasattr(p, 'dict'): p = p.dict()
            html += f"""
                <tr>
                    <td><a href="{p.get('link', '#')}" target="_blank">{p.get('title', '')}</a></td>
                    <td>¥{p.get('price', 0)}</td>
                    <td>{p.get('shop', '')}</td>
                    <td>{p.get('platform', '')}</td>
                    <td class="score">{p.get('smart_score', 0):.1f}</td>
                </tr>
            """
            
        html += """
                </tbody>
            </table>
        </body>
        </html>
        """
        
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
            
        console.print(f"[bold green]✅ 报告已生成: {filepath}[/bold green]")
        return filepath
