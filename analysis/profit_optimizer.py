"""
利润优化器 - 基于聊天记录分析结果提供优化建议

分析砍价、成交、价格和物流等因素对利润的影响，提供优化策略
"""
import os
import json
from typing import Dict, List, Tuple
from loguru import logger
from analysis.chat_analyzer import ChatAnalyzer


class ProfitOptimizer:
    """
    利润优化器
    基于聊天记录分析结果，提供提高成交率和利润率的策略建议
    """
    
    def __init__(self):
        self.optimizer_rules = {}
        self.strategy_templates = {}
        self.load_optimizer_rules()
        self.load_strategy_templates()
    
    def load_optimizer_rules(self):
        """
        加载利润优化规则
        """
        self.optimizer_rules = {
            # 砍价处理规则
            'bargain_handling': {
                'max_bargain_tolerance': 0.15,  # 最大可接受砍价幅度15%
                'bargain_count_threshold': 3,  # 超过3次砍价需要特殊处理
                'bargain_resistance_strategy': [
                    '强调产品价值而非价格',
                    '提供附加服务而非降价',
                    '限时优惠策略',
                    '捆绑销售策略'
                ]
            },
            # 成交促进规则
            'conversion_promotion': {
                'response_time_threshold': 60,  # 60秒内回复提高成交率
                'engagement_indicators': [
                    '多次询问产品细节',
                    '询问物流和售后',
                    '要求发送更多照片'
                ],
                'conversion_tactics': [
                    '紧迫感策略',
                    '社会证明策略',
                    '保证策略',
                    '小步骤策略'
                ]
            },
            # 价格优化规则
            'pricing_optimization': {
                'minimum_margin': 0.20,  # 最低利润率20%
                'dynamic_pricing_factors': [
                    '需求热度',
                    '库存情况',
                    '竞争状况',
                    '时间段'
                ],
                'price_adjustment_tips': [
                    '设置心理价位点',
                    '使用锚定效应',
                    '分层定价策略',
                    '增值包装策略'
                ]
            },
            # 物流优化规则
            'shipping_optimization': {
                'shipping_cost_threshold': 15,  # 超过15元运费需考虑包邮
                'shipping_method_preference': ['包邮', '到付', '平邮'],
                'shipping_promotion_strategies': [
                    '满额包邮',
                    '多件包邮',
                    '会员包邮',
                    '好评返现'
                ]
            }
        }
    
    def load_strategy_templates(self):
        """
        加载策略模板
        """
        self.strategy_templates = {
            # 砍价应对话术模板
            'bargain_response_templates': [
                "亲，这个价格已经是很优惠的了，质量有保证哦～",
                "亲，已经是最低价了，再少的话我就亏本啦～",
                "亲，价格确实不能再少了，但是可以给您多送点配件哦～",
                "感谢您的喜欢，这个价格已经是良心价了，性价比很高的～",
                "亲，要不您再看看其他的，价格真的不能再少了，质量您放心～"
            ],
            # 成交促进话术模板
            'conversion_promotion_templates': [
                "这款很受欢迎的，数量不多了，喜欢的话要抓紧哦～",
                "刚刚有个客户也看中了这款，您考虑好的话我可以先给您留着～",
                "现在下单的话，还可以给您多送一个小礼品哦～",
                "您是对这款产品很感兴趣吗？我可以给您详细介绍一下～",
                "您还有什么顾虑吗？我可以一一为您解答～"
            ],
            # 物流相关话术模板
            'shipping_templates': [
                "亲，支持包邮哦，下单后当天发货～",
                "亲，我们发的是顺丰快递，速度快有保障～",
                "亲，现在下单还可以享受包邮服务哦～",
                "亲，发货后预计2-3天就能收到啦～",
                "亲，收到货后有任何问题随时联系我哦～"
            ]
        }
    
    def optimize_bargain_strategy(self, analysis_result: Dict) -> Dict:
        """
        优化砍价策略
        
        Args:
            analysis_result: 聊天记录分析结果
            
        Returns:
            Dict: 砍价策略建议
        """
        bargain_info = analysis_result.get('bargain_info', {})
        price_info = analysis_result.get('price_info', {})
        
        strategy = {
            'strategy_type': 'bargain_optimization',
            'current_situation': f"砍价次数: {bargain_info.get('total_bargain_count', 0)}, " +
                                f"价格折扣: {price_info.get('discount_rate', 0):.2%}",
            'recommendations': [],
            'confidence': 0.5
        }
        
        # 根据砍价次数提供建议
        bargain_count = bargain_info.get('total_bargain_count', 0)
        discount_rate = price_info.get('discount_rate', 0)
        
        if bargain_count > self.optimizer_rules['bargain_handling']['bargain_count_threshold']:
            strategy['recommendations'].append({
                'type': 'high_bargain_frequency',
                'description': '检测到砍价频率较高，建议使用价值强调策略',
                'tactics': self.optimizer_rules['bargain_handling']['bargain_resistance_strategy'],
                'template': 'bargain_response_templates'
            })
        
        # 根据折扣率提供建议
        if discount_rate > self.optimizer_rules['bargain_handling']['max_bargain_tolerance']:
            strategy['recommendations'].append({
                'type': 'high_discount_request',
                'description': f'请求折扣过高({discount_rate:.2%})，建议坚持底线',
                'tactics': ['强调产品质量', '说明成本构成', '提供替代方案'],
                'template': 'bargain_response_templates'
            })
        
        # 计算置信度
        max_recommendations = len(self.optimizer_rules['bargain_handling']['bargain_resistance_strategy'])
        strategy['confidence'] = min(len(strategy['recommendations']) / max_recommendations if max_recommendations > 0 else 0, 1.0)
        
        return strategy
    
    def optimize_conversion_strategy(self, analysis_result: Dict) -> Dict:
        """
        优化成交策略
        
        Args:
            analysis_result: 聊天记录分析结果
            
        Returns:
            Dict: 成交策略建议
        """
        deal_info = analysis_result.get('deal_info', {})
        bargain_info = analysis_result.get('bargain_info', {})
        
        strategy = {
            'strategy_type': 'conversion_optimization',
            'current_situation': f"成交检测: {deal_info.get('deal_detected', False)}, " +
                                f"成交置信度: {deal_info.get('deal_confidence', 0):.2f}, " +
                                f"砍价次数: {bargain_info.get('total_bargain_count', 0)}",
            'recommendations': [],
            'confidence': 0.5
        }
        
        # 根据成交情况提供建议
        if not deal_info.get('deal_detected', False):
            # 未成交情况，提供促进成交的建议
            strategy['recommendations'].append({
                'type': 'conversion_promotion',
                'description': '客户未成交，建议使用成交促进策略',
                'tactics': self.optimizer_rules['conversion_promotion']['conversion_tactics'],
                'template': 'conversion_promotion_templates'
            })
        
        # 根据砍价次数判断客户购买意向
        bargain_count = bargain_info.get('total_bargain_count', 0)
        if 0 < bargain_count <= 2:
            # 适量砍价可能表示购买意向
            strategy['recommendations'].append({
                'type': 'purchase_intent_detected',
                'description': '检测到购买意向，建议加强成交推动',
                'tactics': ['提供更多产品信息', '强调优惠时效', '解决客户顾虑'],
                'template': 'conversion_promotion_templates'
            })
        elif bargain_count > 3:
            # 过多砍价可能表示犹豫
            strategy['recommendations'].append({
                'type': 'high_negotiation_detected',
                'description': '砍价过多可能表示不真诚，建议适当冷处理',
                'tactics': ['坚持价格底线', '强调产品价值', '适度冷处理'],
                'template': 'bargain_response_templates'
            })
        
        # 计算置信度
        strategy['confidence'] = deal_info.get('deal_confidence', 0)
        
        return strategy
    
    def optimize_pricing_strategy(self, analysis_result: Dict) -> Dict:
        """
        优化定价策略
        
        Args:
            analysis_result: 聊天记录分析结果
            
        Returns:
            Dict: 定价策略建议
        """
        price_info = analysis_result.get('price_info', {})
        deal_info = analysis_result.get('deal_info', {})
        
        strategy = {
            'strategy_type': 'pricing_optimization',
            'current_situation': f"原价: {price_info.get('original_price', 'N/A')}, " +
                                f"成交价: {price_info.get('final_price', 'N/A')}, " +
                                f"折扣率: {price_info.get('discount_rate', 0):.2%}, " +
                                f"是否成交: {deal_info.get('deal_detected', False)}",
            'recommendations': [],
            'confidence': 0.5
        }
        
        original_price = price_info.get('original_price')
        final_price = price_info.get('final_price')
        discount_rate = price_info.get('discount_rate', 0)
        
        if original_price and final_price:
            # 计算毛利率（假定成本为原价的60%）
            assumed_cost = original_price * 0.6
            profit_margin = (final_price - assumed_cost) / final_price if final_price > 0 else 0
            
            if profit_margin < self.optimizer_rules['pricing_optimization']['minimum_margin']:
                strategy['recommendations'].append({
                    'type': 'low_profit_margin',
                    'description': f'利润率过低({profit_margin:.2%})，建议调整定价策略',
                    'tactics': self.optimizer_rules['pricing_optimization']['price_adjustment_tips'],
                    'template': 'bargain_response_templates'
                })
        
        if discount_rate > 0.2:  # 折扣超过20%
            strategy['recommendations'].append({
                'type': 'high_discount_strategy',
                'description': f'折扣率过高({discount_rate:.2%})，建议使用增值服务替代降价',
                'tactics': ['提供配件', '延长保修', '优先服务', '会员权益'],
                'template': 'conversion_promotion_templates'
            })
        
        if deal_info.get('deal_detected', False) and discount_rate == 0:
            # 成交但无折扣，可考虑适当优惠以提高客户满意度
            strategy['recommendations'].append({
                'type': 'no_discount_completion',
                'description': '成功成交但未提供优惠，可考虑提供小礼品以提升满意度',
                'tactics': ['赠送小礼品', '提供额外服务', '下次优惠券'],
                'template': 'shipping_templates'
            })
        
        return strategy
    
    def optimize_shipping_strategy(self, analysis_result: Dict) -> Dict:
        """
        优化物流策略
        
        Args:
            analysis_result: 聊天记录分析结果
            
        Returns:
            Dict: 物流策略建议
        """
        shipping_info = analysis_result.get('shipping_info', {})
        deal_info = analysis_result.get('deal_info', {})
        
        strategy = {
            'strategy_type': 'shipping_optimization',
            'current_situation': f"物流讨论: {shipping_info.get('shipping_discussed', False)}, " +
                                f"物流费用: {shipping_info.get('shipping_cost', 'N/A')}, " +
                                f"是否成交: {deal_info.get('deal_detected', False)}",
            'recommendations': [],
            'confidence': 0.5
        }
        
        shipping_cost = shipping_info.get('shipping_cost')
        
        if shipping_cost and shipping_cost > self.optimizer_rules['shipping_optimization']['shipping_cost_threshold']:
            strategy['recommendations'].append({
                'type': 'high_shipping_cost',
                'description': f'物流费用较高({shipping_cost}元)，建议考虑包邮策略',
                'tactics': self.optimizer_rules['shipping_optimization']['shipping_promotion_strategies'],
                'template': 'shipping_templates'
            })
        
        if not shipping_info.get('shipping_discussed', False) and not deal_info.get('deal_detected', False):
            # 未讨论物流且未成交，可能物流是障碍
            strategy['recommendations'].append({
                'type': 'shipping_concern_undiscussed',
                'description': '客户未讨论物流但交易未完成，可能对物流有顾虑',
                'tactics': ['主动提及包邮', '说明配送时间', '保证物流安全'],
                'template': 'shipping_templates'
            })
        
        if deal_info.get('deal_detected', False) and shipping_cost and shipping_cost > 0:
            # 成交但有物流费用，可考虑优化物流策略
            strategy['recommendations'].append({
                'type': 'shipping_fee_completion',
                'description': '成功成交但收取了物流费，可考虑满额包邮策略',
                'tactics': ['设置包邮门槛', '多件包邮', '会员包邮'],
                'template': 'shipping_templates'
            })
        
        return strategy
    
    def generate_overall_optimization_report(self, analysis_result: Dict) -> Dict:
        """
        生成整体优化报告
        
        Args:
            analysis_result: 聊天记录分析结果
            
        Returns:
            Dict: 整体优化建议报告
        """
        report = {
            'file_path': analysis_result.get('file_path', 'Unknown'),
            'profit_impact_score': analysis_result.get('profit_impact_score', 0),
            'conversion_likelihood': analysis_result.get('conversion_likelihood', 0),
            'bargain_strategy': self.optimize_bargain_strategy(analysis_result),
            'conversion_strategy': self.optimize_conversion_strategy(analysis_result),
            'pricing_strategy': self.optimize_pricing_strategy(analysis_result),
            'shipping_strategy': self.optimize_shipping_strategy(analysis_result),
            'overall_recommendations': [],
            'priority_actions': []
        }
        
        # 合并所有策略的建议
        all_recommendations = []
        for strategy_key in ['bargain_strategy', 'conversion_strategy', 'pricing_strategy', 'shipping_strategy']:
            strategy = report[strategy_key]
            all_recommendations.extend(strategy.get('recommendations', []))
        
        # 确定优先级动作
        priority_map = {
            'low_profit_margin': 1,
            'high_discount_request': 2,
            'high_shipping_cost': 3,
            'high_negotiation_detected': 4,
            'shipping_concern_undiscussed': 5
        }
        
        # 按优先级排序
        priority_actions = []
        for rec in all_recommendations:
            priority = priority_map.get(rec.get('type', ''), 10)
            priority_actions.append({
                'priority': priority,
                'recommendation': rec
            })
        
        priority_actions.sort(key=lambda x: x['priority'])
        report['priority_actions'] = [item['recommendation'] for item in priority_actions]
        
        # 生成总体建议摘要
        report['overall_recommendations'] = self.generate_summary_recommendations(report)
        
        return report
    
    def generate_summary_recommendations(self, report: Dict) -> List[str]:
        """
        生成摘要建议
        
        Args:
            report: 优化报告
            
        Returns:
            List[str]: 摘要建议列表
        """
        recommendations = []
        
        # 根据利润影响评分提供建议
        profit_score = report['profit_impact_score']
        if profit_score < 40:
            recommendations.append("⚠️ 利润影响评分较低，需要重点关注定价策略和砍价处理")
        elif profit_score < 70:
            recommendations.append("📈 利润影响评分中等，有优化空间")
        else:
            recommendations.append("✅ 利润影响评分良好，继续保持")
        
        # 根据转化可能性提供建议
        conversion_likelihood = report['conversion_likelihood']
        if conversion_likelihood < 0.3:
            recommendations.append("💡 转化可能性较低，建议优化成交促进策略")
        elif conversion_likelihood < 0.7:
            recommendations.append("💡 转化可能性中等，可进一步优化")
        else:
            recommendations.append("✅ 转化可能性较高，策略有效")
        
        # 添加具体的优化建议
        if report['priority_actions']:
            top_priority = report['priority_actions'][0] if report['priority_actions'] else None
            if top_priority:
                recommendations.append(f"🔥 高优先级: {top_priority.get('description', '')}")
        
        return recommendations
    
    def save_optimization_report(self, report: Dict, output_path: str):
        """
        保存优化报告到文件
        
        Args:
            report: 优化报告
            output_path: 输出文件路径
        """
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"优化报告已保存到: {output_path}")
        except Exception as e:
            logger.error(f"保存优化报告失败: {e}")
    
    def generate_template_response(self, template_type: str, context: str = "") -> str:
        """
        根据模板类型和上下文生成回复
        
        Args:
            template_type: 模板类型
            context: 上下文信息
            
        Returns:
            str: 生成的回复
        """
        if template_type in self.strategy_templates:
            templates = self.strategy_templates[template_type]
            # 简单选择第一个模板，实际应用中可以基于上下文选择最合适的
            return templates[0] if templates else "感谢您的咨询，我们会尽快回复您"
        else:
            return "感谢您的咨询，我们会尽快回复您"


if __name__ == "__main__":
    optimizer = ProfitOptimizer()
    print("利润优化器已初始化")