# XianyuAutoAgent 项目结构

> 本文档详细描述项目的目录结构和文件功能，帮助你快速了解项目组织方式。

---

## 一、项目根目录

```
XianyuAutoAgent/
│
├── 📄 核心配置文件
│   ├── .env                          # 环境变量配置（API密钥、数据库配置等）
│   ├── .gitignore                    # Git忽略文件配置
│   ├── .dockerignore                 # Docker忽略文件配置
│   ├── requirements.txt              # Python依赖包列表
│   ├── Dockerfile                    # Docker镜像构建文件（多阶段构建）
│   ├── docker-compose.yml            # Docker Compose编排文件
│   └── LICENSE                       # 开源许可证（GNU GPLv3）
│
├── 🚀 启动入口
│   └── start_menu.py                 # 统一启动菜单（7大功能入口）
│
└── 📚 文档文件
    └── README.md                     # 项目说明文档
```

---

## 二、源代码主目录 (`src/`)

> 所有业务逻辑代码都在这里。

```
src/
│
├── 🤖 核心机器人模块 (`bot/`)
│   ├── __init__.py                  # 模块初始化
│   ├── xianyu_bot.py                # 主入口文件（46KB）
│   │                              # 功能：
│   │                              #   - WebSocket长连接管理
│   │                              #   - 消息接收和处理
│   │                              #   - 心跳维持机制
│   │                              #   - 自动重连逻辑
│   │                              #   - 人工/自动模式切换
│   │
│   └── trading_analyzer.py          # 交易数据分析器（16KB）
│                                    # 功能：
│                                    #   - 议价行为分析
│                                    #   - 利润优化建议
│                                    #   - 交易报告生成
│
├── 🧠 多专家Agent系统 (`agents/`)
│   ├── __init__.py                  # 模块初始化
│   ├── xianyu_agent.py              # 核心Agent路由（19KB）
│   │                              # 功能：
│   │                              #   - IntentRouter意图路由器
│   │                              #   - 多专家协调机制
│   │                              #   - 四级路由策略
│   │
│   ├── rental_consultant_agent.py   # 租赁顾问Agent（56KB）
│   │                              # 功能：
│   │                              #   - 设备租赁咨询
│   │                              #   - 库存状态查询
│   │                              #   - 飞书知识库集成
│   │
│   ├── smart_reply_manager.py       # 智能回复管理器（9KB）
│   │                              # 功能：
│   │                              #   - 消息路由调度
│   │                              #   - Agent协调
│   │                              #   - 决策输出
│   │
│   └── intent_analyzer.py           # 意图分析器（24KB）
│                                    # 功能：
│                                    #   - 关键词快速匹配
│                                    #   - LLM语义分析
│                                    #   - 上下文感知检查
│                                    #   - 决策日志记录
│
├── 🔧 核心基础模块 (`core/`)
│   ├── __init__.py                  # 模块初始化
│   ├── xianyu_client.py             # 闲鱼客户端（3KB）
│   │                              # 功能：
│   │                              #   - WebSocket连接管理
│   │                              #   - Token管理
│   │
│   └── context_manager.py           # 对话上下文管理器（14KB）
│                                    # 功能：
│                                    #   - 对话历史存储（JSON）
│                                    #   - 实体提取（位置、设备、时间）
│                                    #   - 多轮对话维护
│                                    #   - TTL过期机制
│
├── 🛠️ 工具模块 (`utils/`)
│   ├── __init__.py                  # 模块初始化
│   ├── xianyu_utils.py              # 闲鱼工具集（10KB）
│   │                              # 功能：
│   │                              #   - MessagePack解码器
│   │                              #   - Base64解码
│   │                              #   - Cookie解析
│   │                              #   - 签名生成
│   │
│   ├── xianyu_apis.py               # 闲鱼API封装（15KB）
│   │                              # 功能：
│   │                              #   - 登录验证
│   │                              #   - Token获取
│   │                              #   - 商品信息查询
│   │                              #   - 聊天列表获取
│   │
│   └── sensitive_keywords.py        # 敏感词检测器（7KB）
│                                    # 功能：
│                                    #   - 6大类敏感词库（80+关键词）
│                                    #   - 例外白名单
│                                    #   - 分类返回检测结果
│
├── 📊 知识库模块 (`knowledge/`)
│   ├── __init__.py                  # 模块初始化
│   └── feishu_sheet_reader.py       # 飞书表格读取器（27KB）
│                                    # 功能：
│                                    #   - OAuth2认证流程
│                                    #   - 表格数据查询
│                                    #   - 设备库存状态管理
│                                    #   - 日期范围查询
│                                    #   - 位置/设备过滤
│
├── 🕷️ 爬虫模块 (`crawler/`)
│   ├── __init__.py                  # 模块初始化
│   └── tools/                       # 爬虫工具集
│       ├── __init__.py              # 模块初始化
│       ├── batch_user_crawler.py    # 批量用户爬虫（79KB）
│       ├── optimized_batch_crawler.py # 优化版批量爬虫（55KB）
│       ├── enhanced_chat_crawler.py # 增强版聊天爬虫（50KB）
│       ├── direct_user_extractor.py # 直接用户提取器（24KB）
│       ├── merged_get_chat_list_users.py # 合并获取聊天列表用户（22KB）
│       ├── analyze_chat_structure.py # 聊天结构分析（11KB）
│       ├── chat_query.py            # 聊天查询（11KB）
│       ├── cookie_refresher.py      # Cookie刷新器（11KB）
│       ├── chat_exporter.py         # 聊天导出器（8KB）
│       └── manual_cookies_updater.py # 手动Cookie更新器（1KB）
│
├── 📈 分析模块 (`analysis/`)
│   ├── __init__.py                  # 模块初始化
│   ├── chat_analyzer.py             # 聊天记录分析器（20KB）
│   │                              # 功能：
│   │                              #   - 聊天记录解析
│   │                              #   - 行为模式分析
│   │                              #   - 统计数据生成
│   │
│   ├── profit_optimizer.py          # 利润优化器（20KB）
│   │                              # 功能：
│   │                              #   - 定价策略分析
│   │                              #   - 利润最大化建议
│   │
│   └── report_generator.py          # 报告生成器（19KB）
│                                    # 功能：
│                                    #   - 分析报告生成
│                                    #   - 可视化图表
│
└── 📝 提示词模板 (`prompts/`)
    ├── __init__.py                  # 模块初始化
    ├── classify_prompt.txt          # 意图分类提示词（741B）
    │                              # 功能：
    │                              #   - 指导LLM进行意图分类
    │
    ├── price_prompt.txt             # 议价专家提示词（2KB）
    │                              # 功能：
    │                              #   - 指导LLM进行议价对话
    │
    ├── tech_prompt.txt              # 技术专家提示词（1KB）
    │                              # 功能：
    │                              #   - 指导LLM回答技术问题
    │
    └── default_prompt.txt           # 默认客服提示词（2KB）
                                    # 功能：
                                    #   - 指导LLM进行通用客服对话
```

---

## 三、测试模块 (`tests/`)

```
tests/
│
├── 🧪 基础功能测试
│   ├── test_basic_functionality.py  # 基础功能测试
│   ├── test_chat.py                 # 聊天功能测试
│   ├── test_components.py           # 组件集成测试
│   └── test_encoding.py             # 编码处理测试
│
├── 🧪 上下文管理测试
│   ├── test_context_functionality.py # 上下文功能测试
│   └── test_nickname_fix.py         # 昵称识别修复测试
│
├── 🧪 飞书集成测试
│   ├── test_feishu_data.py          # 飞书数据测试
│   ├── test_feishu_detailed.py      # 飞书详细功能测试
│   └── test_feishu_functionality.py # 飞书功能测试
│
├── 🧪 价格相关测试
│   ├── test_price_calculation.py    # 价格计算测试
│   └── test_price_explanation.py    # 价格解释测试
│
├── 🧪 查询功能测试
│   ├── test_location_query.py       # 位置查询测试
│   ├── test_month_query.py          # 月份查询测试
│   └── test_multi_location.py       # 多位置查询测试
│
├── 🧪 智能回复测试
│   ├── test_smart_reply.py          # 智能回复系统测试
│   └── test_openai_client.py        # OpenAI客户端测试
│
├── 🧪 框架和工具
│   ├── test_framework.py            # 完整测试框架（25KB）
│   │                              # 功能：
│   │                              #   - 批量自动化测试
│   │                              #   - 交互式手动测试
│   │                              #   - 测试报告生成
│   │
│   ├── conversation_test.py         # 对话流程测试（50KB）
│   ├── interactive_feishu_bot.py    # 交互式飞书机器人测试
│   └── interactive_test.py          # 交互式测试工具
│
└── 🧪 其他测试
    ├── test_fix.py                  # 修复测试
    ├── test_minimal.py              # 最小化测试
    ├── test_non_interactive.py      # 非交互式测试
    └── test_simple.py               # 简单测试
```

---

## 四、其他目录

```
├── scripts/                         # 🛠️ 辅助脚本目录
│   ├── chrome_cookie_manager.py     # Chrome Cookie管理器
│   ├── correct_scroll_direction.py  # 滚动方向修正工具
│   ├── diagnose_chat_page.py        # 聊天页面诊断工具
│   ├── feishu_query_demo.py         # 飞书查询演示
│   └── get_users_no_scroll.py       # 无滚动获取用户
│
├── docs/                            # 📚 文档目录
│   ├── README.md                    # 项目说明文档
│   └── [其他文档文件]
│
├── .cache/                          # 📦 缓存目录（运行时生成）
│   ├── exports/                     # 导出数据
│   ├── fast_batch_chats/            # 快速批量聊天
│   └── optimized_batch_chats/       # 优化批量聊天
│
└── images/                          # 🖼️ 图片资源目录
```

---

## 五、核心文件大小分析

| 文件 | 大小 | 重要性 | 说明 |
|------|------|--------|------|
| `xianyu_bot.py` | 46KB | ⭐⭐⭐⭐⭐ | 主入口，WebSocket消息处理核心 |
| `rental_consultant_agent.py` | 56KB | ⭐⭐⭐⭐⭐ | 租赁顾问Agent，最复杂的Agent |
| `intent_analyzer.py` | 24KB | ⭐⭐⭐⭐ | 意图分析，LLM语义理解核心 |
| `start_menu.py` | 25KB | ⭐⭐⭐ | 统一启动入口 |
| `trading_analyzer.py` | 16KB | ⭐⭐⭐ | 交易数据分析 |
| `xianyu_apis.py` | 15KB | ⭐⭐⭐ | 闲鱼API封装 |
| `context_manager.py` | 14KB | ⭐⭐⭐ | 对话上下文管理 |
| `feishu_sheet_reader.py` | 27KB | ⭐⭐⭐⭐ | 飞书知识库集成 |
| `xianyu_agent.py` | 19KB | ⭐⭐⭐⭐ | Agent路由核心 |

---

## 六、模块依赖关系

```
start_menu.py (启动入口)
    │
    └──→ src/ (源代码主目录)
            │
            ├──→ bot/ (核心机器人模块)
            │       ├──→ xianyu_bot.py (主入口)
            │       └──→ trading_analyzer.py (交易分析)
            │
            ├──→ agents/ (多专家Agent系统)
            │       ├──→ xianyu_agent.py (路由)
            │       ├──→ rental_consultant_agent.py (租赁顾问)
            │       ├──→ smart_reply_manager.py (智能回复)
            │       └──→ intent_analyzer.py (意图分析)
            │
            ├──→ core/ (核心模块)
            │       ├──→ xianyu_client.py (客户端)
            │       └──→ context_manager.py (上下文)
            │
            ├──→ utils/ (工具)
            │       ├──→ xianyu_utils.py (工具集)
            │       ├──→ xianyu_apis.py (API封装)
            │       └──→ sensitive_keywords.py (敏感词)
            │
            ├──→ knowledge/ (知识库)
            │       └──→ feishu_sheet_reader.py (表格读取)
            │
            ├──→ crawler/ (爬虫)
            │       └──→ tools/ (爬虫工具)
            │
            ├──→ analysis/ (分析)
            │       ├──→ chat_analyzer.py (聊天分析)
            │       ├──→ profit_optimizer.py (利润优化)
            │       └──→ report_generator.py (报告生成)
            │
            └──→ prompts/ (提示词)
                    ├──→ classify_prompt.txt
                    ├──→ price_prompt.txt
                    ├──→ tech_prompt.txt
                    └──→ default_prompt.txt
```

---

## 七、快速导航

### 想了解消息处理流程？
→ 查看 `src/bot/xianyu_bot.py`

### 想了解多专家Agent系统？
→ 查看 `src/agents/xianyu_agent.py`

### 想了解智能回复机制？
→ 查看 `src/agents/smart_reply_manager.py`

### 想了解飞书知识库集成？
→ 查看 `src/knowledge/feishu_sheet_reader.py`

### 想了解对话上下文管理？
→ 查看 `src/core/context_manager.py`

### 想了解项目测试？
→ 查看 `tests/test_framework.py`（完整测试框架）

---

## 八、项目统计

- **总文件数**：100+ 个文件
- **核心Python文件**：20+ 个
- **测试文件**：25 个
- **提示词模板**：4 个
- **配置文件**：5 个（.env, requirements.txt, Dockerfile等）

---

> **提示**：建议先阅读 `README.md` 了解项目整体，然后根据面试准备指南重点学习核心模块。
