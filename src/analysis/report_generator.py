"""
报告生成器 - 生成聊天记录分析的可视化报告

将分析结果转换为易于理解的报告格式，包括图表和统计信息
"""
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Dict, List, Any
from loguru import logger
import matplotlib
matplotlib.use('Agg')  # 使用非GUI后端
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']  # 支持中文显示
plt.rcParams['axes.unicode_minus'] = False  # 正常显示负号


class ReportGenerator:
    """
    报告生成器
    生成聊天记录分析的详细报告，包括数据统计和可视化图表
    """
    
    def __init__(self):
        self.output_dir = "analysis_reports"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_single_report(self, analysis_result: Dict, output_path: str = None) -> str:
        """
        生成单个聊天记录的分析报告
        
        Args:
            analysis_result: 单个聊天记录的分析结果
            output_path: 输出路径
            
        Returns:
            str: 生成的报告路径
        """
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"single_analysis_report_{timestamp}.html"
            output_path = os.path.join(self.output_dir, filename)
        
        # 准备报告数据
        report_data = {
            'file_path': analysis_result.get('file_path', 'Unknown'),
            'total_messages': analysis_result.get('total_messages', 0),
            'user_messages': analysis_result.get('user_messages', 0),
            'bargain_info': analysis_result.get('bargain_info', {}),
            'deal_info': analysis_result.get('deal_info', {}),
            'price_info': analysis_result.get('price_info', {}),
            'shipping_info': analysis_result.get('shipping_info', {}),
            'profit_impact_score': analysis_result.get('profit_impact_score', 0),
            'conversion_likelihood': analysis_result.get('conversion_likelihood', 0)
        }
        
        # 生成HTML报告
        html_content = self._generate_single_html_report(report_data)
        
        # 保存报告
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"单个分析报告已保存到: {output_path}")
        return output_path
    
    def _generate_single_html_report(self, report_data: Dict) -> str:
        """
        生成单个报告的HTML内容
        
        Args:
            report_data: 报告数据
            
        Returns:
            str: HTML内容
        """
        bargain_info = report_data['bargain_info']
        deal_info = report_data['deal_info']
        price_info = report_data['price_info']
        shipping_info = report_data['shipping_info']
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>聊天记录分析报告 - {os.path.basename(report_data['file_path'])}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; text-align: center; }}
        h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .summary-box {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #fff; border: 1px solid #ddd; border-radius: 5px; min-width: 200px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #e74c3c; }}
        .metric-label {{ font-size: 14px; color: #7f8c8d; }}
        .positive {{ color: #27ae60; }}
        .negative {{ color: #e74c3c; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .recommendation {{ background-color: #d5f4e6; padding: 10px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #3498db; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>闲鱼聊天记录分析报告</h1>
        <p><strong>分析文件:</strong> {report_data['file_path']}</p>
        <p><strong>分析时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>📊 概要统计</h2>
        <div class="summary-box">
            <div class="metric">
                <div class="metric-value">{report_data['total_messages']}</div>
                <div class="metric-label">总消息数</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report_data['user_messages']}</div>
                <div class="metric-label">用户消息数</div>
            </div>
            <div class="metric">
                <div class="metric-value {self._get_score_color(report_data['profit_impact_score'])}">{report_data['profit_impact_score']:.1f}</div>
                <div class="metric-label">利润影响评分</div>
            </div>
            <div class="metric">
                <div class="metric-value {self._get_score_color(report_data['conversion_likelihood']*100)}">{report_data['conversion_likelihood']:.1f}</div>
                <div class="metric-label">转化可能性</div>
            </div>
        </div>
        
        <h2>💸 砍价分析</h2>
        <table>
            <tr>
                <th>指标</th>
                <th>数值</th>
                <th>说明</th>
            </tr>
            <tr>
                <td>总砍价次数</td>
                <td>{bargain_info.get('total_bargain_count', 0)}</td>
                <td>用户提出砍价的总次数</td>
            </tr>
            <tr>
                <td>每轮平均砍价</td>
                <td>{bargain_info.get('avg_bargain_per_conversation', 0):.2f}</td>
                <td>平均每轮对话的砍价次数</td>
            </tr>
        </table>
        
        <h2>💰 成交分析</h2>
        <table>
            <tr>
                <th>指标</th>
                <th>数值</th>
                <th>说明</th>
            </tr>
            <tr>
                <td>检测到成交</td>
                <td>{'是' if deal_info.get('deal_detected', False) else '否'}</td>
                <td>是否检测到成交相关关键词</td>
            </tr>
            <tr>
                <td>成交置信度</td>
                <td>{deal_info.get('deal_confidence', 0):.2f}</td>
                <td>成交的可信度评分</td>
            </tr>
            <tr>
                <td>交易状态</td>
                <td>{deal_info.get('transaction_status', 'N/A')}</td>
                <td>当前交易状态</td>
            </tr>
        </table>
        
        <h2>🏷️ 价格分析</h2>
        <table>
            <tr>
                <th>指标</th>
                <th>数值</th>
                <th>说明</th>
            </tr>
            <tr>
                <td>原价</td>
                <td>{price_info.get('original_price', 'N/A')}</td>
                <td>商品标价</td>
            </tr>
            <tr>
                <td>成交价</td>
                <td>{price_info.get('final_price', 'N/A')}</td>
                <td>最终成交价格</td>
            </tr>
            <tr>
                <td>折扣率</td>
                <td>{price_info.get('discount_rate', 0):.2%}</td>
                <td>相对原价的折扣比例</td>
            </tr>
            <tr>
                <td>价格协商次数</td>
                <td>{price_info.get('price_negotiation_count', 0)}</td>
                <td>价格相关讨论的次数</td>
            </tr>
        </table>
        
        <h2>📦 物流分析</h2>
        <table>
            <tr>
                <th>指标</th>
                <th>数值</th>
                <th>说明</th>
            </tr>
            <tr>
                <td>讨论物流</td>
                <td>{'是' if shipping_info.get('shipping_discussed', False) else '否'}</td>
                <td>是否讨论过物流相关事宜</td>
            </tr>
            <tr>
                <td>物流费用</td>
                <td>{shipping_info.get('shipping_cost', 'N/A')}</td>
                <td>涉及的物流费用</td>
            </tr>
            <tr>
                <td>物流方式</td>
                <td>{shipping_info.get('shipping_method', 'N/A')}</td>
                <td>使用的物流方式</td>
            </tr>
        </table>
    </div>
</body>
</html>
        """
        
        return html
    
    def generate_batch_report(self, analysis_results: List[Dict], output_path: str = None) -> str:
        """
        生成批量分析的综合报告
        
        Args:
            analysis_results: 多个聊天记录的分析结果
            output_path: 输出路径
            
        Returns:
            str: 生成的报告路径
        """
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"batch_analysis_report_{timestamp}.html"
            output_path = os.path.join(self.output_dir, filename)
        
        # 准备汇总数据
        total_files = len(analysis_results)
        if total_files == 0:
            logger.warning("没有分析结果，无法生成批量报告")
            return ""
        
        # 计算汇总统计
        total_messages = sum(result.get('total_messages', 0) for result in analysis_results)
        total_user_messages = sum(result.get('user_messages', 0) for result in analysis_results)
        avg_profit_impact = sum(result.get('profit_impact_score', 0) for result in analysis_results) / total_files if total_files > 0 else 0
        avg_conversion_rate = sum(result.get('conversion_likelihood', 0) for result in analysis_results) / total_files if total_files > 0 else 0
        
        # 统计成交情况
        deal_detected_count = sum(1 for result in analysis_results if result.get('deal_info', {}).get('deal_detected', False))
        
        # 统计砍价情况
        total_bargain_count = sum(
            result.get('bargain_info', {}).get('total_bargain_count', 0) 
            for result in analysis_results
        )
        
        # 准备报告数据
        report_data = {
            'total_files': total_files,
            'total_messages': total_messages,
            'total_user_messages': total_user_messages,
            'avg_profit_impact': avg_profit_impact,
            'avg_conversion_rate': avg_conversion_rate,
            'deal_success_rate': deal_detected_count / total_files if total_files > 0 else 0,
            'total_bargain_count': total_bargain_count,
            'deal_detected_count': deal_detected_count
        }
        
        # 生成HTML报告
        html_content = self._generate_batch_html_report(report_data, analysis_results)
        
        # 保存报告
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"批量分析报告已保存到: {output_path}")
        return output_path
    
    def _generate_batch_html_report(self, report_data: Dict, analysis_results: List[Dict]) -> str:
        """
        生成批量报告的HTML内容
        
        Args:
            report_data: 汇总报告数据
            analysis_results: 所有分析结果
            
        Returns:
            str: HTML内容
        """
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>批量聊天记录分析报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; text-align: center; }}
        h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .summary-box {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #fff; border: 1px solid #ddd; border-radius: 5px; min-width: 200px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #e74c3c; }}
        .metric-label {{ font-size: 14px; color: #7f8c8d; }}
        .positive {{ color: #27ae60; }}
        .negative {{ color: #e74c3c; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .recommendation {{ background-color: #d5f4e6; padding: 10px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #3498db; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>批量闲鱼聊天记录分析报告</h1>
        <p><strong>分析时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>分析文件数:</strong> {report_data['total_files']} 个</p>
        
        <h2>📈 总体统计</h2>
        <div class="summary-box">
            <div class="metric">
                <div class="metric-value">{report_data['total_files']}</div>
                <div class="metric-label">分析文件数</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report_data['total_messages']}</div>
                <div class="metric-label">总消息数</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report_data['total_user_messages']}</div>
                <div class="metric-label">用户消息数</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report_data['total_bargain_count']}</div>
                <div class="metric-label">总砍价次数</div>
            </div>
        </div>
        
        <h2>💰 核心指标</h2>
        <div class="summary-box">
            <div class="metric">
                <div class="metric-value {self._get_score_color(report_data['avg_profit_impact'])}">{report_data['avg_profit_impact']:.1f}</div>
                <div class="metric-label">平均利润影响评分</div>
            </div>
            <div class="metric">
                <div class="metric-value {self._get_score_color(report_data['avg_conversion_rate']*100)}">{report_data['avg_conversion_rate']:.2f}</div>
                <div class="metric-label">平均转化可能性</div>
            </div>
            <div class="metric">
                <div class="metric-value {self._get_rate_color(report_data['deal_success_rate'])}">{report_data['deal_success_rate']:.2%}</div>
                <div class="metric-label">成交成功率</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report_data['deal_detected_count']}/{report_data['total_files']}</div>
                <div class="metric-label">成交/总文件</div>
            </div>
        </div>
        
        <h2>📋 详细分析</h2>
        <table>
            <tr>
                <th>文件名</th>
                <th>总消息</th>
                <th>砍价次数</th>
                <th>是否成交</th>
                <th>利润评分</th>
                <th>转化可能性</th>
            </tr>
        """
        
        # 添加每个文件的详细信息
        for result in analysis_results:
            file_path = result.get('file_path', 'Unknown')
            filename = os.path.basename(file_path)
            bargain_count = result.get('bargain_info', {}).get('total_bargain_count', 0)
            deal_detected = '是' if result.get('deal_info', {}).get('deal_detected', False) else '否'
            profit_score = result.get('profit_impact_score', 0)
            conversion_rate = result.get('conversion_likelihood', 0)
            
            html += f"""
            <tr>
                <td>{filename}</td>
                <td>{result.get('total_messages', 0)}</td>
                <td>{bargain_count}</td>
                <td>{deal_detected}</td>
                <td>{profit_score:.1f}</td>
                <td>{conversion_rate:.2f}</td>
            </tr>
            """
        
        html += """
        </table>
        
        <h2>💡 优化建议</h2>
        <div class="recommendation">
            <strong>利润优化:</strong> 
            当前平均利润影响评分为 {report_data['avg_profit_impact']:.1f} 分。
            {f'评分较低，建议重点关注定价策略和砍价处理' if report_data['avg_profit_impact'] < 60 else '评分为中等，有优化空间' if report_data['avg_profit_impact'] < 80 else '评分良好，继续保持'}
        </div>
        
        <div class="recommendation">
            <strong>转化提升:</strong> 
            当前平均转化可能性为 {report_data['avg_conversion_rate']:.1f}，成交成功率为 {report_data['deal_success_rate']:.1%}。
            {f'转化率较低，建议优化回复话术和成交促进策略' if report_data['avg_conversion_rate'] < 0.4 else '转化率为中等，可进一步提升' if report_data['avg_conversion_rate'] < 0.7 else '转化率较高，策略有效'}
        </div>
        
        <div class="recommendation">
            <strong>砍价处理:</strong> 
            总砍价次数为 {report_data['total_bargain_count']} 次，平均每个文件砍价 {report_data['total_bargain_count']/report_data['total_files']:.1f} 次。
            {f'砍价次数较多，建议优化砍价应对策略' if report_data['total_bargain_count'] > report_data['total_files'] * 2 else '砍价次数适中，处理得当'}
        </div>
    </div>
</body>
</html>
        """.format(
            avg_profit_impact=report_data['avg_profit_impact'],
            avg_conversion_rate=report_data['avg_conversion_rate'],
            deal_success_rate=report_data['deal_success_rate'],
            total_bargain_count=report_data['total_bargain_count'],
            total_files=report_data['total_files']
        )
        
        return html
    
    def _get_score_color(self, score: float) -> str:
        """
        根据分数获取颜色类
        """
        if score >= 70:
            return "positive"
        elif score >= 40:
            return ""
        else:
            return "negative"
    
    def _get_rate_color(self, rate: float) -> str:
        """
        根据比率获取颜色类
        """
        if rate >= 0.7:
            return "positive"
        elif rate >= 0.3:
            return ""
        else:
            return "negative"


if __name__ == "__main__":
    generator = ReportGenerator()
    print("报告生成器已初始化")