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

### 代码注释
所有核心源代码文件已添加详细的中文注释，包括：
- 模块级注释：说明模块功能、架构设计、工作流程
- 类级注释：说明类的职责、属性、方法
- 函数级注释：说明参数、返回值、算法逻辑
- 关键代码注释：解释复杂逻辑和设计决策

---

## 二、项目架构

### 整体结构
```
XianyuAutoAgent/
├── src/                        # 源代码主目录
│   ├── bot/                    # 核心机器人模块
│   │   └── xianyu_bot.py       # WebSocket主循环（已添加详细注释）
│   ├── agents/                 # 多专家Agent系统
│   │   ├── xianyu_agent.py     # 多专家Agent架构（已添加详细注释）
│   │   ├── rental_consultant_agent.py  # 租赁顾问Agent（已添加详细注释）
│   │   ├── smart_reply_manager.py      # 智能回复管理器（已添加详细注释）
│   │   └── intent_analyzer.py          # 意图分析器（已添加详细注释）
│   ├── core/                   # 核心基础模块
│   │   └── context_manager.py  # 对话上下文管理（已添加详细注释）
│   ├── knowledge/              # 知识库模块
│   │   └── feishu_sheet_reader.py  # 飞书表格读取器（已添加详细注释）
│   ├── utils/                  # 工具模块
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

**代码位置**：`src/agents/xianyu_agent.py`，IntentRouter类

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

## 四、核心技术原理详解（源码级）

> 本章深入讲解每个技术的本质原理，帮助你理解"为什么这样用"而不仅仅是"怎么用"。

### 4.1 WebSocket 实时通信

#### 技术本质

WebSocket 是一种**全双工通信协议**，解决了 HTTP 无法实时推送的问题。

**HTTP 的问题**：
```
客户端 → 服务器：我要消息（请求）
服务器 → 客户端：给你消息（响应）
// 然后连接就断开了，服务器无法主动推送
```

**WebSocket 的解决方案**：
```
客户端 ↔ 服务器：建立持久连接
// 双方都可以随时发送消息，无需重复建立连接
```

**对比表**：
| 特性 | HTTP | WebSocket |
|------|------|-----------|
| 通信方式 | 单向（客户端发起） | 双向（双方都能发） |
| 连接状态 | 无状态（每次请求独立） | 有状态（持久连接） |
| 实时性 | 差（需要轮询） | 好（服务器主动推送） |
| 开销 | 高（每次都要建立连接） | 低（复用同一连接） |

#### 核心 API 详解

**websockets 库核心函数**：

```python
import websockets

# 1. 建立连接
async with websockets.connect(
    uri,                    # WebSocket 服务器地址
    extra_headers=headers,  # 自定义请求头
    ping_interval=None,     # 禁用内置心跳（使用自定义心跳）
    close_timeout=10,       # 关闭超时时间（秒）
    open_timeout=30         # 打开超时时间（秒）
) as websocket:
    # 2. 发送消息
    await websocket.send(json.dumps(message))
    
    # 3. 接收消息
    async for message in websocket:
        data = json.loads(message)
```

#### 完整代码示例：WebSocket 客户端

```python
import asyncio
import json
import websockets
from datetime import datetime

async def websocket_client():
    """完整的 WebSocket 客户端示例"""
    
    # 1. 连接到服务器
    uri = "wss://echo.websocket.org"  # WebSocket 回声服务器
    async with websockets.connect(uri) as websocket:
        print(f"已连接到服务器: {uri}")
        
        # 2. 发送消息
        message = {
            "type": "chat",
            "content": "你好，这是测试消息",
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send(json.dumps(message))
        print(f"已发送: {message}")
        
        # 3. 接收回声
        response = await websocket.recv()
        print(f"收到回声: {response}")
        
        # 4. 持续监听
        async for message in websocket:
            print(f"收到消息: {message}")

# 运行
asyncio.run(websocket_client())
```

#### 在本项目中的应用

**文件位置**：`src/bot/xianyu_bot.py`

```python
# 建立 WebSocket 连接
async with websockets.connect(
    self.client.base_url,
    extra_headers=headers,
    ping_interval=None,  # 禁用内置心跳，使用自定义心跳
    close_timeout=10,
    open_timeout=30
) as websocket:
    self.ws = websocket
    await self.initialize_connection(websocket)
    
    # 接收消息
    async for message in websocket:
        message_data = json.loads(message)
        await self.handle_incoming_message(message_data, websocket)
```

#### 面试回答模板

> **问题**：WebSocket 和 HTTP 有什么区别？
> 
> **回答**：WebSocket 是全双工协议，建立连接后双方可以随时发送消息，而 HTTP 是单向的，每次请求都需要客户端发起。在我们的项目中，使用 WebSocket 长连接接收闲鱼平台的实时消息推送，配合心跳机制保持连接稳定。相比 HTTP 轮询，WebSocket 实时性更好、开销更低。

---

### 4.2 asyncio 异步编程

#### 技术本质

asyncio 是 Python 的**异步 IO 框架**，用于处理并发任务。

**核心概念**：
- **协程（Coroutine）**：用 `async def` 定义的函数，可以暂停执行等待 IO
- **事件循环（Event Loop）**：调度和执行协程的核心机制
- **任务（Task）**：对协程的封装，可以并发执行

**协程 vs 线程 vs 进程**：
| 特性 | 协程 | 线程 | 进程 |
|------|------|------|------|
| 切换开销 | 极低（用户态） | 中等（内核态） | 高（进程创建） |
| 并发方式 | 协作式（主动让出） | 抢占式（系统调度） | 抢占式 |
| 内存共享 | 共享 | 共享（需锁） | 需要 IPC |
| 适用场景 | IO 密集型 | IO 密集型 | CPU 密集型 |

#### 核心 API 详解

```python
import asyncio

# 1. 定义协程
async def my_coroutine():
    print("开始执行")
    await asyncio.sleep(1)  # 暂停 1 秒
    print("执行完成")

# 2. 创建任务
task1 = asyncio.create_task(my_coroutine())
task2 = asyncio.create_task(my_coroutine())

# 3. 并发执行
await asyncio.gather(task1, task2)

# 4. 超时控制
try:
    await asyncio.wait_for(my_coroutine(), timeout=5.0)
except asyncio.TimeoutError:
    print("执行超时")
```

#### 完整代码示例：异步任务调度

```python
import asyncio
from datetime import datetime

async def heartbeat():
    """心跳任务：每 30 秒发送一次"""
    while True:
        print(f"[{datetime.now()}] 发送心跳")
        await asyncio.sleep(30)

async def message_handler():
    """消息处理任务：持续接收消息"""
    while True:
        # 模拟接收消息
        await asyncio.sleep(5)
        print(f"[{datetime.now()}] 收到消息并处理")

async def token_refresh():
    """Token 刷新任务：每小时刷新一次"""
    while True:
        print(f"[{datetime.now()}] 刷新 Token")
        await asyncio.sleep(3600)

async def main():
    """主函数：启动所有并发任务"""
    # 创建任务
    heartbeat_task = asyncio.create_task(heartbeat())
    message_task = asyncio.create_task(message_handler())
    token_task = asyncio.create_task(token_refresh())
    
    try:
        # 并发执行所有任务
        await asyncio.gather(heartbeat_task, message_task, token_task)
    except asyncio.CancelledError:
        print("任务被取消")

# 运行主循环
asyncio.run(main())
```

#### 在本项目中的应用

**文件位置**：`src/bot/xianyu_bot.py`

```python
# 创建并发任务
self.heartbeat_task = asyncio.create_task(self.heartbeat_loop(websocket))
self.token_refresh_task = asyncio.create_task(self.token_refresh_loop())

# 心跳循环
async def heartbeat_loop(self, ws):
    while True:
        if current_time - self.last_heartbeat_time >= self.heartbeat_interval:
            await self.send_heartbeat(ws)
        await asyncio.sleep(1)  # 每秒检查一次
```

#### 面试回答模板

> **问题**：为什么用 asyncio 而不是多线程？
> 
> **回答**：asyncio 是协程模型，切换开销比线程低很多，适合 IO 密集型场景。我们的项目主要是等待网络 IO（WebSocket 消息、HTTP 请求），使用 asyncio 可以高效处理并发。而且 asyncio 的事件循环是单线程的，避免了多线程的竞态条件问题。

---

### 4.3 LLM 大语言模型调用

#### 技术本质

LLM（Large Language Model）是基于 **Transformer 架构**的语言模型，通过海量文本训练获得语言理解和生成能力。

**Transformer 核心机制**：
- **自注意力（Self-Attention）**：让模型关注输入序列中最重要的部分
- **位置编码（Positional Encoding）**：让模型理解词语顺序
- **多头注意力（Multi-Head Attention）**：从不同角度理解文本

**关键参数**：
| 参数 | 作用 | 典型值 |
|------|------|--------|
| temperature | 控制随机性（0=确定，1=随机） | 0.3-0.9 |
| max_tokens | 最大生成长度 | 100-2000 |
| top_p | 核采样（控制词汇多样性） | 0.8-1.0 |

#### 核心 API 详解

**OpenAI SDK 核心函数**：

```python
from openai import OpenAI

# 1. 初始化客户端
client = OpenAI(
    api_key="your-api-key",
    base_url="https://api.deepseek.com"  # 使用 DeepSeek API
)

# 2. 调用聊天完成 API
response = client.chat.completions.create(
    model="deepseek-chat",  # 模型名称
    messages=[
        {"role": "system", "content": "你是一个客服助手"},  # 系统提示词
        {"role": "user", "content": "你好"}                  # 用户消息
    ],
    temperature=0.4,  # 温度参数
    max_tokens=500,   # 最大生成长度
    top_p=0.8         # 核采样
)

# 3. 获取回复
reply = response.choices[0].message.content
```

#### 完整代码示例：调用 DeepSeek API

```python
from openai import OpenAI
import os

def chat_with_llm(user_message: str, system_prompt: str = "") -> str:
    """
    与 LLM 对话的完整示例
    
    参数：
        user_message: 用户消息
        system_prompt: 系统提示词
        
    返回：
        LLM 生成的回复
    """
    # 1. 初始化客户端
    client = OpenAI(
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("MODEL_BASE_URL", "https://api.deepseek.com")
    )
    
    # 2. 构建消息链
    messages = [
        {"role": "system", "content": system_prompt or "你是一个友好的客服助手"},
        {"role": "user", "content": user_message}
    ]
    
    # 3. 调用 LLM
    try:
        response = client.chat.completions.create(
            model=os.getenv("MODEL_NAME", "deepseek-chat"),
            messages=messages,
            temperature=0.4,
            max_tokens=500,
            top_p=0.8
        )
        
        # 4. 返回回复
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"调用 LLM 失败: {e}")
        return "抱歉，我遇到了一些问题，请稍后再试"

# 使用示例
if __name__ == "__main__":
    reply = chat_with_llm(
        user_message="这个商品多少钱？",
        system_prompt="你是一个闲鱼客服，回复要友好简洁"
    )
    print(reply)
```

#### 在本项目中的应用

**文件位置**：`src/agents/xianyu_agent.py`

```python
# 初始化 OpenAI 客户端
self.client = OpenAI(
    api_key=os.getenv("API_KEY") or os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("MODEL_BASE_URL", "https://api.deepseek.com"),
)

# 调用 LLM 生成回复
response = self.client.chat.completions.create(
    model=os.getenv("MODEL_NAME", "qwen-max"),
    messages=messages,
    temperature=dynamic_temp,  # 动态温度
    max_tokens=500,
    top_p=0.8
)
return response.choices[0].message.content
```

#### 面试回答模板

> **问题**：LLM 的 Temperature 参数是什么？
> 
> **回答**：Temperature 控制生成文本的随机性。值越小（如 0.3），回复越确定、越保守；值越大（如 0.9），回复越随机、越有创意。在我们的项目中，议价场景使用动态温度：第一次砍价用 0.3（态度坚定），多次砍价后逐渐升高到 0.9（更容易让步），模拟真实卖家的心理变化。

---

### 4.4 消息安全与去重

#### 技术本质

**SHA-256 哈希算法**：
- 将任意长度的输入转换为固定 256 位（32 字节）的输出
- 单向不可逆：无法从哈希值反推原文
- 碰撞性极低：不同输入几乎不可能产生相同哈希值

**Base64 编码**：
- 将二进制数据转换为 ASCII 字符串
- 用于在文本协议中传输二进制数据
- 编码后体积增加约 33%

#### 核心 API 详解

```python
import hashlib
import base64

# SHA-256 哈希
message = "你好世界"
hash_value = hashlib.sha256(message.encode('utf-8')).hexdigest()
print(f"SHA-256: {hash_value}")  # 64 位十六进制字符串

# Base64 编码/解码
original = "你好世界"
encoded = base64.b64encode(original.encode('utf-8')).decode('utf-8')
decoded = base64.b64decode(encoded).decode('utf-8')
print(f"编码: {encoded}")
print(f"解码: {decoded}")
```

#### 完整代码示例：消息去重实现

```python
import hashlib
import time
from typing import Set, Dict

class MessageDeduplicator:
    """消息去重器"""
    
    def __init__(self, ttl: int = 300, max_size: int = 1000):
        """
        初始化去重器
        
        参数：
            ttl: 消息存活时间（秒）
            max_size: 最大存储消息数
        """
        self.processed_messages: Set[str] = set()
        self.message_timestamps: Dict[str, float] = {}
        self.ttl = ttl
        self.max_size = max_size
    
    def generate_message_id(self, chat_id: str, user_id: str, 
                           content: str, timestamp: int) -> str:
        """
        生成消息唯一标识
        
        使用 SHA-256 哈希算法，将消息的关键信息转换为唯一标识
        """
        # 标准化消息内容（去除空格和换行符差异）
        normalized_content = content.strip().replace('\n', ' ').replace('\r', '')
        
        # 拼接关键信息
        message_content = f"{chat_id}_{user_id}_{normalized_content}_{timestamp}"
        
        # 生成 SHA-256 哈希
        return hashlib.sha256(message_content.encode('utf-8')).hexdigest()
    
    def is_duplicate(self, message_id: str) -> bool:
        """
        检查是否为重复消息
        
        返回：
            True 表示重复消息，False 表示新消息
        """
        current_time = time.time()
        
        # 1. 清理过期消息
        self._cleanup_expired(current_time)
        
        # 2. 检查是否已处理
        if message_id in self.processed_messages:
            return True
        
        # 3. 记录新消息
        self.processed_messages.add(message_id)
        self.message_timestamps[message_id] = current_time
        
        return False
    
    def _cleanup_expired(self, current_time: float):
        """清理过期消息"""
        expired_messages = [
            msg_id for msg_id, timestamp in self.message_timestamps.items()
            if current_time - timestamp > self.ttl
        ]
        
        for msg_id in expired_messages:
            self.processed_messages.discard(msg_id)
            del self.message_timestamps[msg_id]
        
        # 限制集合大小
        if len(self.processed_messages) > self.max_size:
            oldest_messages = sorted(
                self.message_timestamps.items(), 
                key=lambda x: x[1]
            )[:100]
            for msg_id, _ in oldest_messages:
                self.processed_messages.discard(msg_id)
                del self.message_timestamps[msg_id]

# 使用示例
if __name__ == "__main__":
    deduplicator = MessageDeduplicator()
    
    # 模拟消息
    msg_id = deduplicator.generate_message_id(
        chat_id="123456",
        user_id="user_001",
        content="你好",
        timestamp=1234567890
    )
    
    # 检查重复
    print(f"第一次: {deduplicator.is_duplicate(msg_id)}")  # False
    print(f"第二次: {deduplicator.is_duplicate(msg_id)}")  # True
```

#### 在本项目中的应用

**文件位置**：`src/bot/xianyu_bot.py`

```python
# 生成消息 ID
def _generate_message_id(self, chat_id, send_user_id, send_message, create_time):
    import hashlib
    normalized_message = send_message.strip().replace('\n', ' ').replace('\r', '')
    message_content = f"{chat_id}_{send_user_id}_{normalized_message}_{create_time}"
    return hashlib.sha256(message_content.encode('utf-8')).hexdigest()

# 检查重复消息
def _is_duplicate_message(self, message_id):
    # 清理过期消息
    # 检查是否已处理
    # 记录新消息
```

#### 面试回答模板

> **问题**：如何设计消息去重机制？
> 
> **回答**：我们使用 SHA-256 哈希算法生成消息唯一标识，包含聊天 ID、用户 ID、消息内容和时间戳。然后用 Set 存储已处理的消息 ID，配合 TTL 过期机制清理旧消息。当收到消息时，先检查是否已处理，避免重复回复。SHA-256 碰撞性极低，能有效识别重复消息。

---

### 4.5 OAuth2 认证与 HTTP API

#### 技术本质

**OAuth2 认证流程**：
1. 客户端向授权服务器请求授权
2. 用户登录并授权
3. 授权服务器返回授权码
4. 客户端用授权码换取访问令牌
5. 客户端使用访问令牌访问资源

**Token 类型**：
- Access Token：访问令牌，用于访问受保护资源
- Refresh Token：刷新令牌，用于获取新的 Access Token

#### 核心 API 详解

```python
import requests

# 1. 创建会话（自动管理 Cookie）
session = requests.Session()

# 2. 发送 POST 请求
response = session.post(
    url="https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": "xxx", "app_secret": "xxx"},
    timeout=10
)

# 3. 处理响应
result = response.json()
access_token = result.get("tenant_access_token")

# 4. 使用令牌访问资源
headers = {"Authorization": f"Bearer {access_token}"}
response = session.get(url, headers=headers)
```

#### 完整代码示例：飞书 API 调用

```python
import requests
import json

class FeishuClient:
    """飞书 API 客户端"""
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = None
        self.session = requests.Session()
    
    def _get_access_token(self) -> str:
        """获取访问令牌"""
        if self.access_token:
            return self.access_token
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        response = self.session.post(
            url,
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=10
        )
        
        result = response.json()
        self.access_token = result.get("tenant_access_token")
        return self.access_token
    
    def get_sheet_data(self, spreadsheet_token: str, sheet_id: str) -> dict:
        """获取表格数据"""
        access_token = self._get_access_token()
        
        url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{sheet_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = self.session.get(url, headers=headers, timeout=15)
        return response.json()

# 使用示例
if __name__ == "__main__":
    client = FeishuClient(
        app_id="your-app-id",
        app_secret="your-app-secret"
    )
    data = client.get_sheet_data("spreadsheet-token", "sheet-id")
    print(json.dumps(data, indent=2, ensure_ascii=False))
```

#### 在本项目中的应用

**文件位置**：`src/knowledge/feishu_sheet_reader.py`

```python
# 获取访问令牌
def _get_access_token(self) -> str:
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": self.app_id, "app_secret": self.app_secret}
    response = self.session.post(url, json=data, timeout=10)
    result = response.json()
    self.access_token = result.get('tenant_access_token')
    return self.access_token

# 获取表格数据
def _get_sheet_data(self) -> Dict:
    access_token = self._get_access_token()
    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{self.spreadsheet_token}/values/{self.sheet_id}"
    headers = {'Authorization': f'Bearer {access_token}'}
    response = self.session.get(url, headers=headers, timeout=15)
    return response.json()
```

#### 面试回答模板

> **问题**：OAuth2 认证流程是怎样的？
> 
> **回答**：OAuth2 是一种授权框架。在我们的项目中，使用飞书的 OAuth2 认证：首先用 app_id 和 app_secret 向飞书服务器请求访问令牌，获得 tenant_access_token，然后用这个令牌调用飞书 API 获取表格数据。Token 有有效期，需要定期刷新。

---

## 五、消息处理流程

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

## 六、面试介绍技巧

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

## 七、可能被问到的问题

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

### Q7: WebSocket 和 HTTP 有什么区别？
**回答**：WebSocket 是全双工协议，建立连接后双方可以随时发送消息，而 HTTP 是单向的，每次请求都需要客户端发起。WebSocket 连接是持久的，开销更低；HTTP 是无状态的，每次请求都要建立新连接。在我们的项目中，使用 WebSocket 接收闲鱼平台的实时消息推送。

### Q8: 为什么用 asyncio 而不是多线程？
**回答**：asyncio 是协程模型，切换开销比线程低很多，适合 IO 密集型场景。我们的项目主要是等待网络 IO（WebSocket 消息、HTTP 请求），使用 asyncio 可以高效处理并发。而且 asyncio 的事件循环是单线程的，避免了多线程的竞态条件问题。

### Q9: LLM 的 Temperature 参数是什么？
**回答**：Temperature 控制生成文本的随机性。值越小（如 0.3），回复越确定、越保守；值越大（如 0.9），回复越随机、越有创意。在我们的项目中，议价场景使用动态温度：第一次砍价用 0.3（态度坚定），多次砍价后逐渐升高到 0.9（更容易让步）。

### Q10: 如何设计消息去重机制？
**回答**：我们使用 SHA-256 哈希算法生成消息唯一标识，包含聊天 ID、用户 ID、消息内容和时间戳。然后用 Set 存储已处理的消息 ID，配合 TTL 过期机制清理旧消息。当收到消息时，先检查是否已处理，避免重复回复。

### Q11: OAuth2 认证流程是怎样的？
**回答**：OAuth2 是一种授权框架。在我们的项目中，使用飞书的 OAuth2 认证：首先用 app_id 和 app_secret 向飞书服务器请求访问令牌，获得 tenant_access_token，然后用这个令牌调用飞书 API 获取表格数据。Token 有有效期，需要定期刷新。

### Q12: SHA-256 和 MD5 有什么区别？
**回答**：SHA-256 生成 256 位哈希值，MD5 生成 128 位。SHA-256 碰撞性更低、更安全，但计算稍慢。MD5 已被证明存在碰撞漏洞，不适合安全场景。在我们的项目中，消息去重使用 SHA-256，API 签名使用 MD5（闲鱼平台要求）。

---

## 八、项目技术亮点总结

| 设计 | 亮点 | 一句话解释 |
|------|------|-----------|
| **混合路由** | 规则优先+LLM兜底 | 快的先用规则，不确定的再用AI |
| **动态温度** | temperature随议价轮次递增 | 越砍越松口，模拟真实卖家心理 |
| **双重安全** | 敏感词前置+安全过滤后置 | 前门拦敏感内容，后门拦平台违规 |
| **上下文感知** | 实体提取+TTL过期+多位置管理 | 记住你说过的关键信息，但有保质期 |
| **弹性重连** | 指数退避+随机抖动 | 断了不要紧，越来越耐心地重连 |

---

## 九、关键代码位置速查

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

## 十、项目数据

- **测试文件**：25个
- **核心依赖**：8个主要库
- **环境配置**：105行配置项
- **敏感词分类**：6大类，80+关键词
- **Agent类型**：5种专家Agent

---

> **提示**：面试前重点复习多专家Agent系统、WebSocket消息处理、飞书知识库集成这三个部分，这些是最可能被面试官深入提问的内容。
