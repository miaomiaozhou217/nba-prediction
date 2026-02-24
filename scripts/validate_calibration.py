#!/usr/bin/env python3
"""
验证校准效果 - 对比V3原始 vs V3校准版的准确率和ROI
"""
import pandas as pd
import pickle
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / 'models'
DATA_DIR = PROJECT_ROOT / 'data'

def load_model():
    """加载V3模型"""
    filepath = MODELS_DIR / 'total_points_model_v3.pkl'
    with open(filepath, 'rb') as f:
        return pickle.load(f)

def load_features():
    """加载特征数据"""
    filepath = DATA_DIR / 'features' / 'features_v3.csv'
    return pd.read_csv(filepath)

def evaluate_predictions(df, calibration=0):
    """评估预测准确率和ROI"""
    # Line 215准确率
    correct_215 = sum((df['total_points'] > 215) == (df['predicted'] > 215))
    accuracy_215 = correct_215 / len(df) * 100
    
    # Line 220
    correct_220 = sum((df['total_points'] > 220) == (df['predicted'] > 220))
    accuracy_220 = correct_220 / len(df) * 100
    
    # Line 225
    correct_225 = sum((df['total_points'] > 225) == (df['predicted'] > 225))
    accuracy_225 = correct_225 / len(df) * 100
    
    # 高信心下注模拟（>5%）
    df['confidence'] = abs(df['predicted'] - 215) / 215 * 100
    high_conf = df[df['confidence'] > 5].copy()
    
    if len(high_conf) > 0:
        correct_hc = sum((high_conf['total_points'] > 215) == (high_conf['predicted'] > 215))
        accuracy_hc = correct_hc / len(high_conf) * 100
        roi_hc = (correct_hc - len(high_conf)) / len(high_conf) * 95  # -5% vig
    else:
        accuracy_hc = 0
        roi_hc = 0
    
    # MAE
    mae = df['error'].abs().mean()
    
    return {
        'accuracy_215': accuracy_215,
        'accuracy_220': accuracy_220,
        'accuracy_225': accuracy_225,
        'high_conf_games': len(high_conf),
        'high_conf_accuracy': accuracy_hc,
        'roi': roi_hc,
        'mae': mae,
        'avg_error': df['error'].mean()  # 平均偏差（正=高估，负=低估）
    }

def main():
    print("\n" + "="*70)
    print("📊 验证校准效果: V3原始 vs V3校准(+2.7)")
    print("="*70 + "\n")
    
    # 加载模型和数据
    model_pkg = load_model()
    features_df = load_features()
    
    # 删除缺失值
    features_df = features_df.dropna(subset=['combined_pts_last_3', 'combined_pts_last_5'])
    
    # 准备特征
    feature_cols = model_pkg['feature_cols']
    X = features_df[feature_cols].fillna(0)
    y_true = features_df['total_points']
    
    # 原始预测
    y_pred_raw = model_pkg['model'].predict(X)
    
    # 校准预测
    y_pred_calibrated = y_pred_raw + 2.7
    
    # 评估原始版
    df_raw = pd.DataFrame({
        'total_points': y_true,
        'predicted': y_pred_raw,
        'error': y_true - y_pred_raw
    })
    results_raw = evaluate_predictions(df_raw)
    
    # 评估校准版
    df_cal = pd.DataFrame({
        'total_points': y_true,
        'predicted': y_pred_calibrated,
        'error': y_true - y_pred_calibrated
    })
    results_cal = evaluate_predictions(df_cal, calibration=2.7)
    
    # 对比表格
    print(f"{'指标':<25s} {'V3原始':<15s} {'V3校准(+2.7)':<15s} {'改进':<10s}")
    print("-" * 70)
    
    metrics = [
        ('MAE (平均绝对误差)', 'mae', '分'),
        ('平均偏差 (系统误差)', 'avg_error', '分'),
        ('Line 215准确率', 'accuracy_215', '%'),
        ('Line 220准确率', 'accuracy_220', '%'),
        ('Line 225准确率', 'accuracy_225', '%'),
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
    else:
        print(f"⚠️  Line 215准确率下降 {results_cal['accuracy_215'] - results_raw['accuracy_215']:.1f}%")
    
    if results_cal['roi'] > results_raw['roi']:
        print(f"✅ 理论ROI提升 {results_cal['roi'] - results_raw['roi']:.1f}%")
    else:
        print(f"⚠️  理论ROI下降 {results_cal['roi'] - results_raw['roi']:.1f}%")
    
    print("\n" + "="*70 + "\n")

if __name__ == '__main__':
    main()
