# harness-frame-action

一个用于学习与对比各种 **Agent Harness 框架** 的实验性项目。

## 项目背景

随着 LLM Agent 生态的发展，涌现出多种"智能体编排框架/运行时"（harness）。它们在工具调用循环、上下文管理、子代理、沙箱执行等方面的设计思路各不相同。本项目通过在同一仓库内为每种框架编写最小可运行示例，来理解它们的设计差异与适用场景。

## 学习目标

- 理解 Agent 的本质循环：`LLM 输出 → 工具调用 → 结果回填 → 继续推理`
- 对比不同框架在以下维度上的取舍：
  - 工具/Tool 的定义与注册方式
  - 多轮循环与终止条件
  - 上下文管理与压缩策略
  - 子代理 / 多 Agent 协作
  - 执行环境（本地、容器、沙箱）
- 最终能够判断：什么场景适合直接调用 API，什么场景需要引入 harness 框架

## 覆盖的框架

| 框架 | 说明 | 目录/状态 |
| --- | --- | --- |
| **Claude Agent SDK** | Anthropic 官方 Agent SDK，封装 Claude Code 的 agent loop、工具与钩子能力 | `claude-code-sdk/` |
| **smolagents** | Hugging Face 出品的轻量级 Agent 框架，核心是 Code Agent（用代码作为动作） | 计划中 |
| **DeepAgents** | LangChain 生态下的深度 Agent 框架，强调规划、子代理与文件系统 | 计划中 |
| **pi-mono** | 基于 mono 设计的轻量 Agent 框架 | 计划中 |

> 后续会持续补充更多框架，保持每个示例的可运行性与可对比性。

## 项目结构

```
harness-frame-action/
├── claude-code-sdk/        # Claude Agent SDK 学习示例
│   ├── clienttest.py       # ClaudeSDKClient 多轮客户端示例
│   ├── querytest.py        # 一次性 query 示例
│   ├── getbalance.py       # 结合工具调用的示例
│   └── ping.py             # 连通性测试
├── main.py                 # 项目入口占位
├── pyproject.toml          # 依赖与项目元数据
└── .env                    # 环境变量（不入库）
```

各子目录相互独立，互不依赖，可以单独运行。

## 快速开始

项目使用 [uv](https://github.com/astral-sh/uv) 管理依赖（Python >= 3.13）：

```bash
# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env  # 若存在模板
# 然后在 .env 中填写 ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL 等

# 运行示例
uv run claude-code-sdk/querytest.py
```

## 环境变量

示例依赖 Claude 相关环境变量，请在 `.env` 中配置（该文件已被 `.gitignore` 忽略）：

```bash
ANTHROPIC_API_KEY=your-api-key
ANTHROPIC_BASE_URL=https://api.anthropic.com  # 使用代理/中转时修改
```

## 说明

- 本项目仅用于个人学习与实验，示例代码追求可读性而非工程完备性。
- `claude-code-sdk/data/` 与测试产物不会提交到仓库。
