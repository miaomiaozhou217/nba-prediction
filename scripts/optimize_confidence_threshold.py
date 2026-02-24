#!/usr/bin/env python3
"""
优化信心度阈值 - 找出最优ROI的置信度切点
分析不同阈值下的: 比赛数、准确率、ROI
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import TimeSeriesSplit
import xgboost as xgb

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'

def run_cv():
    """运行CV收集预测"""
    features_df = pd.read_csv(DATA_DIR / 'features' / 'features_v3.csv')
    features_df = features_df.dropna(subset=['combined_pts_last_3', 'combined_pts_last_5'])
    
    feature_cols = [
        'home_pts_last_3', 'home_pts_last_5', 'home_pts_last_10',
        'home_opp_pts_last_5', 'home_pts_std_5', 'home_pts_last_5_home',
        'away_pts_last_3', 'away_pts_last_5', 'away_pts_last_10',
        'away_opp_pts_last_5', 'away_pts_std_5', 'away_pts_last_5_away',
        'combined_pts_last_3', 'combined_pts_last_5', 'combined_pts_last_10',
        'home_off_vs_away_def', 'away_off_vs_home_def', 'home_field_advantage',
        'home_injury_impact', 'away_injury_impact'
    ]
    
    X = features_df[feature_cols].fillna(0)
    y = features_df['total_points']
    
    tscv = TimeSeriesSplit(n_splits=5)
    all_predictions = []
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        model = xgb.XGBRegressor(
            n_estimators=200, learning_rate=0.05, max_depth=6,
            min_child_weight=3, subsample=0.8, colsample_bytree=0.8,
            random_state=42, n_jobs=-1
        )
        
        model.fit(X_train, y_train, verbose=False)
        y_pred = model.predict(X_val)
        
        for idx, pred in zip(val_idx, y_pred):
            all_predictions.append({
                'actual': y.iloc[idx],
                'predicted': pred
            })
    
    return pd.DataFrame(all_predictions)

def evaluate_threshold(df, threshold, line=215):
    """评估特定阈值下的表现"""
    df['confidence'] = abs(df['predicted'] - line) / line * 100
    subset = df[df['confidence'] >= threshold].copy()
    
    if len(subset) == 0:
        return None
    
    # 准确率
    correct = sum((subset['actual'] > line) == (subset['predicted'] > line))
    accuracy = correct / len(subset) * 100
    
    # ROI (美式-110赔率)
    # 赢一局赚$100，输一局亏$110
    # 总投注 = len(subset) * $110
    profit = correct * 100 - (len(subset) - correct) * 110
    total_bet = len(subset) * 110
    roi = (profit / total_bet) * 100
    
    return {
        'threshold': threshold,
        'games': len(subset),
        'accuracy': accuracy,
        'roi': roi,
        'wins': correct,
        'losses': len(subset) - correct
    }

def main():
    print("\n" + "="*70)
    print("🎯 信心度阈值优化 - 寻找最优ROI切点")
    print("="*70 + "\n")
    
    print("🔧 运行5折CV收集预测...\n")
    predictions_df = run_cv()
    print(f"✅ 收集了 {len(predictions_df)} 场out-of-sample预测\n")
    
    # 测试不同阈值
    thresholds = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20]
    results = []
    
    for threshold in thresholds:
        result = evaluate_threshold(predictions_df, threshold)
        if result:
            results.append(result)
    
    results_df = pd.DataFrame(results)
    
    # 输出表格
    print("="*70)
    print(f"{'阈值%':<8s} {'比赛数':<10s} {'准确率':<12s} {'胜/负':<12s} {'ROI':<12s} {'评级':<10s}")
    print("-"*70)
    
    for _, row in results_df.iterrows():
        threshold = row['threshold']
        games = int(row['games'])
        accuracy = row['accuracy']
        wins = int(row['wins'])
        losses = int(row['losses'])
        roi = row['roi']
        
        # 评级
        if roi > 10:
            rating = "🏆 优秀"
        elif roi > 0:
            rating = "✅ 盈利"
        elif roi > -10:
            rating = "⚠️  小亏"
        else:
            rating = "❌ 大亏"
        
        win_loss_str = f"{wins}/{losses}"
        print(f"{threshold:<8.0f} {games:<10d} {accuracy:<12.1f} {win_loss_str:<12s} {roi:<+12.1f} {rating:<10s}")
    
    # 找出最优阈值
    best_roi_row = results_df.loc[results_df['roi'].idxmax()]
    best_acc_row = results_df.loc[results_df['accuracy'].idxmax()]
    
    print("\n" + "="*70)
    print("💡 优化建议:")
    print("-"*70)
    print(f"\n🏆 最高ROI阈值: {best_roi_row['threshold']:.0f}%")
    print(f"   比赛数: {int(best_roi_row['games'])}场")
    print(f"   准确率: {best_roi_row['accuracy']:.1f}%")
    print(f"   ROI: {best_roi_row['roi']:+.1f}%")
    
    print(f"\n🎯 最高准确率阈值: {best_acc_row['threshold']:.0f}%")
    print(f"   比赛数: {int(best_acc_row['games'])}场")
    print(f"   准确率: {best_acc_row['accuracy']:.1f}%")
    print(f"   ROI: {best_acc_row['roi']:+.1f}%")
    
    # 推荐
    positive_roi = results_df[results_df['roi'] > 0]
    if len(positive_roi) > 0:
        # 选择ROI>0且比赛数>=20的最低阈值
        viable = positive_roi[positive_roi['games'] >= 20]
        if len(viable) > 0:
            recommended = viable.iloc[0]  # 最低阈值
            print(f"\n💰 推荐阈值: {recommended['threshold']:.0f}%")
            print(f"   原因: ROI>0且有足够样本（{int(recommended['games'])}场）")
            print(f"   预期每月: ~{int(recommended['games'] / 5 * 30 / 30)}场可下注比赛")
        else:
            print(f"\n⚠️  无阈值能达到ROI>0且>=20场样本")
            print(f"   建议: 保持V3原始模型，继续paper trading观察")
    else:
        print(f"\n❌ 所有阈值ROI均为负")
        print(f"   建议: V3模型可能不适合盈利交易，考虑:")
        print(f"   - 扩充训练数据（>1000场）")
        print(f"   - 更换预测目标（比如只预测大分/小分，不预测具体分数）")
        print(f"   - 结合人工判断（模型提供参考，不盲目跟单）")
    
    print("\n" + "="*70 + "\n")

if __name__ == '__main__':
    main()
