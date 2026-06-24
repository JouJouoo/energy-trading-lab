# 论文到代码：高度匹配的论文算法代码生成设计

## 1. 背景与目标

当前项目的论文复现流程存在以下局限：

1. 生成的代码是模板化脚本，通过参数调整模拟"论文创新点"
2. 创新点只体现在描述文本和参数权重上，没有真正的算法实现
3. 只支持有限的策略类型，无法覆盖论文中多样的算法
4. 生成的项目依赖现有框架，不够独立

**目标**：论文解析后，按照论文的算法思路和创新点，构建与论文高度匹配的独立代码项目。支持多种算法类型（RL、优化、拍卖、博弈论等），支持改进算法和原创算法。

## 2. 总体方案：分模块生成 + 多算法类型支持

### 2.1 核心思想

采用"分模块生成、独立验证、按需组装"的模式，将代码生成分解为多个独立模块，每个模块单独生成和验证，最后组装成完整项目。

### 2.2 处理流程

```
阶段1：论文深度解析
  ├─ 提取算法类型
  ├─ 识别基础算法（基线算法）
  ├─ 提取创新点列表（分层分类）
  ├─ 判断创新模式：改进型 vs 原创型
  └─ 提取实验设置

阶段2：模块规划
  ├─ 根据算法类型选择模块列表
  ├─ 确定是否有可复用的基础算法模板
  ├─ 规划创新点应用顺序（从底层到高层）
  └─ 生成模块依赖关系图

阶段3：分模块生成
  ├─ 生成基础模块（grid, market, data）
  ├─ 如果是改进型算法：
  │   ├─ 从模板库加载基础算法
  │   └─ 逐层应用创新点，生成改进版本
  └─ 如果是原创算法：
      └─ 从零生成算法核心模块

阶段4：模块验证
  ├─ 语法检查（ast.parse）
  ├─ 接口检查（导入、函数签名）
  └─ Smoke test（小数据量运行）

阶段5：项目组装
  ├─ 写入所有模块文件
  ├─ 生成 requirements.txt
  ├─ 生成 README.md
  └─ 生成测试用例

阶段6：集成测试
  ├─ 运行完整实验（短周期）
  ├─ 验证输出格式
  └─ 失败则定位并修复对应模块
```

## 3. 算法类型与模块映射

### 3.1 算法类型识别

从论文文本中识别算法类型，支持以下类型：

- **RL/MARL**：强化学习 / 多智能体强化学习
- **Optimization**：优化（线性规划、混合整数规划、凸优化等）
- **Auction**：拍卖机制（双边拍卖、统一价格拍卖等）
- **Game Theory**：博弈论（Stackelberg、纳什均衡等）
- **Rule-based**：规则算法（阈值、调度等）
- **Heuristic**：启发式算法

### 3.2 模块映射表

| 算法类型 | 核心模块 | 可选模块 |
|---------|---------|---------|
| **RL/MARL** | `agent.py`, `training_loop.py`, `reward.py` | `memory.py`, `policy.py`, `state_processor.py` |
| **Optimization** | `optimizer.py`, `objective.py` | `constraints.py`, `solver_config.py` |
| **Auction** | `auction_engine.py`, `bidding.py` | `matching.py`, `settlement.py` |
| **Game Theory** | `game_engine.py`, `players.py` | `equilibrium.py`, `price_dynamics.py` |
| **Rule-based** | `rules.py`, `decision_engine.py` | `thresholds.py`, `scheduler.py` |
| **Heuristic** | `heuristics.py`, `search.py` | `meta_parameters.py` |

### 3.3 共享基础模块

所有算法类型共享以下基础模块：

- `grid_model.py` - IEEE 33/69 配电网模型（基于 pandapower）
- `market_env.py` - 市场环境（供需、价格、时序）
- `data_loader.py` - 数据加载（负荷、PV、电价等）
- `experiment_runner.py` - 实验入口
- `metrics.py` - 指标计算
- `config.py` - 配置管理

## 4. 创新点处理：改进算法 vs 原创算法

### 4.1 创新模式判断

从论文解析中判断创新模式：

- **改进型算法**：论文明确提到在某个已有算法基础上进行改进
- **原创算法**：论文提出全新的算法或机制

### 4.2 创新点分层模型

论文的创新点分为多个层次，每个层次对应不同的代码修改方式：

| 创新层次 | 代码修改方式 | 示例 |
|---------|-------------|------|
| **奖励/目标函数层** | 修改 reward/objective 函数 | 增加碳感知奖励项 |
| **状态/动作空间层** | 修改 state/action 定义 | 增加电压状态、增加电池调度动作 |
| **策略更新层** | 修改策略更新逻辑 | 改变学习率调度、修改探索策略 |
| **网络结构层** | 修改神经网络结构 | 增加注意力机制、使用 GNN |
| **算法框架层** | 修改整体算法流程 | 从单智能体改为多智能体、增加博弈层 |
| **约束层** | 增加约束条件 | 增加电压约束、增加公平性约束 |
| **全新算法** | 从零生成 | 提出全新的市场机制 |

### 4.3 改进型算法生成流程

1. 识别基础算法（如 Q-learning、PPO、双重拍卖等）
2. 从算法模板库中加载基础算法实现
3. 提取创新点并分层分类
4. 按层次顺序应用创新点（从底层到高层）
5. 生成改进后的算法代码
6. 验证改进后的算法

### 4.4 原创算法生成流程

1. 提取算法的核心逻辑、状态转移、更新规则
2. 从零生成算法核心模块
3. 验证原创算法
4. 与基线算法对比验证

## 5. 算法模板库

### 5.1 模板库结构

```
algorithm_templates/
├── RL/
│   ├── q_learning.py
│   ├── dqn.py
│   ├── ppo.py
│   ├── maddpg.py
│   └── sac.py
├── Optimization/
│   ├── linear_programming.py
│   ├── mixed_integer_lp.py
│   └── convex_optimization.py
├── Auction/
│   ├── double_auction.py
│   ├── uniform_price_auction.py
│   └── vickrey_auction.py
├── GameTheory/
│   ├── stackelberg_game.py
│   ├── nash_equilibrium.py
│   └── evolutionary_game.py
└── RuleBased/
    ├── threshold_based.py
    └── schedule_based.py
```

### 5.2 模板规范

每个模板必须包含：

- 标准的类/函数接口
- 清晰的注释说明
- 可运行的示例
- 扩展点标记（哪些地方容易被修改）

## 6. 模块接口规范

### 6.1 环境接口（market_env.py）

```python
class MarketEnvironment:
    def reset(self) -> dict:
        """重置环境，返回初始状态"""

    def step(self, action: dict) -> tuple[dict, float, bool, dict]:
        """执行动作，返回 (下一状态, 奖励, 是否结束, 附加信息)"""

    def get_grid_state(self) -> dict:
        """获取电网状态"""
```

### 6.2 RL 算法接口

```python
class RLAgent:
    def select_action(self, state: dict) -> dict:
        """根据状态选择动作"""

    def update(self, state: dict, action: dict, reward: float, next_state: dict, done: bool) -> None:
        """更新策略"""

    def save(self, path: str) -> None:
        """保存模型"""

    def load(self, path: str) -> None:
        """加载模型"""
```

### 6.3 优化算法接口

```python
class OptimizationSolver:
    def solve(self, market_state: dict) -> dict:
        """求解优化问题，返回分配结果"""

    def get_objective_value(self) -> float:
        """获取目标函数值"""
```

### 6.4 拍卖算法接口

```python
class AuctionEngine:
    def submit_bid(self, bid: dict) -> None:
        """提交报价"""

    def clear_market(self) -> dict:
        """市场出清，返回结果"""
```

### 6.5 博弈论算法接口

```python
class GameEngine:
    def set_leader_price(self, price: float) -> None:
        """设置领导者价格"""

    def get_follower_response(self) -> dict:
        """获取跟随者响应"""

    def find_equilibrium(self) -> dict:
        """寻找均衡点"""
```

### 6.6 电网接口（grid_model.py）

```python
class GridModel:
    def run_power_flow(self, load_profile: dict, pv_profile: dict) -> dict:
        """执行潮流计算"""

    def get_voltage_profile(self) -> dict:
        """获取电压分布"""

    def get_network_loss(self) -> float:
        """获取网损"""
```

## 7. 验证与自动修复机制

### 7.1 三级验证

每个模块生成后，执行三级验证：

1. **Level 1 - 语法检查**：`ast.parse(code)`，验证代码语法正确性
2. **Level 2 - 接口检查**：检查必须的类/函数是否存在，签名是否匹配
3. **Level 3 - Smoke test**：用最小配置运行，检查是否有运行时错误

### 7.2 修复循环

- 每个模块最多尝试 3 次修复
- 每次将错误信息反馈给 LLM 重新生成
- 3 次失败后，降级为模板实现并标记

## 8. 生成的独立项目结构

```
paper_project/
├── README.md
├── requirements.txt
├── configs/
│   ├── experiment_config.json
│   ├── ieee33_config.json 或 ieee69_config.json
│   └── algorithm_config.json
├── src/
│   ├── __init__.py
│   ├── grid/
│   │   ├── __init__.py
│   │   ├── grid_model.py        # pandapower IEEE 33/69
│   │   └── power_flow.py
│   ├── market/
│   │   ├── __init__.py
│   │   ├── market_env.py
│   │   └── data_loader.py
│   ├── algorithm/
│   │   ├── __init__.py
│   │   ├── reward.py            # RL: reward函数
│   │   ├── agent.py             # RL: 智能体
│   │   ├── training_loop.py     # RL: 训练循环
│   │   │  （或根据算法类型不同）
│   │   ├── optimizer.py         # 优化: 求解器
│   │   ├── objective.py         # 优化: 目标函数
│   │   │  （或）
│   │   ├── auction_engine.py    # 拍卖: 引擎
│   │   ├── bidding.py           # 拍卖: 竞价
│   │   │  （或）
│   │   ├── game_engine.py       # 博弈: 引擎
│   │   └── players.py           # 博弈: 玩家
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── metrics.py
│   │   └── visualization.py
│   └── run_experiment.py        # 实验入口
├── tests/
│   ├── test_smoke.py
│   └── test_grid_model.py
└── outputs/
    └── .gitkeep
```

## 9. LLM 提示词设计

### 9.1 通用提示词结构

每个模块的生成都有专门的提示词模板，包含：

- 模块的功能描述
- 接口规范（必须实现的类/函数）
- 论文中提取的相关信息
- 代码风格要求
- 依赖的其他模块

### 9.2 创新点应用提示词

对于改进型算法，提示词中包含：

- 基础算法代码
- 创新点描述
- 需要修改的部分
- 修改后的预期效果

## 10. 与现有系统的集成

### 10.1 新增模块

- `p2plab/code_generator.py` - 代码生成器（核心）
- `p2plab/algorithm_templates/` - 算法模板库
- `p2plab/module_validator.py` - 模块验证器
- `p2plab/project_assembler.py` - 项目组装器

### 10.2 修改现有模块

- `p2plab/agent.py` - 集成新的代码生成流程
- `p2plab/llm_analysis.py` - 增强论文解析，提取创新点分层
- `p2plab/schemas.py` - 新增代码生成相关的数据结构
- `p2plab/project_builder.py` - 升级为组装独立项目

## 11. 关键技术决策

### 11.1 pandapower vs 自建潮流计算

- **选择 pandapower**：成熟、稳定、IEEE 33/69 支持好
- **优势**：代码量少、可靠性高、功能丰富
- **劣势**：增加外部依赖

### 11.2 分模块生成 vs 一次性生成

- **选择分模块生成**：更容易验证和调试
- **优势**：失败后可以只修复特定模块，质量更可控
- **劣势**：需要多次 LLM 调用，成本稍高

### 11.3 模板库 + 创新 vs 完全从零生成

- **选择模板库 + 创新**：质量更有保障，更符合论文"改进"的特点
- **优势**：基线算法可靠，创新点清晰
- **劣势**：需要维护模板库

## 12. 后续扩展

- 支持更多算法类型（如元启发式、联邦学习等）
- 增加更多基线算法模板
- 支持多论文对比实验
- 集成更多电网模型（如 IEEE 123、真实配电网数据）
