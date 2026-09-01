# 🚀 Xianyu AutoAgent - 重构版本

专为闲鱼平台打造的AI值守解决方案，实现闲鱼平台7×24小时自动化值守，支持多专家协同决策、智能议价和上下文感知对话。

## 🎯 重构亮点

- **模块化设计** - 清晰的代码结构，易于维护和扩展
- **功能分离** - 核心逻辑、智能体、工具模块独立
- **简化使用** - 统一的命令行接口
- **代码优化** - 删除冗余代码，提升性能

## 📁 项目结构

```
XianyuAutoAgent-main11/
├── xianyu_bot.py          # 主程序入口
├── requirements.txt        # 依赖包列表
├── .env                   # 环境变量配置
├── chat_history.json      # 聊天记录数据库
├── prompts/               # AI提示词模板
│   ├── classify_prompt.txt
│   ├── price_prompt.txt
│   ├── tech_prompt.txt
│   └── default_prompt.txt
├── core/                  # 核心模块
│   ├── __init__.py
│   ├── xianyu_client.py   # 闲鱼客户端
│   └── context_manager.py # 上下文管理器
├── agents/                # 智能体模块
│   ├── __init__.py
│   └── xianyu_agent.py    # 多专家Agent系统
├── utils/                 # 工具模块
│   ├── __init__.py
│   ├── xianyu_utils.py    # 闲鱼工具函数
│   └── xianyu_apis.py     # API封装
└── tools/                 # 命令行工具
    ├── __init__.py
    ├── cli.py             # 命令行接口
    ├── chat_exporter.py   # 聊天记录导出
    └── cookie_refresher.py # Cookie刷新工具
```

## 🚀 快速开始

### 环境要求
- Python 3.8+
- 有效的闲鱼账号
- API密钥（支持OpenAI兼容接口）

### 安装步骤

1. **克隆仓库**
```bash
git clone <repository-url>
cd XianyuAutoAgent-main11
```

2. **安装依赖**
```bash
pip install -r requirements.txt
playwright install chromium
```

3. **配置环境变量**
创建 `.env` 文件：
```env
# 必填配置
API_KEY=你的API密钥
COOKIES_STR=闲鱼登录cookies
MODEL_BASE_URL=模型API地址
MODEL_NAME=模型名称

# 可选配置
LOG_LEVEL=INFO
HEARTBEAT_INTERVAL=30
TOKEN_REFRESH_INTERVAL=3600
```

### 使用方法

#### 1. 首次使用
```bash
# 启动机器人，会自动引导获取cookies
python xianyu_bot.py
```

#### 2. 刷新Cookies
```bash
# 手动刷新cookies
python tools/cli.py refresh-cookies

# 自动模式刷新
python tools/cli.py refresh-cookies --auto-mode
```

#### 3. 导出聊天记录
```bash
# 导出所有聊天记录
python tools/cli.py export-all

# 导出会话摘要
python tools/cli.py export-summary

# 列出所有会话
python tools/cli.py list-chats

# 显示统计信息
python tools/cli.py stats

# 导出特定会话
python tools/cli.py export-chat <chat_id>
```

#### 4. 独立查询工具 (无需启动机器人)
```bash
# 列出所有会话
python tools/chat_query.py list

# 显示统计信息
python tools/chat_query.py stats

# 搜索聊天记录
python tools/chat_query.py search <关键词>

# 查看会话详情
python tools/chat_query.py view <会话ID>

# 导出所有聊天记录到CSV
python tools/chat_query.py export
```

#### 5. 使用启动菜单 (推荐)
```bash
# 启动统一菜单界面
python start_menu.py
```

启动菜单提供以下功能：
- 启动闲鱼机器人
- 聊天记录查询工具
- 导出聊天记录
- 刷新Cookies
- 查看会话统计
- 列出所有会话
- 导出会话摘要

## 🤖 智能体系统

程序采用多专家Agent架构：

- **`ClassifyAgent`** - 意图分类器，识别用户消息类型
- **`PriceAgent`** - 价格专家，处理议价和价格谈判
- **`TechAgent`** - 技术专家，回答技术参数问题
- **`DefaultAgent`** - 默认客服，处理其他咨询

## 🔧 核心特性

### 智能对话引擎
- **上下文感知** - 完整的对话历史管理
- **专家路由** - 基于意图识别的动态分发
- **安全过滤** - 防止敏感信息泄露

### 技术架构
- **WebSocket长连接** - 实时接收闲鱼消息
- **心跳机制** - 维持连接稳定性
- **Token自动刷新** - 处理会话过期
- **指数退避重连** - 网络异常自动恢复

### 业务功能
- **自动回复** - 7×24小时智能值守
- **议价系统** - 阶梯降价策略
- **技术支持** - 网络搜索整合
- **数据导出** - 完整的聊天记录管理

## ⚙️ 配置说明

### 环境变量
- `API_KEY` - 大模型API密钥
- `COOKIES_STR` - 闲鱼登录cookies
- `MODEL_BASE_URL` - 模型API地址
- `MODEL_NAME` - 模型名称
- `LOG_LEVEL` - 日志级别（DEBUG/INFO/WARNING/ERROR）

### 提示词定制
可以通过编辑 `prompts/` 目录下的文件来自定义各个专家的提示词。

## 🛠️ 开发说明

### 模块说明
- **core/** - 核心业务逻辑
- **agents/** - AI智能体系统
- **utils/** - 工具函数和API封装
- **tools/** - 命令行工具和辅助功能

### 扩展开发
- 添加新的Agent：在 `agents/xianyu_agent.py` 中继承 `BaseAgent`
- 修改路由规则：在 `IntentRouter` 类中添加新的意图识别规则
- 自定义提示词：编辑 `prompts/` 目录下的对应文件

## ⚠️ 注意事项

- 本项目仅供学习与交流使用
- 请遵守闲鱼平台的使用规则
- 注意保护个人隐私和账号安全
- 定期检查cookies有效性

## 📞 技术支持

如有问题请参考：
- 查看日志文件了解详细错误信息
- 检查环境变量配置是否正确
- 确保网络连接正常
- 验证cookies是否有效

---

**重构完成** - 代码结构更清晰，功能更完善，使用更便捷！