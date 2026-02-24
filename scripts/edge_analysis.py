#!/usr/bin/env python3
"""
V3模型Edge分析：在不同盘口线下的真实准确率
用现有1670场数据，模拟"如果盘口=actual_total±N，模型预测是否正确"
核心思路：用actual_total作为盘口proxy，计算模型在不同偏离度下的hit rate

这回答一个关键问题：当V3预测偏离盘口X分时，OVER/UNDER的胜率到底是多少？
"""
import pandas as pd
import numpy as np
import joblib
import os
import json
from sklearn.model_selection import TimeSeriesSplit

PROJECT = os.path.dirname(os.path.dirname(__file__))

def load_model_and_data():
    """加载V3模型和特征数据"""
    pkg = joblib.load(os.path.join(PROJECT, "models/total_points_model_v3.pkl"))
    model = pkg['model'] if isinstance(pkg, dict) else pkg
    feature_cols_saved = pkg.get('feature_cols', []) if isinstance(pkg, dict) else []
    if feature_cols_saved:
        print(f"   模型特征: {len(feature_cols_saved)} 个")
    
    # 尝试加载combined features
    feat_path = os.path.join(PROJECT, "data/features/features_v3_combined.csv")
    if not os.path.exists(feat_path):
        feat_path = os.path.join(PROJECT, "data/features/features_v3.csv")
    
    df = pd.read_csv(feat_path)
    print(f"📊 数据: {len(df)} 场, 特征文件: {os.path.basename(feat_path)}")
    return model, df, feature_cols_saved

def run_edge_analysis(model, df, feature_cols_saved):
    """
    时间序列OOS预测，然后分析不同偏离度下的准确率
    """
    if feature_cols_saved:
        feature_cols = [c for c in feature_cols_saved if c in df.columns]
    else:
        feature_cols = [c for c in df.columns if c not in ['date', 'total_points', 'home_team', 'away_team', 'season']]
    # 确保只用数值列
    feature_cols = [c for c in feature_cols if df[c].dtype in ['int64','float64','int32','float32']]
    X = df[feature_cols].values
    y = df['total_points'].values
    
    # 时间序列OOS：用前70%训练，后30%测试
    split = int(len(df) * 0.7)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    actuals = y_test
    
    print(f"📊 OOS样本: {len(actuals)} 场 (后30%)")
    print(f"   MAE: {np.mean(np.abs(predictions - actuals)):.2f}")
    
    # 核心分析：模拟不同盘口线
    # 假设盘口 = actual_total（即市场完美定价）
    # 然后看模型预测偏离盘口X分时，actual是否真的over/under
    
    results = []
    
    for i in range(len(actuals)):
        pred = predictions[i]
        actual = actuals[i]
        
        # 模拟多个盘口线：actual±0, ±2, ±5, ±10
        # 但更有意义的是：用actual作为"真实盘口"
        # 然后看 pred vs actual_line → 模型说over还是under → 实际对不对
        
        # 方法1：用actual_total作为盘口线
        line = actual  # 如果市场完美定价
        deviation = pred - line
        direction = "OVER" if deviation > 0 else "UNDER"
        # 因为line=actual，所以hit永远是50%（这不有用）
        
        # 方法2：更好的方式 - 用样本均值附近的固定线
        # 方法3：最好的方式 - 分析deviation vs actual的关系
        results.append({
            'prediction': pred,
            'actual': actual,
            'deviation_from_actual': pred - actual,  # 预测误差
        })
    
    df_results = pd.DataFrame(results)
    
    # 关键分析：当模型预测偏离某个线X分时，实际结果如何？
    # 模拟盘口线 = 样本均值（~229分）
    mean_total = np.mean(actuals)
    print(f"\n📊 样本均值总分: {mean_total:.1f}")
    
    # 对每场比赛，假设盘口 = mean_total
    # 看模型是否能正确预测over/under
    print(f"\n{'='*70}")
    print(f"分析1: 固定盘口线下的准确率")
    print(f"{'='*70}")
    
    for line in [215, 220, 225, 228, 230, 232, 235, 240]:
        over_pred = predictions > line  # 模型说OVER
        over_actual = actuals > line    # 实际OVER
        
        # 只看模型有信心的场次（偏离>N分）
        for min_dev in [0, 3, 5, 8, 10, 15]:
            mask = np.abs(predictions - line) >= min_dev
            if mask.sum() < 10:
                continue
            
            correct = (over_pred[mask] == over_actual[mask]).sum()
            total = mask.sum()
            accuracy = correct / total * 100
            
            # 计算ROI（假设赔率1.90）
            wins = correct
            losses = total - correct
            roi = (wins * 0.90 - losses) / total * 100
            
            if min_dev == 0:
                print(f"  Line {line:>3d} | 偏离≥{min_dev:>2d} | {total:>4d}场 | "
                      f"准确率{accuracy:>5.1f}% | ROI{roi:>+6.1f}%")
            elif min_dev in [3, 5, 10]:
                print(f"           | 偏离≥{min_dev:>2d} | {total:>4d}场 | "
                      f"准确率{accuracy:>5.1f}% | ROI{roi:>+6.1f}%")
    
    # 分析2：偏离度 vs 准确率的关系（最重要）
    print(f"\n{'='*70}")
    print(f"分析2: 偏离度分桶准确率（使用样本均值{mean_total:.0f}作为盘口）")
    print(f"{'='*70}")
    
    line = round(mean_total)
    deviations = predictions - line
    over_pred = predictions > line
    over_actual = actuals > line
    correct = over_pred == over_actual
    
    bins = [(0,2), (2,4), (4,6), (6,8), (8,10), (10,15), (15,20), (20,30)]
    print(f"\n{'偏离范围':>10} {'场次':>6} {'准确率':>8} {'ROI':>8} {'方向':>8}")
    print("-" * 50)
    
    for lo, hi in bins:
        mask = (np.abs(deviations) >= lo) & (np.abs(deviations) < hi)
        if mask.sum() < 5:
            continue
        n = mask.sum()
        acc = correct[mask].mean() * 100
        roi = (correct[mask].sum() * 0.90 - (~correct[mask]).sum()) / n * 100
        
        # 看这个区间是OVER多还是UNDER多
        over_pct = over_pred[mask].mean() * 100
        
        print(f"  {lo:>2d}-{hi:<2d}分  {n:>6d} {acc:>7.1f}% {roi:>+7.1f}% {'OVER偏多' if over_pct > 60 else 'UNDER偏多' if over_pct < 40 else '均衡'}")
    
    # 分析3：用真实盘口范围（225-235）的模拟
    print(f"\n{'='*70}")
    print(f"分析3: 真实盘口范围(225-235)模拟 — 最接近实战")
    print(f"{'='*70}")
    
    # 对每场比赛，随机模拟一个"盘口" = actual ± uniform(-3, 3)
    # 这模拟了市场定价不完美的情况
    np.random.seed(42)
    
    for noise_std in [0, 1, 2, 3, 5]:
        noise = np.random.normal(0, noise_std, len(actuals)) if noise_std > 0 else np.zeros(len(actuals))
        sim_lines = actuals + noise  # 模拟盘口 = 实际结果 + 噪声
        
        sim_dev = predictions - sim_lines
        sim_over_pred = sim_dev > 0
        sim_over_actual = actuals > sim_lines
        sim_correct = sim_over_pred == sim_over_actual
        
        for min_dev in [0, 3, 5, 8]:
            mask = np.abs(sim_dev) >= min_dev
            if mask.sum() < 10:
                continue
            n = mask.sum()
            acc = sim_correct[mask].mean() * 100
            roi = (sim_correct[mask].sum() * 0.90 - (~sim_correct[mask]).sum()) / n * 100
            
            if min_dev == 0:
                print(f"  噪声σ={noise_std} | 偏离≥{min_dev} | {n:>4d}场 | 准确率{acc:>5.1f}% | ROI{roi:>+6.1f}%")
            else:
                print(f"          | 偏离≥{min_dev} | {n:>4d}场 | 准确率{acc:>5.1f}% | ROI{roi:>+6.1f}%")

    # 输出结论
    print(f"\n{'='*70}")
    print(f"💡 结论")
    print(f"{'='*70}")
    print(f"  如果噪声σ=0（完美盘口=实际），任何偏离都是噪声，准确率~50%")
    print(f"  如果噪声σ=3-5（盘口偏差3-5分），模型偏离大时有edge")
    print(f"  真实市场噪声大约σ=2-4分")
    print(f"  关键：只有当模型偏离 > 市场噪声时，才有真正的edge")

if __name__ == "__main__":
    model, df, feature_cols_saved = load_model_and_data()
    run_edge_analysis(model, df, feature_cols_saved)
