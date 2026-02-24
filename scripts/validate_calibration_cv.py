#!/usr/bin/env python3
"""
验证校准效果 (Time Series CV Out-of-Sample)
用真正的CV验证集预测评估校准效果
"""
import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error
import xgboost as xgb

PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / 'models'
DATA_DIR = PROJECT_ROOT / 'data'

def load_features():
    """加载特征数据"""
    filepath = DATA_DIR / 'features' / 'features_v3.csv'
    return pd.read_csv(filepath)

def evaluate_predictions(predictions_df, calibration=0):
    """评估预测（基于out-of-sample CV预测）"""
    df = predictions_df.copy()
    
    # 应用校准
    if calibration != 0:
        df['predicted'] += calibration
    
    df['error'] = df['actual'] - df['predicted']
    
    # Line 215准确率
    correct_215 = sum((df['actual'] > 215) == (df['predicted'] > 215))
    accuracy_215 = correct_215 / len(df) * 100
    
    # 高信心下注（>5%）
    df['confidence'] = abs(df['predicted'] - 215) / 215 * 100
    high_conf = df[df['confidence'] > 5].copy()
    
    if len(high_conf) > 0:
        correct_hc = sum((high_conf['actual'] > 215) == (high_conf['predicted'] > 215))
        accuracy_hc = correct_hc / len(high_conf) * 100
        roi_hc = (correct_hc - len(high_conf)) / len(high_conf) * 95
    else:
        accuracy_hc = 0
        roi_hc = 0
    
    return {
        'mae': df['error'].abs().mean(),
        'avg_error': df['error'].mean(),
        'accuracy_215': accuracy_215,
        'high_conf_games': len(high_conf),
        'high_conf_accuracy': accuracy_hc,
        'roi': roi_hc
    }

def run_cv_with_predictions():
    """运行时间序列CV，收集所有验证集预测"""
    print("🔧 运行5折时间序列交叉验证...\n")
    
    features_df = load_features()
    features_df = features_df.dropna(subset=['combined_pts_last_3', 'combined_pts_last_5'])
    
    # 特征列（V3: 20维）
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
            n_estimators=200,
            learning_rate=0.05,
            max_depth=6,
            min_child_weight=3,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train, verbose=False)
        y_pred = model.predict(X_val)
        
        mae = mean_absolute_error(y_val, y_pred)
        print(f"   Fold {fold}: MAE={mae:.2f}, 验证集{len(val_idx)}场")
        
        # 收集预测
        for idx, pred in zip(val_idx, y_pred):
            all_predictions.append({
                'actual': y.iloc[idx],
                'predicted': pred
            })
    
    print(f"\n✅ CV完成，收集了{len(all_predictions)}场out-of-sample预测\n")
    
    return pd.DataFrame(all_predictions)

def main():
    print("\n" + "="*70)
    print("📊 校准验证 (Out-of-Sample Time Series CV)")
    print("="*70 + "\n")
    
    # 运行CV获取真实预测
    predictions_df = run_cv_with_predictions()
    
    # 评估原始版
    results_raw = evaluate_predictions(predictions_df, calibration=0)
    
    # 评估校准版
    results_cal = evaluate_predictions(predictions_df, calibration=2.7)
    
    # 对比
    print("="*70)
    print(f"{'指标':<25s} {'V3原始':<15s} {'V3校准(+2.7)':<15s} {'改进':<10s}")
    print("-" * 70)
    
    metrics = [
        ('MAE', 'mae', '分'),
        ('平均偏差', 'avg_error', '分'),
        ('Line 215准确率', 'accuracy_215', '%'),
        ('高信心比赛数', 'high_conf_games', '场'),
        ('高信心准确率', 'high_conf_accuracy', '%'),
        ('理论ROI', 'roi', '%')
    ]
    
    for label, key, unit in metrics:
        raw_val = results_raw[key]
        cal_val = results_cal[key]
        diff = cal_val - raw_val
        
        if unit == '分':
            raw_str = f"{raw_val:.2f}{unit}"
            cal_str = f"{cal_val:.2f}{unit}"
            diff_str = f"{diff:+.2f}{unit}"
        elif unit == '%':
            raw_str = f"{raw_val:.1f}{unit}"
            cal_str = f"{cal_val:.1f}{unit}"
            diff_str = f"{diff:+.1f}{unit}"
        else:
            raw_str = f"{int(raw_val)}{unit}"
            cal_str = f"{int(cal_val)}{unit}"
            diff_str = f"{int(diff):+d}{unit}"
        
        print(f"{label:<25s} {raw_str:<15s} {cal_str:<15s} {diff_str:<10s}")
    
    print("\n" + "="*70)
    print("💡 结论:")
    print("-" * 70)
    
    if results_cal['mae'] < results_raw['mae']:
        print(f"✅ 校准后MAE改善 {results_raw['mae'] - results_cal['mae']:.2f}分")
    else:
        print(f"❌ 校准后MAE恶化 {results_cal['mae'] - results_raw['mae']:.2f}分")
    
    if abs(results_cal['avg_error']) < abs(results_raw['avg_error']):
        print(f"✅ 系统偏差从{results_raw['avg_error']:.2f}分降低到{results_cal['avg_error']:.2f}分")
    else:
        print(f"⚠️  系统偏差从{results_raw['avg_error']:.2f}分变为{results_cal['avg_error']:.2f}分")
    
    if results_cal['accuracy_215'] > results_raw['accuracy_215']:
        print(f"✅ Line 215准确率提升 {results_cal['accuracy_215'] - results_raw['accuracy_215']:.1f}%")
    elif results_cal['accuracy_215'] < results_raw['accuracy_215']:
        print(f"❌ Line 215准确率下降 {results_cal['accuracy_215'] - results_raw['accuracy_215']:.1f}%")
    else:
        print(f"➖ Line 215准确率无变化")
    
    if results_cal['roi'] > results_raw['roi']:
        print(f"✅ 理论ROI提升 {results_cal['roi'] - results_raw['roi']:.1f}%")
    elif results_cal['roi'] < results_raw['roi']:
        print(f"❌ 理论ROI下降 {results_cal['roi'] - results_raw['roi']:.1f}%")
    else:
        print(f"➖ 理论ROI无变化")
    
    # 最终建议
    print("\n" + "-" * 70)
    if (results_cal['mae'] < results_raw['mae'] and 
        results_cal['roi'] > results_raw['roi']):
        print("🏆 推荐使用校准版 (+2.7分)")
    elif (results_cal['mae'] > results_raw['mae'] or 
          results_cal['roi'] < results_raw['roi']):
        print("❌ 不推荐校准，保持V3原始版本")
    else:
        print("➖ 校准效果中性，继续用V3原始版观察")
    
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
