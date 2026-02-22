#!/usr/bin/env python3
"""
实时预测今日NBA比赛大小分
"""
import pandas as pd
import pickle
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / 'models'
FEATURES_DIR = PROJECT_ROOT / 'data' / 'features'

def load_model():
    """加载训练好的模型"""
    filepath = MODELS_DIR / 'total_points_model.pkl'
    
    if not filepath.exists():
        print(f"❌ 模型不存在: {filepath}")
        print("请先运行: python scripts/train_model.py")
        return None
    
    with open(filepath, 'rb') as f:
        model_package = pickle.load(f)
    
    print(f"✅ 模型已加载")
    print(f"   版本: {model_package['version']}")
    print(f"   训练时间: {model_package['timestamp'][:19]}")
    
    return model_package

def get_today_games():
    """
    获取今日比赛
    （这里用示例数据，实际应该调用NBA API）
    """
    print(f"\n📅 今日比赛 ({datetime.now().strftime('%Y-%m-%d')})")
    print("   (使用示例数据)")
    
    # 示例比赛
    games = [
        {
            'home_team': 'LAL',
            'away_team': 'GSW',
            'home_pts_last_5': 112.5,
            'home_pts_last_10': 110.2,
            'home_fg_pct_last_5': 0.465,
            'away_pts_last_5': 115.8,
            'away_pts_last_10': 113.4,
            'away_fg_pct_last_5': 0.478,
        },
        {
            'home_team': 'BOS',
            'away_team': 'MIA',
            'home_pts_last_5': 118.2,
            'home_pts_last_10': 116.9,
            'home_fg_pct_last_5': 0.492,
            'away_pts_last_5': 108.4,
            'away_pts_last_10': 107.2,
            'away_fg_pct_last_5': 0.445,
        },
    ]
    
    return pd.DataFrame(games)

def make_predictions(model_package, games_df, line=220):
    """预测比赛"""
    model = model_package['model']
    feature_cols = model_package['feature_cols']
    
    # 添加组合特征
    games_df['combined_pts_last_5'] = games_df['home_pts_last_5'] + games_df['away_pts_last_5']
    games_df['combined_pts_last_10'] = games_df['home_pts_last_10'] + games_df['away_pts_last_10']
    
    # 预测
    X = games_df[feature_cols]
    predictions = model.predict(X)
    
    # 添加预测结果
    games_df['predicted_total'] = predictions
    games_df['prediction'] = games_df['predicted_total'].apply(lambda x: 'OVER' if x > line else 'UNDER')
    games_df['confidence'] = abs(games_df['predicted_total'] - line) / line * 100
    
    return games_df

def display_predictions(games_df, line=220):
    """显示预测结果"""
    print(f"\n{'='*70}")
    print(f"🎯 预测结果 (盘口线: {line})")
    print(f"{'='*70}\n")
    
    for idx, row in games_df.iterrows():
        print(f"比赛 {idx + 1}: {row['home_team']} vs {row['away_team']}")
        print(f"  预测总分: {row['predicted_total']:.1f}")
        print(f"  建议: {row['prediction']}")
        print(f"  偏离盘口: {row['predicted_total'] - line:+.1f} 分")
        print(f"  信心度: {row['confidence']:.1f}%")
        
        # 建议下注金额（凯利准则的简化版）
        if row['confidence'] > 5:  # 高置信度
            bet_suggestion = "💰 建议下注 (高信心)"
        elif row['confidence'] > 2:
            bet_suggestion = "⚠️  可考虑 (中等信心)"
        else:
            bet_suggestion = "❌ 不建议 (信心不足)"
        
        print(f"  {bet_suggestion}")
        print()

def main():
    print("\n" + "="*70)
    print("🏀 NBA大小分实时预测")
    print("="*70 + "\n")
    
    # 加载模型
    model_package = load_model()
    if model_package is None:
        return
    
    # 获取今日比赛
    games_df = get_today_games()
    print(f"   今日场次: {len(games_df)}")
    
    # 预测
    predictions = make_predictions(model_package, games_df, line=220)
    
    # 显示结果
    display_predictions(predictions)
    
    print("="*70)
    print("✅ 预测完成")
    print("="*70 + "\n")
    
    print("⚠️  风险提示:")
    print("   1. 本预测仅供参考，不构成投资建议")
    print("   2. 博彩有风险，请谨慎决策")
    print("   3. 建议单场下注不超过资金池的5%")

if __name__ == '__main__':
    main()
