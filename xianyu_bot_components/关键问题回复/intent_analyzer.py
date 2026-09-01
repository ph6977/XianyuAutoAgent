#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
关键问题回复系统 - 意图分析器
通过关键词匹配和DeepSeek语义分析，判断用户问题是否需要回复
"""

import os
import json
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from loguru import logger
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from ..utils.sensitive_keywords import SensitiveKeywordDetector


class IntentAnalyzer:
    """意图分析器"""
    
    def __init__(self, config_path: str = None, context_manager=None):
        """初始化意图分析器"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'agent_config.md')
        
        self.config_path = config_path
        self.agents_config = self._load_config()
        self.client = OpenAI(
            api_key=os.getenv("API_KEY") or os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("MODEL_BASE_URL", "https://api.deepseek.com")
        )
        self.model_name = os.getenv("MODEL_NAME", "deepseek-chat")
        
        # 初始化敏感词检测器
        self.sensitive_detector = SensitiveKeywordDetector()
        
        # 上下文管理器
        self.context_manager = context_manager
        
        # 日志文件路径
        self.log_file = os.path.join(os.path.dirname(__file__), 'intent_log.txt')
        
    def _load_config(self) -> Dict:
        """加载Agent配置"""
        agents = {}
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            current_agent = None
            current_keywords = []
            current_threshold = 80
            current_description = ""
            
            for line in lines:
                line = line.strip()
                
                # 跳过文档标题和系统规则
                if line.startswith('# 关键问题回复系统') or line.startswith('## 系统') or line.startswith('### 回复策略') or line.startswith('### 日志记录'):
                    continue
                
                # 检测Agent标题
                if line.startswith('## ') and 'Agent' in line:
                    # 保存上一个Agent
                    if current_agent and current_keywords:
                        agents[current_agent] = {
                            'keywords': current_keywords,
                            'threshold': current_threshold,
                            'description': current_description
                        }
                    
                    # 开始新的Agent
                    current_agent = line.replace('## ', '').strip()
                    current_keywords = []
                    current_threshold = 80
                    current_description = ""
                
                # 解析关键词
                elif line.startswith('### 关键词列表'):
                    continue  # 标记行，跳过
                elif line.startswith('- ') and current_agent:
                    keyword = line[2:].strip()
                    if keyword:
                        current_keywords.append(keyword)
                
                # 解析阈值
                elif line.startswith('### 匹配度阈值'):
                    threshold_line = line.replace('### 匹配度阈值', '').strip()
                    try:
                        current_threshold = int(threshold_line.replace('%', ''))
                    except ValueError:
                        current_threshold = 80
                
                # 解析描述
                elif line.startswith('### 服务描述'):
                    continue  # 标记行，跳过
                elif line and current_agent and not line.startswith('#') and not line.startswith('-'):
                    if current_description:
                        current_description += " " + line
                    else:
                        current_description = line
            
            # 保存最后一个Agent
            if current_agent and current_keywords:
                agents[current_agent] = {
                    'keywords': current_keywords,
                    'threshold': current_threshold,
                    'description': current_description
                }
            
            logger.info(f"成功加载 {len(agents)} 个Agent配置")
            for name, config in agents.items():
                logger.debug(f"Agent: {name}, 关键词数量: {len(config['keywords'])}, 阈值: {config['threshold']}")
            
            return agents
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _keyword_match(self, question: str) -> List[str]:
        """关键词匹配"""
        matched_agents = []
        question_lower = question.lower()
        
        for agent_name, config in self.agents_config.items():
            for keyword in config['keywords']:
                if keyword.lower() in question_lower:
                    logger.debug(f"关键词匹配: {agent_name} - 关键词: {keyword}")
                    matched_agents.append(agent_name)
                    break
        
        return matched_agents
    
    def _semantic_match_with_context(self, question: str, context_entities: Dict[str, str]) -> List[Tuple[str, float]]:
        """使用上下文实体进行语义匹配"""
        matched_agents = []
        
        try:
            # 构建Agent描述
            agent_descriptions = []
            for agent_name, config in self.agents_config.items():
                description = f"{agent_name}: {config['description']}\n关键词: {', '.join(config['keywords'])}"
                agent_descriptions.append(description)
            
            # 构建上下文信息
            context_info = ""
            if context_entities:
                context_items = []
                for entity_type, entity_value in context_entities.items():
                    if entity_type == "location":
                        context_items.append(f"用户位置: {entity_value}")
                    elif entity_type == "device_type":
                        context_items.append(f"设备类型: {entity_value}")
                    elif entity_type == "time_reference":
                        context_items.append(f"时间参考: {entity_value}")
                    else:
                        context_items.append(f"{entity_type}: {entity_value}")
                
                if context_items:
                    context_info = "会话上下文: " + ", ".join(context_items) + "\n"
            
            # 构建提示词
            prompt = f"""
请分析以下用户问题与各个Agent服务的匹配度。

{context_info}
用户问题：{question}

Agent服务列表：
{chr(10).join(agent_descriptions)}

请以JSON格式返回匹配结果，格式如下：
{{
    "results": [
        {{"agent": "Agent名称", "score": 匹配度分数(0-100), "reason": "匹配原因"}},
        ...
    ]
}}

要求：
1. 匹配度分数为0-100的整数
2. 只返回匹配度大于等于50的Agent
3. 如果没有匹配的Agent，返回空数组
4. 严格按照JSON格式返回
5. 在分析时考虑上下文信息，如果用户问题中缺少某些信息（如地点、设备类型等），但上下文中有相关信息，请将上下文信息整合到分析中
"""
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的意图分析助手，擅长分析用户问题与服务的匹配度。在分析时需要考虑上下文信息，如果用户问题不完整但上下文中有相关信息，应将上下文信息整合到分析中。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 尝试解析JSON，处理markdown格式
            try:
                # 如果返回的是markdown格式，提取JSON部分
                if result_text.startswith('```json'):
                    json_start = result_text.find('{')
                    json_end = result_text.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        result_text = result_text[json_start:json_end]
                
                result_data = json.loads(result_text)
                for item in result_data.get('results', []):
                    agent_name = item.get('agent', '')
                    score = item.get('score', 0)
                    reason = item.get('reason', '')
                    
                    if agent_name in self.agents_config:
                        threshold = self.agents_config[agent_name]['threshold']
                        if score >= threshold:
                            matched_agents.append((agent_name, score))
                            logger.debug(f"语义匹配: {agent_name} - 分数: {score} - 原因: {reason}")
                
                return matched_agents
                
            except json.JSONDecodeError as e:
                logger.error(f"解析DeepSeek返回结果失败: {e}")
                logger.debug(f"原始返回: {result_text}")
                return []
                
        except Exception as e:
            logger.error(f"语义匹配失败: {e}")
            return []

    def _semantic_match(self, question: str) -> List[Tuple[str, float]]:
        """语义匹配（保留原始方法以兼容）"""
        return self._semantic_match_with_context(question, {})
    
    def _log_decision(self, question: str, keyword_matches: List[str], 
                     semantic_matches: List[Tuple[str, float]], 
                     final_decision: List[str], reason: str):
        """记录决策日志"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            log_entry = f"""
[{timestamp}] 用户问题: {question}
关键词匹配: {keyword_matches}
语义匹配: {[(agent, score) for agent, score in semantic_matches]}
最终决策: {final_decision}
决策原因: {reason}
---
"""
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
                
        except Exception as e:
            logger.error(f"写入日志失败: {e}")
    
    def analyze_intent(self, question: str, context: str = "", user_id: str = None, chat_id: str = None) -> Tuple[List[str], str]:
        """
        分析用户意图，使用强化的语义分析替代关键词匹配
        
        Args:
            question: 用户问题
            context: 对话上下文
            user_id: 用户ID
            chat_id: 聊天ID
        
        Returns:
            Tuple[List[str], str]: (匹配的Agent列表, 决策原因)
        """
        logger.info(f"开始分析用户问题: {question}")
        
        # 0. 检测是否包含敏感词
        is_sensitive, detected_keywords = self.sensitive_detector.is_sensitive_message(question)
        if is_sensitive:
            reason = f"检测到敏感词，转人工处理: {detected_keywords}"
            self._log_decision(question, [], [], [], reason)
            logger.info(f"检测到敏感词，转人工处理: {question}")
            # 返回空列表，表示需要人工处理
            return [], reason
        
        # 1. 从上下文管理器获取实体信息
        extracted_context_info = {}
        if self.context_manager and user_id:
            extracted_context_info = self.context_manager.get_all_entities(user_id, chat_id or user_id)
            logger.debug(f"从上下文管理器获取实体: {extracted_context_info}")
        
        # 2. 使用LLM进行意图分析
        try:
            # 构建Agent描述
            agent_descriptions = []
            for agent_name, config in self.agents_config.items():
                description = f"{agent_name}: {config['description']}"
                agent_descriptions.append(description)
            
            # 构建上下文信息
            context_info = ""
            if context:
                context_info += f"对话上下文: {context}\n"
            if extracted_context_info:
                context_items = []
                for entity_type, entity_value in extracted_context_info.items():
                    if entity_type == "location":
                        context_items.append(f"用户位置: {entity_value}")
                    elif entity_type == "device_type":
                        context_items.append(f"设备类型: {entity_value}")
                    elif entity_type == "time_reference":
                        context_items.append(f"时间参考: {entity_value}")
                    else:
                        context_items.append(f"{entity_type}: {entity_value}")
                
                if context_items:
                    context_info += "实体信息: " + ", ".join(context_items) + "\n"
            
            # 构建提示词
            prompt = f"""请分析用户问题是否与以下业务相关，并确定最适合处理的Agent。

{context_info}
用户问题：{question}

可用Agent服务：
{chr(10).join(agent_descriptions)}

请以JSON格式返回分析结果，格式如下：
{{
    "should_reply": 是否需要回复(true/false),
    "matched_agents": ["匹配的Agent名称列表"],
    "confidence": 置信度分数(0-100),
    "intent_type": "意图类型",
    "extracted_info": {{
        "target_devices": ["设备列表"],
        "rental_dates": ["日期"],
        "target_city": "城市",
        "other_info": "其他信息"
    }},
    "reason": "分析原因"
}}

要求：
1. should_reply: 如果问题与任意Agent服务相关则为true，否则为false
2. matched_agents: 返回匹配的Agent名称列表，如果should_reply为false则为空数组
3. confidence: 置信度分数(0-100)
4. intent_type: 如availability_check, location_inquiry, price_inquiry等
5. extracted_info: 提取关键信息
6. reason: 详细分析原因
7. 在分析时充分考虑上下文信息，即使用户问题本身不完整，但如果有上下文信息可以补充，则应进行匹配
"""
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的意图分析助手，擅长分析用户问题与服务的匹配度。在分析时需要考虑上下文信息，如果用户问题不完整但上下文中有相关信息，应将上下文信息整合到分析中。不要进行关键词匹配，而是理解问题的真正意图。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 尝试解析JSON，处理markdown格式
            try:
                # 如果返回的是markdown格式，提取JSON部分
                if result_text.startswith('```json'):
                    json_start = result_text.find('{')
                    json_end = result_text.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        result_text = result_text[json_start:json_end]
                
                result_data = json.loads(result_text)
                should_reply = result_data.get('should_reply', False)
                
                if should_reply:
                    matched_agents = result_data.get('matched_agents', [])
                    reason = result_data.get('reason', '语义分析匹配')
                    confidence = result_data.get('confidence', 0)
                    
                    # 验证匹配的Agent是否在配置中
                    valid_matched_agents = []
                    for agent_name in matched_agents:
                        if agent_name in self.agents_config:
                            valid_matched_agents.append(agent_name)
                    
                    if valid_matched_agents:
                        final_reason = f"语义分析匹配成功: {', '.join(valid_matched_agents)}({confidence}分) - {reason}"
                        self._log_decision(question, [], [(agent, confidence) for agent in valid_matched_agents], valid_matched_agents, final_reason)
                        logger.info(f"决策结果: 回复 - {final_reason}")
                        return valid_matched_agents, final_reason
                    else:
                        reason = "问题与所有Agent服务都不相关"
                        self._log_decision(question, [], [], [], reason)
                        logger.info(f"决策结果: 静默 - {reason}")
                        return [], reason
                else:
                    reason = "问题与所有Agent服务都不相关"
                    self._log_decision(question, [], [], [], reason)
                    logger.info(f"决策结果: 静默 - {reason}")
                    return [], reason
                
            except json.JSONDecodeError as e:
                logger.error(f"解析DeepSeek返回结果失败: {e}")
                logger.debug(f"原始返回: {result_text}")
                # 如果解析失败，尝试使用上下文感知检查
                context_matches = self._context_aware_check(question, context)
                if context_matches:
                    reason = f"上下文感知匹配: {', '.join(context_matches)}"
                    self._log_decision(question, context_matches, [], context_matches, reason)
                    logger.info(f"决策结果: 回复 - {reason}")
                    return context_matches, reason
                else:
                    reason = "问题与所有Agent服务都不相关"
                    self._log_decision(question, [], [], [], reason)
                    logger.info(f"决策结果: 静默 - {reason}")
                    return [], reason
        except Exception as e:
            logger.error(f"语义分析失败: {e}")
            # 如果语义分析失败，回退到上下文感知检查
            context_matches = self._context_aware_check(question, context)
            if context_matches:
                reason = f"上下文感知匹配: {', '.join(context_matches)}"
                self._log_decision(question, context_matches, [], context_matches, reason)
                logger.info(f"决策结果: 回复 - {reason}")
                return context_matches, reason
            else:
                reason = "问题与所有Agent服务都不相关"
                self._log_decision(question, [], [], [], reason)
                logger.info(f"决策结果: 静默 - {reason}")
                return [], reason
    
    def _context_aware_check(self, question: str, context: str) -> List[str]:
        """上下文感知检查 - 检查用户是否在回复我们的提问"""
        try:
            if not context:
                return []
            
            # 检查最近的机器人回复是否包含提问
            recent_replies = self._extract_recent_replies(context)
            if not recent_replies:
                return []
            
            # 检查最近的机器人回复是否包含位置询问
            location_question_patterns = [
                "哪个城市", "您在哪个城市", "您所在的城市", "您的城市",
                "告诉我您的城市", "您在什么地方", "您在哪里",
                "您的位置", "所在地", "地区"
            ]
            
            has_location_question = False
            for reply in recent_replies:
                for pattern in location_question_patterns:
                    if pattern in reply:
                        has_location_question = True
                        break
                if has_location_question:
                    break
            
            # 如果机器人最近问了位置，且用户回答包含城市信息，则匹配租赁顾问
            if has_location_question:
                # 检查用户回答是否包含城市信息
                city_keywords = [
                    "北京", "上海", "广州", "深圳", "杭州", "南京", "武汉", "成都", "西安", 
                    "天津", "重庆", "青岛", "济南", "大连", "沈阳", "长春", "哈尔滨", 
                    "石家庄", "太原", "呼和浩特", "郑州", "合肥", "福州", "南昌", 
                    "长沙", "南宁", "海口", "昆明", "贵阳", "拉萨", "兰州", "西宁", 
                    "银川", "乌鲁木齐", "苏州", "无锡", "常州", "南通", "徐州", 
                    "扬州", "泰州", "镇江", "盐城", "淮安", "连云港", "宿迁"
                ]
                
                location_indicators = ["我在", "我在的", "我这边", "我这里", "我所在地", "我的位置", "我的城市"]
                
                # 检查是否包含城市名或位置指示词
                for city in city_keywords:
                    if city in question:
                        logger.debug(f"上下文感知: 检测到城市回复 {city}")
                        return ["智能租赁顾问Agent"]
                
                for indicator in location_indicators:
                    if indicator in question:
                        logger.debug(f"上下文感知: 检测到位置指示词 {indicator}")
                        return ["智能租赁顾问Agent"]
            
            return []
            
        except Exception as e:
            logger.error(f"上下文感知检查失败: {e}")
            return []
    
    def _extract_recent_replies(self, context: str, max_count: int = 3) -> List[str]:
        """提取最近的机器人回复"""
        try:
            import re
            
            # 确保context是字符串类型
            if not isinstance(context, str):
                if isinstance(context, list):
                    context = '\n'.join(str(item) for item in context)
                else:
                    context = str(context)
            
            # 简单的上下文解析 - 查找机器人回复
            # 假设格式为: 机器人: 回复内容
            pattern = r"机器人[:：]\s*(.*?)(?=\n用户[:：]|$)"
            matches = re.findall(pattern, context, re.DOTALL)
            
            # 返回最近的几条回复
            return matches[-max_count:] if matches else []
            
        except Exception as e:
            logger.error(f"提取最近回复失败: {e}")
            return []
    
    def reload_config(self):
        """重新加载配置"""
        self.agents_config = self._load_config()
        logger.info("配置已重新加载")


# 测试代码
if __name__ == "__main__":
    analyzer = IntentAnalyzer()
    
    # 测试问题
    test_questions = [
        "我想租一个相机",
        "我的快递什么时候到",
        "今天天气怎么样",
        "你们有手机出租吗",
        "物流信息怎么查"
    ]
    
    for question in test_questions:
        matched_agents, reason = analyzer.analyze_intent(question)
        print(f"问题: {question}")
        print(f"匹配Agent: {matched_agents}")
        print(f"原因: {reason}")
        print("-" * 50)
