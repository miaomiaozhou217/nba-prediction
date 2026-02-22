#!/usr/bin/env python3
"""
实时预测 V2 - 使用增强模型预测今日比赛
"""
import pandas as pd
import pickle
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / 'models'
DATA_DIR = PROJECT_ROOT / 'data'

def load_model():
    """加载V2模型"""
    filepath = MODELS_DIR / 'total_points_model_v2.pkl'
    
    if not filepath.exists():
        print(f"❌ 模型不存在: {filepath}")
        print("   请先运行: python scripts/train_model_v2.py")
        return None
    
    with open(filepath, 'rb') as f:
        model_package = pickle.load(f)
    
    print(f"✅ 模型已加载 (V{model_package['version']})")
    print(f"   训练时间: {model_package['timestamp'][:19]}")
    print(f"   交叉验证MAE: {sum(model_package['cv_scores'])/len(model_package['cv_scores']):.2f}")
    
    return model_package

def get_team_recent_stats(team_abbr):
    """
    获取球队近期统计（从历史数据计算）
    实际使用中应该接入实时API
    """
    # 加载历史数据
    filepath = DATA_DIR / 'raw' / 'games_2024-25_clean.csv'
    df = pd.read_csv(filepath)
    
    # 该球队最近的比赛
    team_games = df[df['TEAM_ABBREVIATION'] == team_abbr].sort_values('GAME_DATE')
    
    if len(team_games) < 3:
        print(f"⚠️  {team_abbr} 数据不足")
        return None
    
    # 计算统计
    stats = {
        'pts_last_3': team_games['PTS'].tail(3).mean(),
        'pts_last_5': team_games['PTS'].tail(5).mean(),
        'pts_last_10': team_games['PTS'].tail(10).mean(),
        'opp_pts_last_5': team_games['OPP_PTS'].tail(5).mean(),
        'pts_std_5': team_games['PTS'].tail(5).std() if len(team_games) >= 5 else 0,
    }
    
    # 主客场分组
    is_home = team_games['MATCHUP'].str.contains('vs')
    home_games = team_games[is_home]
    away_games = team_games[~is_home]
    
    stats['pts_last_5_home'] = home_games['PTS'].tail(5).mean() if len(home_games) >= 5 else stats['pts_last_5']
    stats['pts_last_5_away'] = away_games['PTS'].tail(5).mean() if len(away_games) >= 5 else stats['pts_last_5']
    
    return stats

def build_matchup_features(home_team, away_team):
    """构建对阵特征"""
    print(f"\n🔧 构建特征: {home_team} vs {away_team}...")
    
    # 获取两队统计
    home_stats = get_team_recent_stats(home_team)
    away_stats = get_team_recent_stats(away_team)
    
    if home_stats is None or away_stats is None:
        return None
    
    # 构建特征向量（顺序必须和训练时一致！）
    features = {
        'home_pts_last_3': home_stats['pts_last_3'],
        'home_pts_last_5': home_stats['pts_last_5'],
        'home_pts_last_10': home_stats['pts_last_10'],
        'home_opp_pts_last_5': home_stats['opp_pts_last_5'],
        'home_pts_std_5': home_stats['pts_std_5'],
        'home_pts_last_5_home': home_stats['pts_last_5_home'],
        
        'away_pts_last_3': away_stats['pts_last_3'],
        'away_pts_last_5': away_stats['pts_last_5'],
        'away_pts_last_10': away_stats['pts_last_10'],
        'away_opp_pts_last_5': away_stats['opp_pts_last_5'],
        'away_pts_std_5': away_stats['pts_std_5'],
        'away_pts_last_5_away': away_stats['pts_last_5_away'],
        
        'combined_pts_last_3': home_stats['pts_last_3'] + away_stats['pts_last_3'],
        'combined_pts_last_5': home_stats['pts_last_5'] + away_stats['pts_last_5'],
        'combined_pts_last_10': home_stats['pts_last_10'] + away_stats['pts_last_10'],
        
        'home_off_vs_away_def': home_stats['pts_last_5'] - away_stats['opp_pts_last_5'],
        'away_off_vs_home_def': away_stats['pts_last_5'] - home_stats['opp_pts_last_5'],
        'home_field_advantage': home_stats['pts_last_5_home'] - away_stats['pts_last_5_away'],
    }
    
    print(f"   主队近5场均分: {home_stats['pts_last_5']:.1f}")
    print(f"   客队近5场均分: {away_stats['pts_last_5']:.1f}")
    print(f"   组合预期: {features['combined_pts_last_5']:.1f}")
    
    return pd.DataFrame([features])

def make_prediction(model_package, features_df):
    """预测并给出建议"""
    model = model_package['model']
    feature_cols = model_package['feature_cols']
    
    # 确保特征顺序一致
    X = features_df[feature_cols]
    
    # 预测
    predicted_total = model.predict(X)[0]
    
    return predicted_total

def generate_recommendation(predicted_total, lines=[215, 220, 225, 230]):
    """生成下注建议"""
    print(f"\n🎯 预测总分: {predicted_total:.1f}")
    print(f"\n💰 下注建议:")
    print(f"{'盘口':>8s} {'预测':>10s} {'建议':>10s} {'偏离':>10s} {'信心度':>10s} {'决策':>15s}")
    print("-" * 70)
    
    recommendations = []
    
    for line in lines:
        prediction = 'OVER' if predicted_total > line else 'UNDER'
        deviation = predicted_total - line
        confidence = abs(deviation) / line * 100
        
        # 决策逻辑
        if line == 215 and confidence > 3:  # 盘口215是金矿
            decision = "🏆 强烈推荐"
        elif confidence > 5:
            decision = "💰 建议下注"
        elif confidence > 2:
            decision = "⚠️  可考虑"
        else:
            decision = "❌ 不建议"
        
        print(f"{line:8d} {prediction:>10s} {prediction:>10s} {deviation:>+9.1f} {confidence:>9.1f}% {decision:>15s}")
        
        recommendations.append({
            'line': line,
            'prediction': prediction,
            'confidence': confidence,
            'decision': decision
        })
    
    # 最佳建议
    best = max(recommendations, key=lambda x: x['confidence'])
    print(f"\n   🎯 最佳下注点: 盘口 {best['line']}, {best['prediction']} (信心度 {best['confidence']:.1f}%)")

def predict_matchup(home_team, away_team):
    """预测单场比赛"""
    print("\n" + "="*70)
    print(f"🏀 NBA大小分预测: {home_team} vs {away_team}")
    print("="*70)
    
    # 加载模型
    model_package = load_model()
    if model_package is None:
        return
    
    # 构建特征
    features_df = build_matchup_features(home_team, away_team)
    if features_df is None:
        print("❌ 特征构建失败")
        return
    
    # 预测
    predicted_total = make_prediction(model_package, features_df)
    
    # 建议
    generate_recommendation(predicted_total)
    
    print("\n" + "="*70)
    print("⚠️  风险提示:")
    print("   1. 本预测基于历史数据，不保证准确性")
    print("   2. 模型在盘口215的准确率最高（70.8%，ROI +35.2%）")
    print("   3. 建议单场下注不超过资金池的5%")
    print("="*70 + "\n")

def main():
    parser = argparse.ArgumentParser(description='NBA大小分预测 V2')
    parser.add_argument('--home', required=True, help='主队缩写 (e.g., LAL)')
    parser.add_argument('--away', required=True, help='客队缩写 (e.g., GSW)')
    args = parser.parse_args()
    
    predict_matchup(args.home.upper(), args.away.upper())

if __name__ == '__main__':
    # 如果没有参数，运行示例
    import sys
    if len(sys.argv) == 1:
        print("示例用法: python scripts/predict_v2.py --home LAL --away GSW")
        print("\n运行示例预测...")
        predict_matchup('BOS', 'MIA')  # 示例
    else:
        main()
