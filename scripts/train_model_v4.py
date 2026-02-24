#!/usr/bin/env python3
"""
训练 V4 模型 (24维特征)
对比V3模型 (20维) 验证防守+节奏特征的效果

评估指标:
- RMSE (越低越好)
- MAE (平均绝对误差, 目标: <15分)
- R² (拟合优度, 越接近1越好)
- Line 215 Accuracy (总分预测准确度)
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
import pickle

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
FEATURES_DIR = DATA_DIR / 'features'
MODELS_DIR = PROJECT_ROOT / 'models'
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def load_features():
    """加载V4特征数据"""
    filepath = FEATURES_DIR / 'features_v4.csv'
    df = pd.read_csv(filepath)
    print(f"📊 加载了 {len(df)} 场比赛的特征 (V4: 24维)")
    return df

def prepare_data(df):
    """准备训练数据"""
    # 删除缺失值过多的行
    df = df.dropna(subset=['combined_pts_last_3', 'combined_pts_last_5'])
    
    # 特征列 (V4: 24个)
    feature_cols = [
        # V2基础 (18个)
        'home_pts_last_3', 'home_pts_last_5', 'home_pts_last_10',
        'home_opp_pts_last_5', 'home_pts_std_5', 'home_pts_last_5_home',
        'away_pts_last_3', 'away_pts_last_5', 'away_pts_last_10',
        'away_opp_pts_last_5', 'away_pts_std_5', 'away_pts_last_5_away',
        'combined_pts_last_3', 'combined_pts_last_5', 'combined_pts_last_10',
        'home_off_vs_away_def', 'away_off_vs_home_def', 'home_field_advantage',
        # V3伤病 (2个)
        'home_injury_impact', 'away_injury_impact',
        # V4防守节奏 (4个)
        'home_def_rating_last_10', 'away_def_rating_last_10',
        'home_pace_last_10', 'away_pace_last_10'
    ]
    
    X = df[feature_cols].fillna(0)
    y = df['total_points']
    
    # 保留元数据用于评估
    metadata = df[['game_id', 'game_date', 'home_team', 'away_team', 'total_points']].copy()
    
    print(f"\n✅ 数据准备完成:")
    print(f"   训练样本: {len(X)} 场")
    print(f"   特征维度: {len(feature_cols)} 维")
    print(f"   - V2基础: 18维")
    print(f"   - V3伤病: 2维")
    print(f"   - V4防守节奏: 4维")
    
    return X, y, metadata, feature_cols

def train_model(X, y, metadata):
    """时间序列交叉验证训练 + 真正的out-of-sample测试"""
    print(f"\n🔧 训练 XGBoost 模型 (5折时间序列交叉验证)...\n")
    
    tscv = TimeSeriesSplit(n_splits=5)
    fold_results = []
    all_predictions = []  # 收集所有fold的预测
    
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
        
        rmse = np.sqrt(mean_squared_error(y_val, y_pred))
        mae = mean_absolute_error(y_val, y_pred)
        r2 = r2_score(y_val, y_pred)
        
        print(f"   Fold {fold}: RMSE={rmse:.2f}, MAE={mae:.2f}, R²={r2:.3f}")
        fold_results.append({'rmse': rmse, 'mae': mae, 'r2': r2})
        
        # 保存验证集预测（用于out-of-sample评估）
        for idx, pred in zip(val_idx, y_pred):
            all_predictions.append({
                'index': idx,
                'actual': y.iloc[idx],
                'predicted': pred,
                'game_id': metadata.iloc[idx]['game_id'],
                'game_date': metadata.iloc[idx]['game_date'],
                'home_team': metadata.iloc[idx]['home_team'],
                'away_team': metadata.iloc[idx]['away_team']
            })
    
    # 汇总CV结果
    avg_rmse = np.mean([r['rmse'] for r in fold_results])
    avg_mae = np.mean([r['mae'] for r in fold_results])
    avg_r2 = np.mean([r['r2'] for r in fold_results])
    
    print(f"\n📊 交叉验证平均结果:")
    print(f"   RMSE: {avg_rmse:.2f} 分")
    print(f"   MAE:  {avg_mae:.2f} 分")
    print(f"   R²:   {avg_r2:.3f}")
    
    # 用全部数据训练最终模型
    print(f"\n🔧 使用全部数据训练最终模型...")
    final_model = xgb.XGBRegressor(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=6,
        min_child_weight=3,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1
    )
    final_model.fit(X, y, verbose=False)
    
    return final_model, {'avg_rmse': avg_rmse, 'avg_mae': avg_mae, 'avg_r2': avg_r2}, all_predictions

def evaluate_line_accuracy(all_predictions):
    """评估盘口准确率 (Line 215) - 使用CV的out-of-sample预测"""
    print(f"\n🎯 评估盘口准确率 (Line 215, Out-of-Sample)...")
    
    # 使用CV期间的验证集预测（真正的out-of-sample）
    eval_df = pd.DataFrame(all_predictions)
    eval_df['total_points'] = eval_df['actual']
    eval_df['error'] = eval_df['total_points'] - eval_df['predicted']
    
    # Line 215 准确率
    correct_215 = sum((eval_df['total_points'] > 215) == (eval_df['predicted'] > 215))
    accuracy_215 = correct_215 / len(eval_df) * 100
    
    # 投注模拟 (只押>5%信心的)
    eval_df['confidence'] = abs(eval_df['predicted'] - 215) / 215 * 100
    high_confidence = eval_df[eval_df['confidence'] > 5].copy()
    
    if len(high_confidence) > 0:
        correct_hc = sum((high_confidence['total_points'] > 215) == (high_confidence['predicted'] > 215))
        accuracy_hc = correct_hc / len(high_confidence) * 100
        roi_hc = (correct_hc - len(high_confidence)) / len(high_confidence) * 95  # -5% vig
        
        print(f"\n   全部比赛 ({len(eval_df)}场):")
        print(f"   - Line 215 准确率: {accuracy_215:.1f}%")
        print(f"   - 平均误差: {eval_df['error'].abs().mean():.2f} 分")
        
        print(f"\n   高信心比赛 (>{5}%, {len(high_confidence)}场):")
        print(f"   - Line 215 准确率: {accuracy_hc:.1f}%")
        print(f"   - 理论ROI: {roi_hc:+.1f}%")
    else:
        print(f"\n   全部比赛 ({len(eval_df)}场):")
        print(f"   - Line 215 准确率: {accuracy_215:.1f}%")
        print(f"   ⚠️  无高信心比赛 (全部<5%)")
    
    return {
        'accuracy_215': accuracy_215,
        'avg_error': eval_df['error'].abs().mean(),
        'high_confidence_games': len(high_confidence),
        'high_confidence_accuracy': accuracy_hc if len(high_confidence) > 0 else 0,
        'roi': roi_hc if len(high_confidence) > 0 else 0
    }

def show_feature_importance(model, feature_cols):
    """显示特征重要性"""
    print(f"\n📊 特征重要性 Top 10:")
    
    importance = model.feature_importances_
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    for idx, row in feature_importance.head(10).iterrows():
        print(f"   {row['feature']:30s} {row['importance']:.1%}")
    
    # 分组统计
    v2_importance = feature_importance[feature_importance['feature'].isin(feature_cols[:18])]['importance'].sum()
    v3_importance = feature_importance[feature_importance['feature'].isin(feature_cols[18:20])]['importance'].sum()
    v4_importance = feature_importance[feature_importance['feature'].isin(feature_cols[20:])]['importance'].sum()
    
    print(f"\n   特征组贡献:")
    print(f"   - V2基础特征: {v2_importance:.1%}")
    print(f"   - V3伤病特征: {v3_importance:.1%}")
    print(f"   - 🆕 V4防守节奏: {v4_importance:.1%}")

def save_model(model, filename='total_points_model_v4.pkl'):
    """保存模型"""
    filepath = MODELS_DIR / filename
    with open(filepath, 'wb') as f:
        pickle.dump(model, f)
    print(f"\n💾 模型已保存: {filepath}")
    print(f"   大小: {filepath.stat().st_size / 1024:.1f} KB")

def compare_with_v3():
    """加载V3模型对比"""
    v3_model_path = MODELS_DIR / 'total_points_model_v3.pkl'
    
    if not v3_model_path.exists():
        print(f"\n⚠️  V3模型不存在，无法对比")
        return
    
    print(f"\n📊 V3模型基线指标 (参考):")
    print(f"   - MAE: 17.31 分")
    print(f"   - Line 215准确率: 73.5%")
    print(f"   - 理论ROI: +40.3%")

def main():
    print("\n" + "="*70)
    print("🔧 训练 NBA V4 模型 (防守效率 + 节奏)")
    print("="*70 + "\n")
    
    # 加载数据
    df = load_features()
    X, y, metadata, feature_cols = prepare_data(df)
    
    # 对比V3基线
    compare_with_v3()
    
    # 训练模型
    model, cv_results, all_predictions = train_model(X, y, metadata)
    
    # 评估盘口准确率（用CV的out-of-sample预测）
    line_results = evaluate_line_accuracy(all_predictions)
    
    # 特征重要性
    show_feature_importance(model, feature_cols)
    
    # 保存模型
    save_model(model)
    
    # 最终对比
    print(f"\n" + "="*70)
    print(f"📊 V3 vs V4 对比:")
    print(f"="*70)
    print(f"\n{'指标':<20s} {'V3 (20维)':<15s} {'V4 (24维)':<15s} {'改进':<10s}")
    print(f"{'-'*70}")
    
    v4_mae_str = f"{cv_results['avg_mae']:.2f} 分"
    v4_acc_str = f"{line_results['accuracy_215']:.1f}%"
    v4_roi_str = f"{line_results['roi']:+.1f}%"
    mae_diff = 17.31 - cv_results['avg_mae']
    acc_diff = line_results['accuracy_215'] - 73.5
    roi_diff = line_results['roi'] - 40.3
    
    print(f"{'MAE':<20s} {'17.31 分':<15s} {v4_mae_str:<15s} {mae_diff:+.2f} 分")
    print(f"{'Line 215准确率':<20s} {'73.5%':<15s} {v4_acc_str:<15s} {acc_diff:+.1f}%")
    print(f"{'理论ROI':<20s} {'+40.3%':<15s} {v4_roi_str:<15s} {roi_diff:+.1f}%")
    
    print(f"\n" + "="*70)
    print(f"✅ V4模型训练完成")
    print(f"="*70 + "\n")

if __name__ == '__main__':
    main()
