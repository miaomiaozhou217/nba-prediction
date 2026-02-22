# NBA 大小分预测系统 🏀

## 项目目标

预测NBA比赛的**大小分**（Over/Under）：
- 全场总分（两队得分之和）
- 主队单独得分
- 客队单独得分

## 项目结构

```
nba/
├── data/              # 数据存储
│   ├── raw/          # 原始API数据
│   ├── processed/    # 清洗后的数据
│   └── features/     # 特征工程结果
├── scripts/          # 核心脚本
│   ├── fetch_data.py      # 数据获取
│   ├── build_features.py  # 特征工程
│   ├── train_model.py     # 模型训练
│   └── predict.py         # 实时预测
├── models/           # 训练好的模型
├── notebooks/        # Jupyter分析笔记
├── docs/             # 文档
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 获取数据

```bash
python scripts/fetch_data.py --season 2024-25 --games 100
```

### 3. 分析数据

```bash
python scripts/analyze.py
```

### 4. 训练模型

```bash
python scripts/train_model.py
```

### 5. 预测今日比赛

```bash
python scripts/predict.py --today
```

## 数据源

- **NBA官方API** (via `nba_api`)
- **BALLDONTLIE API** (补充)

## 核心特征

### 球队层面
- 场均得分/失分
- 比赛节奏（Pace）
- 攻防效率（Offensive/Defensive Rating）
- 近期趋势（5场/10场滑动窗口）
- 主客场差异

### 对阵层面
- 历史交手得分
- 防守对位强度
- 节奏匹配度

### 环境因素
- 背靠背情况
- 休息天数
- 伤病报告

## 建模策略

### 阶段1: 规则Based（快速验证）
- 基于节奏+防守效率的简单规则
- 目标：准确率 > 52%（盈亏平衡点）

### 阶段2: 机器学习（优化）
- XGBoost/LightGBM
- 特征重要性分析
- 目标：准确率 > 55%

### 阶段3: 深度学习（可选）
- LSTM（时间序列）
- Transformer（注意力机制）

## 回测框架

```python
# 模拟过去100场比赛
python scripts/backtest.py --games 100 --strategy ml_model
```

输出：
- 预测准确率
- 盈利曲线
- 凯利准则建议下注比例

## 风控

- 单场最大下注：资金池的 2-5%
- 停止条件：连续亏损 > 10场
- 凯利公式动态调整仓位

## 作者

细菌 + 淼淼 🌊

## 许可

MIT License
