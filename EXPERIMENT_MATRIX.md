# NBA模型最小实验矩阵（Codex 5.3设计）

## 统一规则
- 验证: 5折TimeSeriesSplit (OOS)
- 主盘口: 只看215
- ROI口径: -110赔率, 统一公式
- 主指标: ROI@215, Accuracy@215, 下注场数
- 辅助: MAE
- 阈值: 固定看 0/3/5/6/10%

## E1: 基线复测 (V3当前版)
- 建立唯一可信基准
- 各阈值ROI/Accuracy/场数
- +2.7校准是否值得保留

## E2: 伤病消融 (V3无伤病)
- 去掉home/away_injury_impact
- 与E1对比
- 判断伤病特征真实贡献

## E3: 伤病时序一致性快检
- E1 vs E2按月份/折次看差异稳定性
- 判断是否值得做历史伤病快照

## E4: V4特征增益 (20维vs24维)
- 与E1同口径OOS评估
- MAE降但ROI不变=无交易增益

## E5: B2B最小验证
- 只加home_b2b, away_b2b
- 主要看ROI@215和高阈值表现

## E6: 目标重构POC (回归→分类Over215)
- 同特征(V3 20维)
- 扫描概率阈值0.55/0.58/0.60/0.65
- 与E1回归切线法对比

## 执行顺序
- 今晚: E1 + E2 + E3
- 明天: E4 + E5 + E6

## 结果模板
| exp | features | model | threshold | bets | acc@215 | roi | mae | stable? |
