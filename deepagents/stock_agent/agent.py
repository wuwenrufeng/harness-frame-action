import os
import sys
from pathlib import Path

from deepagents.backends import LocalShellBackend
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from deepagents import create_deep_agent

load_dotenv(
    "/Users/wuwen/workspace/python/github/harness-frame-action/.env", override=True
)

PROJECT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = PROJECT_DIR / "skills"
if not SKILLS_DIR.is_dir():
    raise FileNotFoundError(f"Skills directory does not exist: {SKILLS_DIR}")

model = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", ""))

shell_path = os.pathsep.join([str(Path(sys.executable).parent), os.defpath])
local_backend = LocalShellBackend(str(PROJECT_DIR), virtual_mode=True, env={"PATH": shell_path})

agent = create_deep_agent(
    model,
    backend=local_backend,
    skills=["/skills"],  # virtual path relative to PROJECT_DIR in virtual_mode
    system_prompt=f"""
    你是一位金融研报项目协调员。用户会提供股票代码、公司名称、市场和分析年份。

    文件工具中的 / 是项目目录 {PROJECT_DIR}；例如 /workspace/data 对应
    宿主机 {PROJECT_DIR}/workspace/data。execute 使用宿主机 shell，工作目录为
    {PROJECT_DIR}，不会映射虚拟绝对路径。执行脚本时使用相对路径
    skills/<技能目录>/scripts/...，并使用 python 调用当前项目的解释器。
    脚本默认的 /workspace 是宿主机绝对路径，不可直接使用；调用脚本时
    必须显式传入输入、输出等路径参数，使用 workspace/... 相对路径，
    确保与文件工具的 /workspace/... 对应。技能目录以实际 ls 结果为准。
    只有工具返回了具体错误时才报告相应限制；禁止将未经验证的数字作为事实。

    你的工作流程（按顺序执行）：

    ## 阶段 1: 数据采集
    - 调用 `competitor-research` skill 研究竞争对手和行业
    - 调用 `financial-data-collection` skill 采集所有公司的财务报表

    ## 阶段 2: 指标计算
    - 调用 `financial-ratio-calculation` skill 计算所有公司的财务比率

    ## 阶段 3: 分析与可视化
    - 调用 `financial-visualization` skill 生成趋势图和对比图
    - 调用 `valuation-modeling` skill 生成估值报告

    ## 阶段 4: 报告撰写
    - 调用 `report-writing` skill（隐式遵循其写作规范）
    - 调用 `report-assembly` skill 组装最终研报

    ## 状态管理
    所有中间产物都保存在文件系统中，你通过 read/glob 工具检查产物是否存在。
    如果某个 skill 失败，记录警告并尝试继续。
    """,
)

run_config = {"recursion_limit": 100}

result = agent.invoke(
    {"messages": [{"role": "user", "content": "生成青岛啤酒SH600600的2025年金融研报"}]},
    run_config=run_config,
)

print("#" * 80)
print(result)
print("#" * 80)
