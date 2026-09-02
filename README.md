# XianyuAutoAgent

> 闲鱼AI自动值守客服机器人 - 7x24小时智能回复买家消息

---

## 项目简介

XianyuAutoAgent 是一个为闲鱼（Goofish）二手交易平台打造的AI自动值守客服机器人。通过WebSocket长连接实时监听买家消息，利用大语言模型（DeepSeek）实现多专家协同决策、智能议价和上下文感知对话。

### 核心特性

- **多专家Agent系统**：不同问题交给不同专家处理（价格、技术、租赁等）
- **智能议价**：动态温度策略，模拟真实卖家心理
- **实时响应**：WebSocket长连接，消息秒级响应
- **飞书知识库**：集成飞书表格，实时查询设备库存
- **人工接管**：随时切换人工/自动模式

---

## 项目结构

```
XianyuAutoAgent/
├── src/                        # 源代码主目录
│   ├── bot/                    # 核心机器人模块
│   │   ├── xianyu_bot.py       # 主入口（WebSocket、消息处理）
│   │   └── trading_analyzer.py # 交易数据分析
│   │
│   ├── agents/                 # 多专家Agent系统
│   │   ├── xianyu_agent.py     # Agent路由核心
│   │   ├── rental_consultant_agent.py # 租赁顾问
│   │   ├── smart_reply_manager.py # 智能回复管理
│   │   └── intent_analyzer.py  # 意图分析
│   │
│   ├── core/                   # 核心基础模块
│   │   ├── xianyu_client.py    # 闲鱼客户端
│   │   └── context_manager.py  # 上下文管理
│   │
│   ├── utils/                  # 工具模块
│   │   ├── xianyu_utils.py     # 工具集（加解密、签名）
│   │   ├── xianyu_apis.py      # 闲鱼API封装
│   │   └── sensitive_keywords.py # 敏感词检测
│   │
│   ├── knowledge/              # 知识库模块
│   │   └── feishu_sheet_reader.py # 飞书表格读取
│   │
│   ├── crawler/                # 爬虫模块
│   │   └── tools/              # 爬虫工具集
│   │
│   ├── analysis/               # 分析模块
│   │   ├── chat_analyzer.py    # 聊天分析
│   │   ├── profit_optimizer.py # 利润优化
│   │   └── report_generator.py # 报告生成
│   │
│   └── prompts/                # 提示词模板
│       ├── classify_prompt.txt
│       ├── price_prompt.txt
│       ├── tech_prompt.txt
│       └── default_prompt.txt
│
├── tests/                      # 测试文件
├── scripts/                    # 辅助脚本
├── docs/                       # 文档
│
├── .env                        # 环境变量配置
├── requirements.txt            # Python依赖
├── start_menu.py               # 启动入口
├── Dockerfile                  # Docker构建文件
└── docker-compose.yml          # Docker编排文件
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，并填入以下配置：

```env
# DeepSeek API配置
API_KEY=your_api_key
MODEL_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat

# 闲鱼Cookies
COOKIES_STR=your_cookies

# 飞书配置（可选）
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
```

### 3. 启动机器人

```bash
python start_menu.py
```

---

## 技术栈

- **Python 3.8+**
- **OpenAI SDK** - LLM API调用
- **websockets** - WebSocket长连接
- **playwright** - 浏览器自动化
- **requests** - HTTP请求
- **飞书开放平台API** - 知识库集成

---

## 核心架构

### 多专家Agent系统

```
用户消息 → 意图路由
           ├── 租赁关键词 → 租赁顾问Agent
           ├── 技术关键词 → 技术专家Agent
           ├── 价格关键词 → 议价专家Agent
           └── 兜底分类 → 默认客服Agent
```

### 动态议价策略

```python
temperature = min(0.3 + bargain_count * 0.15, 0.9)
```

- 第一次砍价（0.3）：态度坚定
- 多次砍价（0.9）：高度灵活

---

## 面试准备

详见 `docs/PROJECT_INTERVIEW_GUIDE.md`

---

## 许可证

GNU GPLv3 License
