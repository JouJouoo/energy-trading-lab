# Energy Trading Lab：面向能源交易的科研仿真实验智能体

Energy Trading Lab 是一个垂直场景 AI Agent 作品，用于投递 **AI Agent 应用开发工程师**。当前 MVP 以 P2P 能源交易为核心演示切口，聚焦两个痛点：

- 期刊论文通常不公开代码，复现实验困难。
- 研究者已有创新理论后，从零搭建 IEEE 33/69 节点实验很耗时。

MVP 已实现科研 Agent 闭环：论文/理论输入、RAG 式领域抽取、策略类型识别、复现缺口分析、IEEE 33/69 实验配置生成、传统算法与轻量 RL 策略对比、配电网潮流风险校验、研究报告生成。配置 LLM API 后会调用大语言模型做结构化论文理解；未配置时会明确降级为 deterministic fallback，便于离线演示。

每篇论文或每份创新点草稿都会生成一个专属代码项目 `runs/{run_id}/code_project/`，里面包含独立的 `configs/`、`src/energy_project/`、`tests/` 和 `outputs/`。这不是只保存一段脚本，而是给该文章/想法单独建立一个可继续开发、可 smoke test、可复现实验的工程目录。

## Quick Start

```bash
source .venv/bin/activate
python -m p2plab.cli demo --grid-case ieee33 --experiment-depth quick
python -m p2plab.cli reproduce --input examples/sample_paper.md --grid-case ieee33 --experiment-depth research
python -m p2plab.cli theory --input examples/theory_draft.md --grid-case ieee69 --experiment-depth research
```

启动本地产品工作台：

```bash
source .venv/bin/activate
python -m p2plab.cli serve --port 8765
```

打开 `http://127.0.0.1:8765`。

## Experiment Depth

前端默认使用 `Research` 档，不再是几秒钟的纯演示流程：

| Depth | Horizon | RL episodes | 用途 |
| --- | --- | --- | --- |
| `quick` | 48 hours | 100 | 面试现场快速展示，确认端到端链路 |
| `research` | 168 hours | 3000 | 默认产品体验，真实生成脚本、执行子进程、训练 RL baseline/proposed method |
| `deep` | 336 hours | 12000 | 更长时间泛化验证，可用于录制 Demo 或离线实验 |

每次运行会保存 `generated_experiment_attempt_*.py`、`execution_log_attempt_*.txt`、`training_curve_attempt_*.json` 和最终 `training_curve.csv`。前端 Agent Trace 会显示 `strategy_start`、`training_progress`、`strategy_done`，可以看到当前训练到第几个 episode。

## LLM API 配置

真正理解不同论文创新点、生成 paper-specific 实验方案，需要调用大语言模型 API。项目支持 OpenAI-compatible Chat Completions 接口：

```bash
source .venv/bin/activate
export ENERGY_LAB_LLM_API_KEY="你的 API Key"
export ENERGY_LAB_LLM_BASE_URL="https://api.openai.com/v1"
export ENERGY_LAB_LLM_MODEL="gpt-4o-mini"
export ENERGY_LAB_LLM_TEMPERATURE="0.1"
export ENERGY_LAB_LLM_MAX_TOKENS="2500"
python -m p2plab.cli serve --port 8765
```

也可以接 DeepSeek、Qwen、Kimi 等兼容 OpenAI `/chat/completions` 的服务，只需要替换 `ENERGY_LAB_LLM_BASE_URL` 和 `ENERGY_LAB_LLM_MODEL`。

前端顶部会显示：

- `LLM gpt-4o-mini`：已启用模型调用。
- `LLM fallback`：没有配置 API Key，当前使用启发式 fallback。

CLI 和报告里也会写入 `analysis_meta.json`，标明本次分析来源、模型名和错误信息。

复现文章的产品流程：

1. 在左侧选择 `Paper` 工作流。
2. 点击 `Upload` 上传 `.md/.txt/.pdf` 文献，或把论文摘要/方法段落粘贴进文本框。
3. 上传成功后，文献文本会自动进入输入区。
4. 点击 `Run Agent`，系统会生成模型卡、策略识别、复现缺口、IEEE 33/69 实验配置、仿真结果和报告。

当前执行链路不是直接调用内存函数出结果，而是：

1. Attempt 1：根据论文抽取结果生成经典 baseline + RL scaffold 的 `generated_experiment_attempt_1.py` 和 `experiment_config_attempt_1.json`。
2. 子进程在沙盒 run 目录中执行生成代码，实时打印 `training_progress`，写出 `metrics_attempt_1.json`、`hourly_metrics_attempt_1.json`、`training_curve_attempt_1.json` 和 `execution_log_attempt_1.txt`。
3. Agent 检查日志和指标，并根据论文创新点生成 `innovation_spec.json`。
4. Attempt 2：在经典算法基础上注入论文相关修改项，例如碳感知 reward、电压风险惩罚、博弈定价偏置或公平性约束。生成脚本内会写入 `PAPER_SPECIFIC_ALGORITHM` 和 `apply_paper_specific_algorithm(...)`，让不同论文/理论产生不同的代码级 adapter，然后再次运行。
5. Agent 生成专属工程 `code_project/`：包含项目 README、完整配置、论文创新点 adapter、运行入口、smoke test 和输出目录。
6. 最终报告展示每次代码生成、执行耗时、优化原因和最终实验结果。

PDF 说明：PDF 上传接口已经接好；若环境未安装 PDF 解析库，请执行：

```bash
source .venv/bin/activate
python -m pip install pypdf
```

运行作品级评测：

```bash
source .venv/bin/activate
python -m p2plab.eval --output-dir runs/eval
```

评测会批量覆盖 paper/theory 与 IEEE 33/69，生成 `runs/eval/eval_report.md` 和 `runs/eval/eval_report.json`。

## What It Generates

每次运行会在 `runs/{task_id}/` 生成：

- `model_spec.json`
- `strategy_spec.json`
- `reproduction_gaps.md`
- `experiment_config.yaml`
- `metrics.json`
- `hourly_metrics.csv`
- `training_curve.csv`
- `agent_trace.json`
- `innovation_spec.json`
- `analysis_meta.json`
- `execution_summary.json`
- `generated_experiment_attempt_*.py`
- `training_curve_attempt_*.json`
- `execution_log_attempt_*.txt`
- `run_report.md`
- `code_project/README.md`
- `code_project/configs/experiment_config.json`
- `code_project/configs/smoke_config.json`
- `code_project/src/energy_project/adapter.py`
- `code_project/src/energy_project/run_experiment.py`
- `code_project/src/energy_project/generated_attempt.py`
- `code_project/tests/test_smoke.py`

专属代码项目可以单独运行：

```bash
cd runs/{run_id}/code_project
python src/energy_project/run_experiment.py --config configs/experiment_config.json --output-dir outputs/research
python -m unittest discover -s tests
```

## Implemented Agent Capabilities

- **Paper-to-Reproduction**：上传或粘贴 P2P 能源交易论文文本，生成结构化复现实验包。
- **Theory-to-Experiment**：输入中文理论草稿，生成 3 个实验假设和可运行实验。
- **Strategy classification**：识别 RL/MARL、优化、拍卖、博弈论、规则算法。
- **Traditional baselines**：`no_trading`、`rule_double_auction`、`optimization_clearing`。
- **RL baseline**：轻量 Q-learning 风格 bidding，用于本地快速演示。
- **Proposed method**：理论草稿流程中加入电压/碳感知 bidding 变体。
- **Paper-specific algorithm generation**：根据文章创新点把经典算法改成不同 proposed method 参数和 reward/objective 组合。
- **LLM structured analysis**：配置 API Key 后，调用 OpenAI-compatible LLM 抽取模型、算法、创新点、复现缺口和实验假设。
- **Generated-code execution**：每次运行保存生成脚本、配置、日志和指标，而不是直接隐藏式调用仿真函数。
- **Dedicated code project**：每篇文章/每份创新草稿生成一个独立 `code_project/`，包含专属 adapter、配置、runner、smoke test 和输出目录。
- **Streaming training progress**：Research/Deep 模式会流式展示 episode 进度，并保存训练曲线。
- **IEEE 33/69 support**：IEEE 33 使用 Baran-Wu 风格数据；IEEE 69 使用内置可替换径向 feeder。
- **Agent trace**：记录每一步工具调用、输入输出摘要和运行状态。
- **Portfolio eval**：批量统计成功率、延迟、artifact 完整度、策略覆盖率。

## Portfolio Mapping

简历项目名：

**Energy Trading Lab：面向能源交易的科研仿真实验智能体**

简历描述：

基于 Python、OpenAI-compatible LLM API 和 Agent 工具调用思想构建垂直科研仿真实验智能体，支持能源交易论文解析、策略类型识别、复现缺口分析、IEEE 33/69 节点实验配置生成、RL 与传统交易算法对比、配电网潮流校验和研究报告生成。设计多步骤 Agent Graph，实现任务规划、工具调用、结构化输出、实验日志记忆、失败诊断与自动修复，并通过评测集统计抽取准确率、实验成功率、平均响应延迟和调用成本。

## Next Engineering Upgrades

- 用 LangGraph 替换当前确定性 graph runner，保留同一套 tool interface。
- 将当前 OpenAI-compatible structured analysis 升级为 LangGraph 节点，并接入 Chroma/Qdrant 向量库。
- 安装 pandapower 后，将 `SimplePowerFlowValidator` 替换成 AC power flow adapter。
- 用 FastAPI + Uvicorn 部署生产 API；当前标准库 HTTP server 用于轻量演示。
- 接入 Dify 复刻轻量 workflow，或用 AutoGen/supervisor 做实验质检 Agent。
