# XianyuAutoAgent 项目面试准备指南

> 本文档帮助你熟悉项目结构、理解技术难点，并准备面试中的项目介绍。

---

## 一、项目概述

### 一句话描述
**XianyuAutoAgent** 是一个为**闲鱼（Goofish）二手交易平台**打造的 **7x24小时AI自动值守客服机器人**，帮卖家自动回复买家消息、处理议价、查询库存。

### 核心价值
- **实时性**：WebSocket长连接，实时接收买家消息
- **智能性**：多专家Agent系统，不同问题交给不同专家处理
- **稳定性**：心跳维持、自动重连、敏感词检测、人工接管

### 技术栈
- **Python 3.8+**（推荐3.10）
- **OpenAI SDK**：调用DeepSeek等LLM API
- **websockets**：WebSocket长连接
- **playwright**：浏览器自动化（爬虫）
- **requests**：HTTP请求
- **飞书开放平台API**：集成飞书知识库

---

## 二、项目架构

### 整体结构
```
XianyuAutoAgent/
├── src/                        # 源代码主目录
│   ├── bot/                    # 核心机器人模块
│   ├── agents/                 # 多专家Agent系统
│   ├── core/                   # 核心基础模块
│   ├── utils/                  # 工具模块
│   ├── knowledge/              # 知识库模块
│   ├── crawler/                # 爬虫模块
│   ├── analysis/               # 分析模块
│   └── prompts/                # 提示词模板
├── tests/                      # 测试文件
├── scripts/                    # 辅助脚本
├── docs/                       # 文档
├── .env                        # 环境变量配置
├── requirements.txt            # Python依赖
├── start_menu.py               # 启动入口
├── Dockerfile                  # Docker多阶段构建
└── docker-compose.yml          # Docker Compose部署
```

### 模块职责
- **src/bot/**：核心业务逻辑，包含消息处理、Agent系统、API交互
- **src/agents/**：多专家Agent系统，包含路由、议价、租赁等专家
- **src/core/**：核心基础模块，包含客户端、上下文管理
- **src/utils/**：工具模块，包含加解密、API封装、敏感词检测
- **src/knowledge/**：知识库模块，飞书在线表格作为实时设备库存数据库
- **src/crawler/**：爬虫模块，浏览器自动化、Cookie管理、数据导出
- **src/analysis/**：分析模块，聊天记录分析、利润优化、报告生成
- **src/prompts/**：提示词模板，各专家Agent的提示词配置

---

## 三、核心技术实现（通俗解释）

### 1. 多专家Agent系统 - "医院分诊系统"

**专业说法**：四级漏斗路由 + LLM兜底的混合路由架构

**通俗解释**：
想象一家医院的分诊系统：
1. **智能挂号机**（SmartReplyManager）：先快速判断你的症状，直接告诉你该挂什么科
2. **导诊护士**（租赁关键词检测）：如果你是急诊（问租赁的），直接送急诊室
3. **正式分诊**（IntentRouter）：先做基础检查（关键词匹配），不行再做深度检查（LLM分析）
4. **全科医生**（DefaultAgent）：如果其他专家都不确定，就由全科医生处理

**代码位置**：`xianyu_bot_components/agents/xianyu_agent.py`，第251-302行

**核心逻辑**：
```python
class IntentRouter:
    def detect(self, user_msg: str, item_desc, context) -> str:
        # 1. 租赁类关键词优先检查
        if any(kw in text_clean for kw in self.rules['rental']['keywords']):
            return 'rental'
        # 2. 技术类关键词优先检查
        if any(kw in text_clean for kw in self.rules['tech']['keywords']):
            return 'tech'
        # 3. 价格类检查
        # ...
        # 4. 大模型兜底
        return self.classify_agent.generate(user_msg=user_msg, ...)
```

**为什么这样设计**：
- 快的问题用规则快速解决（零成本）
- 复杂的问题用AI仔细分析（高成本但准确）
- 每个专家有自己的专长（价格、技术、租赁等）

---

### 2. 动态议价温度 - "卖家心理模拟器"

**专业说法**：temperature = min(0.3 + bargain_count * 0.15, 0.9)

**通俗解释**：
就像一个经验丰富的卖家：
- **第一次砍价**（温度0.3）：态度坚定，"不行，最低就是这个价了"
- **第二次砍价**（温度0.45）：稍微松动，"嗯...让我想想"
- **第三次砍价**（温度0.6）：开始让步，"好吧，给你打个折"
- **第四次砍价**（温度0.9）：高度灵活，"行行行，就按你说的价"

**代码位置**：`xianyu_bot_components/agents/xianyu_agent.py`，第388-413行

**核心逻辑**：
```python
class PriceAgent(BaseAgent):
    def generate(self, user_msg, item_desc, context, bargain_count=0):
        dynamic_temp = self._calc_temperature(bargain_count)
        # 使用 dynamic_temp 调用LLM...

    def _calc_temperature(self, bargain_count: int) -> float:
        return min(0.3 + bargain_count * 0.15, 0.9)
```

**为什么这样设计**：
- 模拟真实卖家的心理变化过程
- 第一次砍价太容易答应，卖家会亏本
- 砍价次数越多，说明买家诚意越高，可以适当让步

---

### 3. WebSocket长连接 - "永不挂断的电话"

**专业说法**：WebSocket长连接 + 心跳维持 + 指数退避重连

**通俗解释**：
就像两个人保持电话联系：
1. **建立连接**：拨通电话，保持通话状态
2. **心跳机制**：每30秒按一下"嘟"，确认对方还在听
3. **消息处理**：听到对方说话就处理，处理完回话
4. **自动重连**：如果电话断了，不是疯狂拨号，而是等5秒、10秒、20秒...越来越耐心地重连

**代码位置**：`xianyu_bot_components/xianyu_bot.py`，第713-786行（主循环）、第621-683行（心跳）

**核心逻辑**：
```python
async def heartbeat_loop(self, ws):
    consecutive_timeouts = 0
    max_consecutive_timeouts = 3

    while True:
        if current_time - self.last_heartbeat_time >= self.heartbeat_interval:
            await self.send_heartbeat(ws)

        time_since_last_response = current_time - self.last_heartbeat_response
        if time_since_last_response > (self.heartbeat_interval + self.heartbeat_timeout):
            consecutive_timeouts += 1
            if consecutive_timeouts >= max_consecutive_timeouts:
                break  # 连续3次超时，判定连接断开
        else:
            consecutive_timeouts = 0  # 有响应，重置计数
```

**为什么这样设计**：
- 实时性：买家发消息，卖家能立刻收到
- 稳定性：网络波动时能自动恢复
- 防崩溃：指数退避避免同时重连打爆服务器

---

### 4. 智能回复系统 - "智能前台"

**专业说法**：双层决策系统（敏感词过滤 + 意图分析）

**通俗解释**：
就像公司前台接待：
1. **安全检查**：先看是不是骗子来套话（敏感词检测），如果是直接转人工
2. **意图分析**：问AI分析师"这个问题该不该回答？交给谁回答？"
3. **决策输出**：AI说"该回答"就自动回复，说"不该回答"就静默不回复

**代码位置**：`xianyu_bot_components/关键问题回复/smart_reply_manager.py`，第94-153行

**核心逻辑**：
```python
def process_message(self, user_message, user_id=None, item_id=None, context=None, chat_id=None):
    # 0. 敏感词检测
    is_sensitive, detected_keywords = self.sensitive_detector.is_sensitive_message(user_message)
    if is_sensitive:
        return []  # 空列表 = 静默不回复

    # 1. 意图分析
    matched_agents, reason = self.intent_analyzer.analyze_intent(user_message, context, user_id, chat_id)

    # 2. 没有匹配的Agent → 静默
    if not matched_agents:
        return []

    # 3. 调用匹配的Agent生成回复
    replies = []
    for agent_name in matched_agents:
        reply = self._call_rental_agent(agent, ...)
        if reply:
            replies.append(reply)

    return replies  # 空列表 = 静默；非空 = 自动回复
```

**为什么这样设计**：
- 安全性：敏感内容不自动回复，避免风险
- 智能性：不是所有问题都要回复，避免打扰用户
- 专业性：不同问题交给不同专家处理

---

### 5. 飞书知识库 - "实时库存查询系统"

**专业说法**：飞书在线表格作为RAG知识库

**通俗解释**：
就像一个实时更新的库存表：
- **数据源**：飞书在线表格，卖家可以随时更新
- **查询方式**：问AI"某设备某天有空吗？"，AI去查表格回答
- **状态表示**：空白=可租，1/2/3=不可租（在物流/在客户/在寄回）

**代码位置**：`feishu_knowledge_base/feishu_sheet_reader.py`，第66-157行

**核心逻辑**：
```python
def _is_device_available(self, status_value) -> bool:
    # None / 空字符串 / 'None' → 可租用（白色格子）
    if status_value is None or status_value == '' or status_value == 'None':
        return True
    # 数字1/2/3 → 不可租用（在物流中/在客户手中/寄回中）
    try:
        status_num = int(str(status_value).strip())
        return False
    except ValueError:
        return False
```

**为什么这样设计**：
- 实时性：卖家更新表格，AI立刻知道最新库存
- 低成本：不需要额外搭建数据库
- 易用性：卖家用熟悉的Excel操作，不需要技术背景

---

### 6. 上下文管理 - "智能记事本"

**专业说法**：实体提取 + TTL过期 + 多位置管理

**通俗解释**：
就像一个智能记事本：
- **自动记录**：你说"想在北京租相机"，记事本自动记下"位置=北京，设备=相机"
- **有保质期**：每条记录1小时后自动擦掉，避免信息过时
- **多位置管理**：你说"北京、上海都可以"，记事本记下两个城市，但默认用最新的

**代码位置**：`xianyu_bot_components/core/context_manager.py`，第254-286行

**核心逻辑**：
```python
def _extract_and_store_entities(self, user_id, chat_id, content):
    self.clear_expired_entities()

    # 1. 提取地点实体（支持多位置）
    location_keywords = ["北京", "上海", "广州", "深圳", ...]
    found_locations = [loc for loc in location_keywords if loc in content]
    if found_locations:
        self.store_multiple_locations(user_id, chat_id, found_locations)

    # 2. 提取设备类型（只存第一个）
    device_keywords = ["胖卡", "相机", "手机", ...]
    for device in device_keywords:
        if device in content:
            self.store_entity(user_id, chat_id, "device_type", device)
            break

    # 3. 提取时间引用
    time_keywords = ["今天", "明天", "后天", ...]
    for time_kw in time_keywords:
        if time_kw in content:
            self.store_entity(user_id, chat_id, "time_reference", time_kw)
            break
```

**为什么这样设计**：
- 连贯性：记住你说过的话，不用重复问
- 准确性：只记住关键信息，避免信息过载
- 时效性：过时的信息自动清除，避免误导

---

## 四、消息处理流程

### 完整流程图
```
WebSocket收到消息
    ↓
发送ACK响应（告诉服务器"收到了"）
    ↓
同步包过滤（只处理聊天消息）
    ↓
双重解码尝试（Base64 → 解密）
    ↓
敏感词检测（命中则转人工）
    ↓
意图分析（LLM判断是否回复）
    ↓
多专家路由（分发给对应专家）
    ↓
生成回复（调用对应Agent）
    ↓
发送回复（通过WebSocket）
```

---

## 五、面试介绍技巧

### 介绍结构（3分钟）
1. **项目背景**（30秒）：解决闲鱼卖家24小时客服需求
2. **核心架构**（1分钟）：多专家Agent系统 + 混合路由
3. **技术亮点**（1分钟）：动态议价、实时库存、智能回复
4. **个人贡献**（30秒）：根据你的实际情况补充

### 关键话术模板

**介绍架构**：
> "我们采用了类似医院分诊的系统，快速问题用规则处理，复杂问题用AI分析，不同问题交给不同专家"

**介绍议价**：
> "系统模拟真实卖家心理，第一次砍价态度坚定，多次砍价后逐渐松口"

**介绍稳定性**：
> "通过心跳机制保持连接，断线后指数退避重连，避免服务器压力"

**介绍知识库**：
> "用飞书在线表格作为实时库存数据库，卖家更新表格AI立刻知道，不需要额外搭建数据库"

---

## 六、可能被问到的问题

### Q1: 为什么选择多专家架构而不是单个AI？
**回答**：不同问题需要不同专业知识。价格问题需要议价技巧，技术问题需要专业知识，租赁问题需要库存查询。单个AI难以精通所有领域，多专家架构让每个AI专注自己的领域，回复更准确。

### Q2: 如何保证实时性？
**回答**：通过WebSocket长连接实时接收消息，配合心跳机制保持连接稳定。消息处理采用异步架构，一个主循环处理消息，多个任务并行处理心跳、Token刷新等。

### Q3: 如何处理AI回复错误的情况？
**回答**：有多重保障机制：
1. 敏感词检测：危险内容不自动回复
2. 人工接管：卖家可随时切换人工模式
3. 智能回退：AI失败时生成预设回复
4. 消息去重：避免重复回复

### Q4: 飞书知识库的优势是什么？
**回答**：实时性好，卖家更新表格AI立刻知道；成本低，不需要额外数据库；易用性好，卖家用熟悉的Excel操作。相比传统向量数据库，更适合这种实时库存查询场景。

### Q5: 如何处理并发消息？
**回答**：采用asyncio异步架构，WebSocket消息处理、心跳维持、Token刷新都是独立的异步任务，可以并发处理。消息去重机制（SHA256 + TTL）避免重复处理同一消息。

### Q6: 如何保证安全性？
**回答**：多重安全机制：
1. 敏感词检测：6大类敏感词 + 例外白名单
2. 人工接管：卖家可随时切换人工模式
3. 消息去重：避免重复回复
4. 防回声：检测机器人自己的消息，避免无限循环

---

## 七、项目技术亮点总结

| 设计 | 亮点 | 一句话解释 |
|------|------|-----------|
| **混合路由** | 规则优先+LLM兜底 | 快的先用规则，不确定的再用AI |
| **动态温度** | temperature随议价轮次递增 | 越砍越松口，模拟真实卖家心理 |
| **双重安全** | 敏感词前置+安全过滤后置 | 前门拦敏感内容，后门拦平台违规 |
| **上下文感知** | 实体提取+TTL过期+多位置管理 | 记住你说过的关键信息，但有保质期 |
| **弹性重连** | 指数退避+随机抖动 | 断了不要紧，越来越耐心地重连 |

---

## 八、关键代码位置速查

| 功能 | 文件位置 | 行号范围 |
|------|----------|----------|
| 多专家路由 | `xianyu_bot_components/agents/xianyu_agent.py` | 251-302 |
| 动态温度策略 | `xianyu_bot_components/agents/xianyu_agent.py` | 388-413 |
| WebSocket主循环 | `xianyu_bot_components/xianyu_bot.py` | 713-786 |
| 心跳机制 | `xianyu_bot_components/xianyu_bot.py` | 621-683 |
| 智能回复管理 | `xianyu_bot_components/关键问题回复/smart_reply_manager.py` | 94-153 |
| 意图分析 | `xianyu_bot_components/关键问题回复/intent_analyzer.py` | 265-435 |
| 飞书知识库 | `feishu_knowledge_base/feishu_sheet_reader.py` | 32-157 |
| 上下文管理 | `xianyu_bot_components/core/context_manager.py` | 254-286 |

---

## 九、项目数据

- **测试文件**：25个
- **核心依赖**：8个主要库
- **环境配置**：105行配置项
- **敏感词分类**：6大类，80+关键词
- **Agent类型**：5种专家Agent

---

> **提示**：面试前重点复习多专家Agent系统、WebSocket消息处理、飞书知识库集成这三个部分，这些是最可能被面试官深入提问的内容。
