"""
交易分析器 - 分析交易数据，提取影响利润的因素
"""

import json
import os
import time
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime
from collections import defaultdict
from core.context_manager import ChatContextManager

class TradingAnalyzer:
    """交易数据分析器"""

    def __init__(self, context_manager: ChatContextManager = None):
        self.context_manager = context_manager or ChatContextManager()
        self.bargain_patterns = {
            'aggressive': ['最少', '不能再少了', '就这个价', '底价', '最低'],
            'moderate': ['便宜点', '少点', '优惠', '便宜', '再少'],
            'polite': ['可以便宜', '能便宜', '便宜些', '给个优惠', '优惠点']
        }

    def analyze_bargain_behavior(self) -> Dict:
        """分析议价行为模式"""
        all_chats = self.context_manager.get_all_chats()
        
        analysis = {
            'total_chats': len(all_chats),
            'bargain_chats': 0,
            'completed_deals': 0,
            'bargain_patterns': defaultdict(int),
            'price_negotiation_stats': {
                'total_negotiations': 0,
                'successful_negotiations': 0,
                'avg_discount_rate': 0,
                'total_discount_amount': 0
            },
            'shipping_impact': {
                'free_shipping_deals': 0,
                'paid_shipping_deals': 0
            }
        }
        
        total_discount = 0
        discount_count = 0
        
        for chat in all_chats:
            # 检查是否有议价行为
            if chat.get('bargain_count', 0) > 0:
                analysis['bargain_chats'] += 1
                
                # 分析议价历史
                bargain_history = chat.get('bargain_history', [])
                analysis['price_negotiation_stats']['total_negotiations'] += len(bargain_history)
                
                for event in bargain_history:
                    if 'original_price' in event and 'counter_price' in event:
                        original = event['original_price']
                        counter = event['counter_price']
                        discount = original - counter
                        if discount > 0:
                            analysis['price_negotiation_stats']['successful_negotiations'] += 1
                            total_discount += discount
                            discount_count += 1
            
            # 检查交易状态
            if chat.get('deal_status') == 'completed':
                analysis['completed_deals'] += 1
                
                # 检查包邮情况
                if chat.get('is_free_shipping', False):
                    analysis['shipping_impact']['free_shipping_deals'] += 1
                else:
                    analysis['shipping_impact']['paid_shipping_deals'] += 1
        
        # 计算平均折扣率
        if discount_count > 0:
            analysis['price_negotiation_stats']['avg_discount_rate'] = (
                (total_discount / discount_count) if discount_count > 0 else 0
            )
            analysis['price_negotiation_stats']['total_discount_amount'] = total_discount
        
        return analysis

    def analyze_profit_impact_factors(self) -> Dict:
        """分析影响利润的因素"""
        all_chats = self.context_manager.get_all_chats()
        
        factors = {
            'bargaining_impact': self._analyze_bargaining_impact(all_chats),
            'shipping_impact': self._analyze_shipping_impact(all_chats),
            'timing_impact': self._analyze_timing_impact(all_chats),
            'product_condition_impact': self._analyze_product_condition_impact(all_chats),
            'message_response_analysis': self._analyze_message_response(all_chats)
        }
        
        return factors

    def _analyze_bargaining_impact(self, chats: List[Dict]) -> Dict:
        """分析议价对成交的影响"""
        bargain_success = 0  # 有议价且成交
        bargain_fail = 0     # 有议价但未成交
        no_bargain_success = 0  # 无议价且成交
        no_bargain_fail = 0     # 无议价且未成交
        
        total_discount = 0
        discount_count = 0
        
        for chat in chats:
            has_bargain = chat.get('bargain_count', 0) > 0
            is_completed = chat.get('deal_status') == 'completed'
            original_price = chat.get('original_price')
            final_price = chat.get('final_price')
            
            if has_bargain and is_completed:
                bargain_success += 1
                if original_price and final_price:
                    total_discount += (original_price - final_price)
                    discount_count += 1
            elif has_bargain and not is_completed:
                bargain_fail += 1
            elif not has_bargain and is_completed:
                no_bargain_success += 1
            elif not has_bargain and not is_completed:
                no_bargain_fail += 1
        
        avg_discount_with_bargain = (total_discount / discount_count) if discount_count > 0 else 0
        
        return {
            'bargain_success_rate': bargain_success / (bargain_success + bargain_fail) if (bargain_success + bargain_fail) > 0 else 0,
            'no_bargain_success_rate': no_bargain_success / (no_bargain_success + no_bargain_fail) if (no_bargain_success + no_bargain_fail) > 0 else 0,
            'avg_discount_with_bargain': avg_discount_with_bargain,
            'bargain_vs_no_bargain_success': {
                'bargain_success': bargain_success,
                'bargain_fail': bargain_fail,
                'no_bargain_success': no_bargain_success,
                'no_bargain_fail': no_bargain_fail
            }
        }

    def _analyze_shipping_impact(self, chats: List[Dict]) -> Dict:
        """分析邮费对成交的影响"""
        free_shipping_success = 0
        free_shipping_fail = 0
        paid_shipping_success = 0
        paid_shipping_fail = 0
        
        for chat in chats:
            is_free_shipping = chat.get('is_free_shipping', False)
            is_completed = chat.get('deal_status') == 'completed'
            
            if is_free_shipping and is_completed:
                free_shipping_success += 1
            elif is_free_shipping and not is_completed:
                free_shipping_fail += 1
            elif not is_free_shipping and is_completed:
                paid_shipping_success += 1
            elif not is_free_shipping and not is_completed:
                paid_shipping_fail += 1
        
        return {
            'free_shipping_success_rate': free_shipping_success / (free_shipping_success + free_shipping_fail) if (free_shipping_success + free_shipping_fail) > 0 else 0,
            'paid_shipping_success_rate': paid_shipping_success / (paid_shipping_success + paid_shipping_fail) if (paid_shipping_success + paid_shipping_fail) > 0 else 0,
            'shipping_impact': {
                'free_shipping_success': free_shipping_success,
                'free_shipping_fail': free_shipping_fail,
                'paid_shipping_success': paid_shipping_success,
                'paid_shipping_fail': paid_shipping_fail
            }
        }

    def _analyze_timing_impact(self, chats: List[Dict]) -> Dict:
        """分析时间因素对成交的影响"""
        # 分析会话时长对成交的影响
        short_duration_success = 0  # 短时间成交
        short_duration_fail = 0     # 短时间未成交
        long_duration_success = 0   # 长时间成交
        long_duration_fail = 0      # 长时间未成交
        
        # 设置时间阈值（比如30分钟）
        duration_threshold = 1800  # 30分钟的秒数
        
        for chat in chats:
            messages = chat.get('messages', [])
            if len(messages) >= 2:
                start_time = messages[0]['timestamp']
                end_time = messages[-1]['timestamp']
                duration = end_time - start_time
                
                is_completed = chat.get('deal_status') == 'completed'
                
                if duration <= duration_threshold:
                    if is_completed:
                        short_duration_success += 1
                    else:
                        short_duration_fail += 1
                else:
                    if is_completed:
                        long_duration_success += 1
                    else:
                        long_duration_fail += 1
        
        return {
            'short_duration_success_rate': short_duration_success / (short_duration_success + short_duration_fail) if (short_duration_success + short_duration_fail) > 0 else 0,
            'long_duration_success_rate': long_duration_success / (long_duration_success + long_duration_fail) if (long_duration_success + long_duration_fail) > 0 else 0,
            'timing_analysis': {
                'short_duration_success': short_duration_success,
                'short_duration_fail': short_duration_fail,
                'long_duration_success': long_duration_success,
                'long_duration_fail': long_duration_fail
            }
        }

    def _analyze_product_condition_impact(self, chats: List[Dict]) -> Dict:
        """分析商品成色对价格的影响"""
        condition_premium = defaultdict(list)  # 不同成色对应的价格折扣
        
        for chat in chats:
            condition = chat.get('product_condition')
            original_price = chat.get('original_price')
            final_price = chat.get('final_price')
            
            if condition and original_price and final_price:
                discount_rate = (original_price - final_price) / original_price if original_price > 0 else 0
                condition_premium[condition].append(discount_rate)
        
        # 计算每种成色的平均折扣率
        avg_discount_by_condition = {}
        for condition, discounts in condition_premium.items():
            avg_discount_by_condition[condition] = sum(discounts) / len(discounts) if discounts else 0
        
        return {
            'avg_discount_by_condition': avg_discount_by_condition,
            'condition_count': {k: len(v) for k, v in condition_premium.items()}
        }

    def _analyze_message_response(self, chats: List[Dict]) -> Dict:
        """分析消息和响应对成交的影响"""
        # 统计每条聊天中的消息数量
        messages_per_chat_success = []
        messages_per_chat_fail = []
        
        for chat in chats:
            message_count = len(chat.get('messages', []))
            is_completed = chat.get('deal_status') == 'completed'
            
            if is_completed:
                messages_per_chat_success.append(message_count)
            else:
                messages_per_chat_fail.append(message_count)
        
        # 计算平均值
        avg_messages_success = sum(messages_per_chat_success) / len(messages_per_chat_success) if messages_per_chat_success else 0
        avg_messages_fail = sum(messages_per_chat_fail) / len(messages_per_chat_fail) if messages_per_chat_fail else 0
        
        return {
            'avg_messages_per_success': avg_messages_success,
            'avg_messages_per_fail': avg_messages_fail,
            'message_count_analysis': {
                'success_chat_message_counts': messages_per_chat_success,
                'fail_chat_message_counts': messages_per_chat_fail
            }
        }

    def generate_trading_report(self) -> Dict:
        """生成完整的交易分析报告"""
        bargain_analysis = self.analyze_bargain_behavior()
        profit_factors = self.analyze_profit_impact_factors()
        
        report = {
            'summary': {
                'total_chats': bargain_analysis['total_chats'],
                'bargain_rate': bargain_analysis['bargain_chats'] / bargain_analysis['total_chats'] if bargain_analysis['total_chats'] > 0 else 0,
                'completion_rate': bargain_analysis['completed_deals'] / bargain_analysis['total_chats'] if bargain_analysis['total_chats'] > 0 else 0,
                'avg_discount': bargain_analysis['price_negotiation_stats']['avg_discount_rate'],
                'free_shipping_rate': (bargain_analysis['shipping_impact']['free_shipping_deals'] / 
                                    (bargain_analysis['shipping_impact']['free_shipping_deals'] + 
                                     bargain_analysis['shipping_impact']['paid_shipping_deals'])) if 
                                    (bargain_analysis['shipping_impact']['free_shipping_deals'] + 
                                     bargain_analysis['shipping_impact']['paid_shipping_deals']) > 0 else 0
            },
            'bargaining_analysis': bargain_analysis,
            'profit_impact_factors': profit_factors,
            'recommendations': self._generate_recommendations(bargain_analysis, profit_factors)
        }
        
        return report

    def _generate_recommendations(self, bargain_analysis: Dict, profit_factors: Dict) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 议价相关建议
        bargaining_impact = profit_factors['bargaining_impact']
        if bargaining_impact['bargain_success_rate'] < bargaining_impact['no_bargain_success_rate']:
            recommendations.append("议价降低了成交率，建议优化议价回应策略")
        else:
            recommendations.append("议价对成交率影响较小，可继续当前策略")
        
        # 包邮相关建议
        shipping_impact = profit_factors['shipping_impact']
        if shipping_impact['free_shipping_success_rate'] > shipping_impact['paid_shipping_success_rate']:
            recommendations.append("包邮明显提高成交率，建议推广包邮策略")
        
        # 时间相关建议
        timing_impact = profit_factors['timing_impact']
        if timing_impact['short_duration_success_rate'] > timing_impact['long_duration_success_rate']:
            recommendations.append("快速响应提高成交率，建议优化响应速度")
        
        # 价格折扣建议
        avg_discount = bargain_analysis['price_negotiation_stats']['avg_discount_rate']
        if avg_discount > 20:  # 如果平均折扣超过20%
            recommendations.append(f"平均折扣{avg_discount:.2f}%较高，建议调整定价策略")
        
        return recommendations

    def export_analysis_to_json(self, filepath: str = None) -> str:
        """导出分析结果到JSON文件"""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"trading_analysis_report_{timestamp}.json"
        
        report = self.generate_trading_report()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"交易分析报告已导出到: {filepath}")
        return filepath

    def print_analysis_summary(self):
        """打印分析摘要"""
        report = self.generate_trading_report()
        summary = report['summary']
        
        print("=" * 60)
        print("交易数据分析摘要")
        print("=" * 60)
        print(f"总聊天数: {summary['total_chats']}")
        print(f"议价率: {summary['bargain_rate']:.2%}")
        print(f"成交率: {summary['completion_rate']:.2%}")
        print(f"平均折扣: {summary['avg_discount']:.2f}元")
        print(f"包邮率: {summary['free_shipping_rate']:.2%}")
        print("\n优化建议:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. {rec}")
        print("=" * 60)
