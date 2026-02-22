#!/usr/bin/env python3
"""
模型训练 - XGBoost预测大小分
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import pickle

# 尝试导入XGBoost，如果没有就用简单的线性回归
try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except ImportError:
    from sklearn.linear_model import LinearRegression
    HAS_XGB = False
    print("⚠️  XGBoost未安装，使用LinearRegression替代")
    print("   安装XGBoost: pip3 install xgboost --user")

PROJECT_ROOT = Path(__file__).parent.parent
FEATURES_DIR = PROJECT_ROOT / 'data' / 'features'
MODELS_DIR = PROJECT_ROOT / 'models'
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def load_features():
    """加载特征"""
    filepath = FEATURES_DIR / 'features.csv'
    df = pd.read_csv(filepath)
    print(f"📊 加载了 {len(df)} 场比赛特征")
    return df

def prepare_data(df):
    """准备训练数据"""
    print(f"\n🔧 准备训练数据...")
    
    # 删除缺失值过多的行
    df = df.dropna()
    print(f"   删除缺失值后: {len(df)} 场")
    
    # 特征列
    feature_cols = [
        'home_pts_last_5', 'home_pts_last_10', 'home_fg_pct_last_5',
        'away_pts_last_5', 'away_pts_last_10', 'away_fg_pct_last_5',
        'combined_pts_last_5', 'combined_pts_last_10'
    ]
    
    X = df[feature_cols]
    y = df['total_points']  # 预测总分
    
    print(f"   特征维度: {X.shape}")
    print(f"   目标范围: {y.min():.0f} - {y.max():.0f}, 均值: {y.mean():.1f}")
    
    return X, y, feature_cols

def train_model(X, y):
    """训练模型"""
    print(f"\n🤖 训练模型...")
    
    # 划分训练/测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    print(f"   训练集: {len(X_train)} 场")
    print(f"   测试集: {len(X_test)} 场")
    
    # 训练
    if HAS_XGB:
        model = XGBRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=4,
            random_state=42
        )
        model_name = 'XGBoost'
    else:
        model = LinearRegression()
        model_name = 'LinearRegression'
    
    print(f"   使用模型: {model_name}")
    model.fit(X_train, y_train)
    
    # 评估
    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)
    
    train_mae = mean_absolute_error(y_train, train_pred)
    test_mae = mean_absolute_error(y_test, test_pred)
    test_rmse = np.sqrt(mean_squared_error(y_test, test_pred))
    test_r2 = r2_score(y_test, test_pred)
    
    print(f"\n📊 模型评估:")
    print(f"   训练MAE: {train_mae:.2f} 分")
    print(f"   测试MAE: {test_mae:.2f} 分")
    print(f"   测试RMSE: {test_rmse:.2f} 分")
    print(f"   测试R²: {test_r2:.3f}")
    
    return model, X_test, y_test, test_pred

def evaluate_betting_strategy(y_true, y_pred, line=220):
    """评估博彩策略"""
    print(f"\n🎯 博彩策略评估 (盘口线: {line})...")
    
    # 模型预测Over/Under
    pred_over = y_pred > line
    actual_over = y_true > line
    
    # 计算准确率
    correct = (pred_over == actual_over).sum()
    total = len(y_true)
    accuracy = correct / total * 100
    
    print(f"   预测准确率: {accuracy:.1f}% ({correct}/{total})")
    
    # 盈利计算（假设赔率1.91）
    wins = correct
    losses = total - correct
    roi = (wins * 0.91 - losses) / total * 100
    
    print(f"   盈利: {wins}胜 / {losses}负")
    print(f"   ROI: {roi:+.1f}%")
    
    # 如果准确率>52.4%才有盈利
    breakeven = 52.4
    if accuracy > breakeven:
        print(f"   ✅ 策略有效！(超过盈亏平衡点{breakeven}%)")
    else:
        print(f"   ❌ 策略无效 (需超过{breakeven}%)")

def save_model(model, feature_cols):
    """保存模型"""
    filepath = MODELS_DIR / 'total_points_model.pkl'
    
    model_package = {
        'model': model,
        'feature_cols': feature_cols,
        'version': '1.0',
        'timestamp': pd.Timestamp.now().isoformat()
    }
    
    with open(filepath, 'wb') as f:
        pickle.dump(model_package, f)
    
    print(f"\n💾 模型已保存: {filepath}")
    print(f"   大小: {filepath.stat().st_size / 1024:.1f} KB")

def main():
    print("\n" + "="*70)
    print("🤖 NBA大小分预测模型训练")
    print("="*70 + "\n")
    
    # 加载特征
    df = load_features()
    
    # 准备数据
    X, y, feature_cols = prepare_data(df)
    
    # 训练模型
    model, X_test, y_test, test_pred = train_model(X, y)
    
    # 评估博彩策略
    evaluate_betting_strategy(y_test.values, test_pred, line=220)
    
    # 保存模型
    save_model(model, feature_cols)
    
    print("\n" + "="*70)
    print("✅ 训练完成")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
