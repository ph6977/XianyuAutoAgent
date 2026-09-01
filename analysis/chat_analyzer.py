"""
聊天记录分析器 - 主分析引擎

分析爬取的聊天记录，提取关键指标如砍价次数、成交情况、价格变化等
"""
import os
import pandas as pd
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from loguru import logger


class ChatAnalyzer:
    """
    聊天记录分析器
    用于分析爬取的闲鱼聊天记录，提取影响成交率和利润的关键指标
    """
    
    def __init__(self):
        # 砍价相关关键词
        self.bargain_keywords = [
            '便宜', '少点', '再便宜', '能少', '砍价', '优惠', '打折', '降点', 
            '价格', '多少钱', '贵', '贵了', '太贵', '能便宜', '给个优惠', '优惠价'
        ]
        
        # 成交相关关键词
        self.deal_keywords = [
            '付款', '已付', '支付', '转账', '拍下', '下单', '成交', '买了', '要了',
            '发货', '快递', '包邮', '已发', '马上发', '确认收货', '收到货', '签收'
        ]
        
        # 价格相关关键词
        self.price_keywords = [
            '元', '价格', '卖', '售价', '标价', '成交价', '原价', '现价', '特价'
        ]
        
        # 物流相关关键词
        self.shipping_keywords = [
            '快递', '物流', '包邮', '运费', '邮费', '发', '发货', '到付', '顺丰', 
            '邮政', '圆通', '中通', '申通', '韵达', '配送', '到货', '签收'
        ]
        
        # 初始化结果存储
        self.analysis_results = {}
    
    def load_chat_data(self, file_path: str) -> pd.DataFrame:
        """
        加载聊天记录数据
        
        Args:
            file_path: CSV文件路径
            
        Returns:
            DataFrame: 加载的聊天记录数据
        """
        try:
            # 尝试不同的编码方式
            encodings = ['utf-8', 'gbk', 'gb2312']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    logger.info(f"成功使用 {encoding} 编码加载文件: {file_path}")
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise ValueError(f"无法使用常见编码格式打开文件: {file_path}")
            
            return df
            
        except Exception as e:
            logger.error(f"加载聊天记录失败: {e}")
            raise
    
    def extract_bargain_info(self, df: pd.DataFrame) -> Dict:
        """
        提取砍价相关信息
        
        Args:
            df: 聊天记录DataFrame
            
        Returns:
            Dict: 砍价信息统计
        """
        bargain_info = {
            'total_bargain_count': 0,  # 总砍价次数
            'bargain_conversations': [],  # 砍价对话记录
            'avg_bargain_per_conversation': 0,  # 每次对话平均砍价次数
            'bargain_success_rate': 0  # 砍价成功率
        }
        
        if df.empty:
            return bargain_info
        
        # 检查必需的列是否存在
        required_columns = ['role', 'content']  # 基础必需列
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        # 检查是否使用了增强版爬虫的数据结构
        if 'message_role' in df.columns and 'message_content' in df.columns:
            # 使用增强版爬虫的数据列名
            df = df.rename(columns={'message_role': 'role', 'message_content': 'content'})
        elif 'role' in df.columns and 'content' in df.columns:
            # 使用基础版爬虫的数据列名
            pass  # 不需要重命名
        else:
            logger.warning(f"缺少基础列: {missing_columns}, 尝试查找其他可能的列名")
            # 尝试查找相似的列名
            for col in df.columns:
                if 'role' in col.lower() or 'sender' in col.lower() or 'type' in col.lower():
                    df = df.rename(columns={col: 'role'})
                elif 'content' in col.lower() or 'message' in col.lower() or 'text' in col.lower():
                    df = df.rename(columns={col: 'content'})
        
        # 检查是否找到必要的列
        if 'role' not in df.columns or 'content' not in df.columns:
            logger.error(f"无法找到必需的列，现有列: {list(df.columns)}")
            return bargain_info
        
        # 筛选用户消息（非机器人/卖家消息）
        user_messages = df[df['role'].str.contains('user|customer|buyer', case=False, na=False)]
        
        bargain_conversations = []
        total_bargain_count = 0
        
        for idx, row in user_messages.iterrows():
            content = str(row['content']).lower() if pd.notna(row['content']) else ""
            
            # 检查是否包含砍价关键词
            for keyword in self.bargain_keywords:
                if keyword in content:
                    total_bargain_count += 1
                    bargain_conversations.append({
                        'index': idx,
                        'content': row['content'],
                        'keyword': keyword,
                        'timestamp': row.get('timestamp', 'N/A')
                    })
                    break  # 每条消息只计算一次
        
        bargain_info['total_bargain_count'] = total_bargain_count
        bargain_info['bargain_conversations'] = bargain_conversations
        
        # 计算每轮对话的平均砍价次数
        if len(df) > 0:
            bargain_info['avg_bargain_per_conversation'] = total_bargain_count / len(df)
        
        return bargain_info
    
    def extract_deal_info(self, df: pd.DataFrame) -> Dict:
        """
        提取成交相关信息
        
        Args:
            df: 聊天记录DataFrame
            
        Returns:
            Dict: 成交信息统计
        """
        deal_info = {
            'deal_detected': False,  # 是否检测到成交
            'deal_messages': [],  # 成交相关消息
            'deal_confidence': 0,  # 成交置信度
            'deal_method': '',  # 成交确认方式
            'transaction_status': 'pending'  # 交易状态
        }
        
        if df.empty:
            return deal_info
        
        # 检查列是否存在
        if 'content' not in df.columns:
            logger.warning("未找到content列")
            return deal_info
        
        deal_messages = []
        deal_keywords_found = 0
        
        for idx, row in df.iterrows():
            content = str(row['content']).lower() if pd.notna(row['content']) else ""
            
            # 检查是否包含成交关键词
            for keyword in self.deal_keywords:
                if keyword in content:
                    deal_keywords_found += 1
                    deal_messages.append({
                        'index': idx,
                        'content': row['content'],
                        'keyword': keyword,
                        'timestamp': row.get('timestamp', 'N/A')
                    })
                    
                    # 根据关键词确定交易状态
                    if any(w in content for w in ['付款', '已付', '支付', '转账', '拍下', '下单']):
                        deal_info['transaction_status'] = 'paid'
                    elif any(w in content for w in ['发货', '已发', '快递']):
                        if deal_info['transaction_status'] != 'paid':
                            deal_info['transaction_status'] = 'shipped'
                    elif any(w in content for w in ['确认收货', '收到货', '签收']):
                        deal_info['transaction_status'] = 'completed'
                    break
        
        deal_info['deal_detected'] = deal_keywords_found > 0
        deal_info['deal_messages'] = deal_messages
        deal_info['deal_confidence'] = min(deal_keywords_found / 3.0, 1.0)  # 简单的置信度计算
        
        # 确定成交确认方式
        if deal_messages:
            last_deal_message = deal_messages[-1]['content'].lower()
            if any(w in last_deal_message for w in ['付款', '已付', '支付', '转账']):
                deal_info['deal_method'] = 'payment_confirmed'
            elif any(w in last_deal_message for w in ['拍下', '下单']):
                deal_info['deal_method'] = 'order_placed'
            elif any(w in last_deal_message for w in ['发货', '已发']):
                deal_info['deal_method'] = 'shipping_confirmed'
        
        return deal_info
    
    def extract_price_info(self, df: pd.DataFrame) -> Dict:
        """
        提取价格相关信息
        
        Args:
            df: 聊天记录DataFrame
            
        Returns:
            Dict: 价格信息统计
        """
        price_info = {
            'original_price': None,  # 原价
            'final_price': None,  # 最终成交价
            'price_negotiation_count': 0,  # 价格协商次数
            'discount_rate': 0,  # 折扣率
            'price_mentions': []  # 价格提及记录
        }
        
        if df.empty:
            return price_info
        
        if 'content' not in df.columns:
            logger.warning("未找到content列")
            return price_info
        
        price_mentions = []
        price_pattern = r'(\d+(?:\.\d{1,2})?)元|(\d+(?:\.\d{1,2})?)块|(\d+(?:\.\d{1,2})?)[￥$]'
        
        for idx, row in df.iterrows():
            content = str(row['content']) if pd.notna(row['content']) else ""
            
            # 查找价格提及
            matches = re.findall(price_pattern, content)
            if matches:
                for match in matches:
                    # match是一个包含3个元素的元组，其中一个是实际匹配值，其他是空字符串
                    actual_price = next((m for m in match if m), None)
                    if actual_price:
                        try:
                            price_value = float(actual_price)
                            price_mentions.append({
                                'index': idx,
                                'content': content,
                                'price': price_value,
                                'timestamp': row.get('timestamp', 'N/A')
                            })
                        except ValueError:
                            continue
        
        price_info['price_mentions'] = price_mentions
        price_info['price_negotiation_count'] = len(price_mentions)
        
        # 简单的价格分析 - 假设第一个价格是原价，最后一个价格是成交价
        if price_mentions:
            price_info['original_price'] = price_mentions[0]['price']
            price_info['final_price'] = price_mentions[-1]['price']
            
            if price_info['original_price'] and price_info['original_price'] > 0:
                price_info['discount_rate'] = (
                    (price_info['original_price'] - price_info['final_price']) / 
                    price_info['original_price']
                )
        
        return price_info
    
    def extract_shipping_info(self, df: pd.DataFrame) -> Dict:
        """
        提取物流相关信息
        
        Args:
            df: 聊天记录DataFrame
            
        Returns:
            Dict: 物流信息统计
        """
        shipping_info = {
            'shipping_discussed': False,  # 是否讨论物流
            'shipping_cost': None,  # 物流费用
            'shipping_method': '',  # 物流方式
            'shipping_mentions': []  # 物流提及记录
        }
        
        if df.empty:
            return shipping_info
        
        if 'content' not in df.columns:
            logger.warning("未找到content列")
            return shipping_info
        
        shipping_mentions = []
        
        for idx, row in df.iterrows():
            content = str(row['content']).lower() if pd.notna(row['content']) else ""
            
            # 检查是否包含物流关键词
            for keyword in self.shipping_keywords:
                if keyword in content:
                    shipping_mentions.append({
                        'index': idx,
                        'content': row['content'],
                        'keyword': keyword,
                        'timestamp': row.get('timestamp', 'N/A')
                    })
                    
                    # 尝试提取物流费用
                    cost_pattern = r'运费(\d+(?:\.\d{1,2})?)|邮费(\d+(?:\.\d{1,2})?)|快递费(\d+(?:\.\d{1,2})?)|(\d+(?:\.\d{1,2})?)包邮'
                    cost_matches = re.findall(cost_pattern, content)
                    if cost_matches:
                        for match in cost_matches[0]:
                            if match and match.strip():
                                try:
                                    shipping_cost = float(match.strip())
                                    shipping_info['shipping_cost'] = shipping_cost
                                    break
                                except ValueError:
                                    continue
                    
                    # 识别物流方式
                    shipping_methods = ['顺丰', '邮政', '圆通', '中通', '申通', '韵达', '快递', '物流']
                    for method in shipping_methods:
                        if method in content:
                            shipping_info['shipping_method'] = method
                            break
                    break
        
        shipping_info['shipping_discussed'] = len(shipping_mentions) > 0
        shipping_info['shipping_mentions'] = shipping_mentions
        
        return shipping_info
    
    def analyze_single_chat(self, file_path: str) -> Dict:
        """
        分析单个聊天记录文件
        
        Args:
            file_path: 聊天记录文件路径
            
        Returns:
            Dict: 完整分析结果
        """
        logger.info(f"开始分析聊天记录: {file_path}")
        
        try:
            # 加载数据
            df = self.load_chat_data(file_path)
            
            # 执行各项分析
            bargain_info = self.extract_bargain_info(df)
            deal_info = self.extract_deal_info(df)
            price_info = self.extract_price_info(df)
            shipping_info = self.extract_shipping_info(df)
            
            # 计算总体指标
            total_messages = len(df) if not df.empty else 0
            user_messages = len(df[df['role'].str.contains('user|customer|buyer', case=False, na=False)]) if 'role' in df.columns else 0
            
            # 综合分析结果
            analysis_result = {
                'file_path': file_path,
                'total_messages': total_messages,
                'user_messages': user_messages,
                'bargain_info': bargain_info,
                'deal_info': deal_info,
                'price_info': price_info,
                'shipping_info': shipping_info,
                'profit_impact_score': self.calculate_profit_impact_score(bargain_info, deal_info, price_info, shipping_info),
                'conversion_likelihood': self.calculate_conversion_likelihood(bargain_info, deal_info, price_info)
            }
            
            self.analysis_results[file_path] = analysis_result
            logger.info(f"完成分析: {file_path}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"分析聊天记录失败: {e}")
            raise
    
    def calculate_profit_impact_score(self, bargain_info: Dict, deal_info: Dict, price_info: Dict, shipping_info: Dict) -> float:
        """
        计算利润影响评分
        
        Args:
            bargain_info: 砍价信息
            deal_info: 成交信息
            price_info: 价格信息
            shipping_info: 物流信息
            
        Returns:
            float: 利润影响评分 (0-100)
        """
        score = 50.0  # 基础分
        
        # 砍价影响：砍价次数越多，利润影响越大（负向）
        if bargain_info['total_bargain_count'] > 0:
            score -= min(bargain_info['total_bargain_count'] * 5, 30)  # 最多扣30分
        
        # 成交影响：成功成交加20分
        if deal_info['deal_detected']:
            score += 20
        
        # 价格折扣影响：折扣越大，利润影响越大（负向）
        if price_info['discount_rate'] > 0:
            score -= min(price_info['discount_rate'] * 100, 40)  # 最多扣40分
        
        # 物流费用影响：如果有明确物流费用，对利润有影响
        if shipping_info['shipping_cost'] is not None and shipping_info['shipping_cost'] > 0:
            score -= min(shipping_info['shipping_cost'] / 10, 10)  # 假设每10元运费扣1分
        
        return max(0, min(100, score))  # 限制在0-100之间
    
    def calculate_conversion_likelihood(self, bargain_info: Dict, deal_info: Dict, price_info: Dict) -> float:
        """
        计算转化可能性
        
        Args:
            bargain_info: 砍价信息
            deal_info: 成交信息
            price_info: 价格信息
            
        Returns:
            float: 转化可能性 (0-1)
        """
        # 如果已经检测到成交，转化可能性为1
        if deal_info['deal_detected']:
            return 1.0
        
        # 基础转化可能性
        likelihood = 0.3  # 基础30%
        
        # 成交相关关键词增加转化可能性
        if deal_info['deal_confidence'] > 0:
            likelihood += deal_info['deal_confidence'] * 0.4  # 最多增加40%
        
        # 价格协商可能表示购买意向，但过多可能降低转化
        if price_info['price_negotiation_count'] > 0:
            if price_info['price_negotiation_count'] <= 3:
                likelihood += 0.2  # 适量价格协商增加购买意向
            else:
                likelihood -= 0.1  # 过多价格协商可能表示犹豫
        
        # 砍价次数对转化的影响
        if bargain_info['total_bargain_count'] > 0:
            if bargain_info['total_bargain_count'] <= 2:
                likelihood += 0.1  # 适量砍价表示购买意向
            else:
                likelihood -= 0.2  # 过多砍价可能表示犹豫或不真诚
        
        return max(0, min(1, likelihood))  # 限制在0-1之间
    
    def analyze_batch(self, directory_path: str) -> List[Dict]:
        """
        批量分析聊天记录
        
        Args:
            directory_path: 包含聊天记录文件的目录路径
            
        Returns:
            List[Dict]: 所有文件的分析结果
        """
        results = []
        
        # 查找目录中的所有CSV文件
        for filename in os.listdir(directory_path):
            if filename.lower().endswith('.csv'):
                file_path = os.path.join(directory_path, filename)
                try:
                    result = self.analyze_single_chat(file_path)
                    results.append(result)
                    logger.info(f"完成批量分析: {filename}")
                except Exception as e:
                    logger.error(f"批量分析失败 {filename}: {e}")
        
        return results


if __name__ == "__main__":
    # 测试代码
    analyzer = ChatAnalyzer()
    print("聊天记录分析器已初始化")