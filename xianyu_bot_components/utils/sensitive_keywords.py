"""
敏感关键词检测器
用于检测需要人工接管的重要话题
"""

from typing import List, Dict, Tuple
from loguru import logger


class SensitiveKeywordDetector:
    """敏感关键词检测器类"""
    
    def __init__(self):
        """初始化敏感关键词库"""
        self.sensitive_keywords = {
            # 砍价议价类
            'bargaining': [
                '最低价', '不能再低', '血亏价', '跳楼价', '清仓价', '破价', '倒贴', 
                '给个底价', '最低多少', '还有优惠吗', '最大优惠', '最便宜',
                '再便宜点', '能不能再便宜', '价格能再低点吗', '给个最低价',
                '底价', '跳楼价', '亏本价', '一口价', '议价', '砍价'
            ],
            
            # 高度敏感与规则性话题
            'sensitive': [
                '违法', '违规', '黄赌毒', '刷单', '诈骗', '假货', '山寨', 
                '盗版', '侵权', '投诉', '举报', '差评', '封号', '违规操作',
                '骗子', '坑人', '套路', '陷阱', '假的', '骗钱', '骗人',
                '平台规则', '处罚', '违规', '禁言', '拉黑', '封禁'
            ],
            
            # 交易与支付安全
            'payment_security': [
                '转账', '微信', '支付宝', '银行卡', '线下交易', '脱离平台', '私下', 
                '担保交易', '货到付款', '预付', '定金', '押金', '保证金', '安全码',
                '私下交易', '平台外交易', '脱离闲鱼', '线下', '银行转账',
                '付款码', '收款码', '花呗', '借呗', '信用卡', '套现'
            ],
            
            # 情感驱动与复杂投诉
            'complaints': [
                '态度', '服务', '骗', '坑', '垃圾', '后悔', '差劲', '烂', 
                '气死', '无语', '失望', '投诉', '差评', '拉黑', '骗子',
                '不靠谱', '不诚信', '不负责任', '欺骗', '违约', '毁约',
                '不好', '很差', '非常差', '太差', '糟糕', '恶劣'
            ],
            
            # 专业咨询与个性化决策
            'consultation': [
                '专业', '咨询', '建议', '推荐', '定制', '私人', '专属', 
                '一对一', 'VIP', '专家', '顾问', '量身定做', '个性化',
                '私人定制', '专门', '专业建议', '专家建议', '咨询一下',
                '帮我看一下', '帮我分析', '专业评估', '专家评估'
            ],
            
            # 极限承诺与绝对化用语
            'absolute_claims': [
                '100%', '绝对', '保证', '无疑', '最强', '顶级', '完美', 
                '无条件', '永远', '终身', '史上', '最牛', '无敌', '必过', '包过',
                '一定', '肯定', '确保', '务必', '必须', '完全', '彻底',
                '全部', '所有', '每个', '任何', '所有条件', '任何情况'
            ]
        }
        
        # 定义例外关键词，这些关键词即使包含在敏感词中也不应触发敏感检测
        # 用于处理一些常见但无害的询问，如"有没有货"这类正常商品询问
        self.exception_keywords = [
            '有没有货', '有货吗', '还有货吗', '有现货吗', '还有吗', '有没有', '还有没有',
            '在吗', '有人吗', '在线', '客服', '咨询', '问问', '了解一下', '想买', '要买',
            '还有没有类似的', '有没有类似', '还有没有档期', '有没有档期', '有空吗',
            '有时间吗', '有空没', '有档期吗', '还有空吗', '有余量吗', '还有存货吗',
            '有库存吗', '还有存货', '有库存', '有货没', '还有吗', '有吗', '有无',
            '是否有', '是否还有', '是否在', '是否有人', '是否在线'
        ]
        
        # 统计关键词总数
        total_keywords = sum(len(keywords) for keywords in self.sensitive_keywords.values())
        logger.info(f"敏感关键词检测器初始化完成，共加载 {total_keywords} 个关键词")
    
    def detect_sensitive_keywords(self, text: str) -> List[Dict]:
        """
        检测敏感关键词，返回检测到的类别和关键词
        
        Args:
            text: 要检测的文本
            
        Returns:
            检测结果列表，每个元素包含类别、关键词和位置
        """
        if not text:
            return []
            
        detected = []
        text_lower = text.lower()
        
        # 检查是否是例外关键词，如果是则直接返回空列表（不认为是敏感词）
        for exception in self.exception_keywords:
            if exception in text_lower:
                return []  # 如果包含例外关键词，则不检测为敏感词
        
        for category, keywords in self.sensitive_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    detected.append({
                        'category': category,
                        'keyword': keyword,
                        'position': text_lower.find(keyword.lower())
                    })
        
        return detected
    
    def is_sensitive_message(self, text: str) -> Tuple[bool, List[Dict]]:
        """
        判断消息是否包含敏感词
        
        Args:
            text: 要检测的文本
            
        Returns:
            (是否为敏感消息, 检测到的敏感词详情)
        """
        detected = self.detect_sensitive_keywords(text)
        return len(detected) > 0, detected
    
    def get_sensitive_categories(self, text: str) -> List[str]:
        """
        获取文本中包含的敏感类别
        
        Args:
            text: 要检测的文本
            
        Returns:
            包含的敏感类别列表
        """
        detected = self.detect_sensitive_keywords(text)
        return list(set(item['category'] for item in detected))


# 测试代码
if __name__ == "__main__":
    detector = SensitiveKeywordDetector()
    
    test_messages = [
        "这个价格能不能再便宜点？",
        "你这个东西是假的，我要投诉",
        "我们私下转账吧，脱离平台交易",
        "服务态度太差了，非常失望",
        "请专业人员帮我评估一下",
        "保证100%正品，绝对没问题"
    ]
    
    for msg in test_messages:
        is_sensitive, details = detector.is_sensitive_message(msg)
        print(f"消息: {msg}")
        print(f"是否敏感: {is_sensitive}")
        if is_sensitive:
            print(f"检测详情: {details}")
            print(f"敏感类别: {detector.get_sensitive_categories(msg)}")
        print("-" * 50)