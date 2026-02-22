#!/usr/bin/env python3
"""
模型训练 V2 - 增强版
- 使用V2特征（18维）
- 时间序列交叉验证
- 特征重要性分析
- 多阈值回测
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import pickle

try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except ImportError:
    from sklearn.linear_model import LinearRegression
    HAS_XGB = False
    print("⚠️  XGBoost未安装，使用LinearRegression")

PROJECT_ROOT = Path(__file__).parent.parent
FEATURES_DIR = PROJECT_ROOT / 'data' / 'features'
MODELS_DIR = PROJECT_ROOT / 'models'
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def load_features():
    """加载V2特征"""
    filepath = FEATURES_DIR / 'features_v3.csv'
    df = pd.read_csv(filepath)
    print(f"📊 加载了 {len(df)} 场比赛特征（V2增强版）")
    return df

def prepare_data(df):
    """准备训练数据"""
    print(f"\n🔧 准备训练数据...")
    
    # 按日期排序（时间序列重要！）
    df = df.sort_values('game_date').copy()
    
    # 删除缺失值
    df = df.dropna()
    print(f"   删除缺失值后: {len(df)} 场")
    
    # 特征列（排除元数据和标签）
    exclude_cols = ['game_id', 'game_date', 'home_team', 'away_team', 
                    'total_points', 'home_points', 'away_points']
    feature_cols = [c for c in df.columns if c not in exclude_cols]
    
    X = df[feature_cols]
    y = df['total_points']
    
    print(f"   特征维度: {X.shape}")
    print(f"   目标范围: {y.min():.0f} - {y.max():.0f}, 均值: {y.mean():.1f}")
    print(f"   使用特征: {len(feature_cols)} 个")
    
    return X, y, feature_cols, df['game_date']

def time_series_cv(X, y, dates, n_splits=5):
    """时间序列交叉验证"""
    print(f"\n🔄 时间序列交叉验证 ({n_splits} 折)...")
    
    tscv = TimeSeriesSplit(n_splits=n_splits)
    cv_scores = []
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        if HAS_XGB:
            model = XGBRegressor(n_estimators=100, learning_rate=0.05, 
                                max_depth=4, random_state=42)
        else:
            model = LinearRegression()
        
        model.fit(X_train, y_train)
        val_pred = model.predict(X_val)
        
        mae = mean_absolute_error(y_val, val_pred)
        cv_scores.append(mae)
        
        val_dates = dates.iloc[val_idx]
        print(f"   Fold {fold}: MAE={mae:.2f} (验证集: {val_dates.min()} ~ {val_dates.max()})")
    
    print(f"\n   平均MAE: {np.mean(cv_scores):.2f} ± {np.std(cv_scores):.2f}")
    
    return cv_scores

def train_final_model(X, y):
    """训练最终模型"""
    print(f"\n🤖 训练最终模型...")
    
    # 80/20 时间序列分割
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"   训练集: {len(X_train)} 场")
    print(f"   测试集: {len(X_test)} 场")
    
    if HAS_XGB:
        model = XGBRegressor(
            n_estimators=150,
            learning_rate=0.05,
            max_depth=5,
            min_child_weight=3,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        model_name = 'XGBoost'
    else:
        model = LinearRegression()
        model_name = 'LinearRegression'
    
    print(f"   模型: {model_name}")
    model.fit(X_train, y_train)
    
    # 评估
    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)
    
    train_mae = mean_absolute_error(y_train, train_pred)
    test_mae = mean_absolute_error(y_test, test_pred)
    test_rmse = np.sqrt(mean_squared_error(y_test, test_pred))
    test_r2 = r2_score(y_test, test_pred)
    
    print(f"\n📊 模型性能:")
    print(f"   训练MAE: {train_mae:.2f} 分")
    print(f"   测试MAE: {test_mae:.2f} 分")
    print(f"   测试RMSE: {test_rmse:.2f} 分")
    print(f"   测试R²: {test_r2:.3f}")
    
    return model, X_test, y_test, test_pred

def analyze_feature_importance(model, feature_cols):
    """特征重要性分析"""
    if not HAS_XGB:
        print("\n⚠️  LinearRegression不支持特征重要性分析")
        return
    
    print(f"\n📊 特征重要性 TOP 10:")
    
    importance = model.feature_importances_
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    for i, row in feature_importance.head(10).iterrows():
        print(f"   {row['feature']:30s} {row['importance']:.4f}")
    
    return feature_importance

def evaluate_betting_strategy(y_true, y_pred, lines=[215, 220, 225, 230]):
    """多盘口线回测"""
    print(f"\n🎯 博彩策略回测 (多盘口线)...\n")
    
    results = []
    
    for line in lines:
        pred_over = y_pred > line
        actual_over = y_true > line
        
        correct = (pred_over == actual_over).sum()
        total = len(y_true)
        accuracy = correct / total * 100
        
        wins = correct
        losses = total - correct
        roi = (wins * 0.91 - losses) / total * 100
        
        results.append({
            'line': line,
            'accuracy': accuracy,
            'wins': wins,
            'losses': losses,
            'roi': roi
        })
        
        status = "✅" if accuracy > 52.4 else "❌"
        print(f"   盘口 {line}: {accuracy:.1f}% ({wins}胜/{losses}负) ROI: {roi:+.1f}% {status}")
    
    # 找最佳盘口
    best = max(results, key=lambda x: x['roi'])
    print(f"\n   🏆 最佳盘口: {best['line']} (ROI {best['roi']:+.1f}%, 准确率 {best['accuracy']:.1f}%)")
    
    return results

def save_model(model, feature_cols, cv_scores):
    """保存模型"""
    filepath = MODELS_DIR / 'total_points_model_v3.pkl'
    
    model_package = {
        'model': model,
        'feature_cols': feature_cols,
        'cv_scores': cv_scores,
        'version': '2.0',
        'timestamp': pd.Timestamp.now().isoformat()
    }
    
    with open(filepath, 'wb') as f:
        pickle.dump(model_package, f)
    
    print(f"\n💾 模型已保存: {filepath}")
    print(f"   大小: {filepath.stat().st_size / 1024:.1f} KB")

def main():
    print("\n" + "="*70)
    print("🤖 NBA大小分预测模型训练 V3 (集成伤病)")
    print("="*70 + "\n")
    
    # 加载特征
    df = load_features()
    
    # 准备数据
    X, y, feature_cols, dates = prepare_data(df)
    
    # 时间序列交叉验证
    cv_scores = time_series_cv(X, y, dates, n_splits=5)
    
    # 训练最终模型
    model, X_test, y_test, test_pred = train_final_model(X, y)
    
    # 特征重要性
    analyze_feature_importance(model, feature_cols)
    
    # 博彩策略评估
    evaluate_betting_strategy(y_test.values, test_pred)
    
    # 保存模型
    save_model(model, feature_cols, cv_scores)
    
    print("\n" + "="*70)
    print("✅ 训练完成")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
