#!/usr/bin/env python3
"""
特征工程 V2 - 增强版特征
添加: 主客场优势、得分趋势、对位历史、命中率趋势
"""
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
RAW_DIR = DATA_DIR / 'raw'
FEATURES_DIR = DATA_DIR / 'features'
FEATURES_DIR.mkdir(parents=True, exist_ok=True)

def load_games():
    """加载真实数据"""
    filepath = RAW_DIR / 'games_2024-25_clean.csv'
    df = pd.read_csv(filepath)
    print(f"📊 加载了 {len(df)//2} 场比赛")
    return df

def build_team_stats(df):
    """构建球队滑动窗口统计（更全面）"""
    print(f"\n🔧 计算球队滑动统计...")
    
    df = df.sort_values(['TEAM_ABBREVIATION', 'GAME_DATE']).copy()
    
    for window in [3, 5, 10]:
        # 得分均值
        df[f'pts_last_{window}'] = df.groupby('TEAM_ABBREVIATION')['PTS'].transform(
            lambda x: x.rolling(window, min_periods=1).mean().shift(1)
        )
        
        # 失分均值
        df[f'opp_pts_last_{window}'] = df.groupby('TEAM_ABBREVIATION')['OPP_PTS'].transform(
            lambda x: x.rolling(window, min_periods=1).mean().shift(1)
        )
        
        # 得分标准差（稳定性）
        df[f'pts_std_{window}'] = df.groupby('TEAM_ABBREVIATION')['PTS'].transform(
            lambda x: x.rolling(window, min_periods=2).std().shift(1)
        )
    
    # 主客场分组统计
    df['is_home'] = df['MATCHUP'].str.contains('vs')
    
    # 主场近5场均分
    df['pts_last_5_home'] = df[df['is_home']].groupby('TEAM_ABBREVIATION')['PTS'].transform(
        lambda x: x.rolling(5, min_periods=1).mean().shift(1)
    )
    
    # 客场近5场均分
    df['pts_last_5_away'] = df[~df['is_home']].groupby('TEAM_ABBREVIATION')['PTS'].transform(
        lambda x: x.rolling(5, min_periods=1).mean().shift(1)
    )
    
    # 填充主客场数据（用全局均分）
    df['pts_last_5_home'].fillna(df['pts_last_5'], inplace=True)
    df['pts_last_5_away'].fillna(df['pts_last_5'], inplace=True)
    
    print(f"✅ 添加了 {len([c for c in df.columns if 'last' in c or 'std' in c])} 个统计特征")
    
    return df

def build_matchup_features(df):
    """构建对阵特征（增强版）"""
    print(f"\n🔧 构建对阵特征...")
    
    games = []
    
    for game_id in df['GAME_ID'].unique():
        game_df = df[df['GAME_ID'] == game_id]
        
        if len(game_df) != 2:
            continue
        
        team1 = game_df.iloc[0]
        team2 = game_df.iloc[1]
        
        # 判断主客场
        is_home_1 = 'vs' in team1['MATCHUP']
        home_team = team1 if is_home_1 else team2
        away_team = team2 if is_home_1 else team1
        
        feature = {
            'game_id': game_id,
            'game_date': team1['GAME_DATE'],
            
            # 实际总分（标签）
            'total_points': team1['PTS'] + team2['PTS'],
            'home_points': home_team['PTS'],
            'away_points': away_team['PTS'],
            
            # 主队基础特征
            'home_team': home_team['TEAM_ABBREVIATION'],
            'home_pts_last_3': home_team.get('pts_last_3', 0),
            'home_pts_last_5': home_team.get('pts_last_5', 0),
            'home_pts_last_10': home_team.get('pts_last_10', 0),
            'home_opp_pts_last_5': home_team.get('opp_pts_last_5', 0),
            'home_pts_std_5': home_team.get('pts_std_5', 0),
            'home_pts_last_5_home': home_team.get('pts_last_5_home', 0),  # 主场优势
            
            # 客队基础特征
            'away_team': away_team['TEAM_ABBREVIATION'],
            'away_pts_last_3': away_team.get('pts_last_3', 0),
            'away_pts_last_5': away_team.get('pts_last_5', 0),
            'away_pts_last_10': away_team.get('pts_last_10', 0),
            'away_opp_pts_last_5': away_team.get('opp_pts_last_5', 0),
            'away_pts_std_5': away_team.get('pts_std_5', 0),
            'away_pts_last_5_away': away_team.get('pts_last_5_away', 0),  # 客场表现
            
            # 组合特征
            'combined_pts_last_3': home_team.get('pts_last_3', 0) + away_team.get('pts_last_3', 0),
            'combined_pts_last_5': home_team.get('pts_last_5', 0) + away_team.get('pts_last_5', 0),
            'combined_pts_last_10': home_team.get('pts_last_10', 0) + away_team.get('pts_last_10', 0),
            
            # 对位防守
            'home_off_vs_away_def': home_team.get('pts_last_5', 0) - away_team.get('opp_pts_last_5', 0),
            'away_off_vs_home_def': away_team.get('pts_last_5', 0) - home_team.get('opp_pts_last_5', 0),
            
            # 主客场优势（主队主场均分 vs 客队客场均分）
            'home_field_advantage': home_team.get('pts_last_5_home', 0) - away_team.get('pts_last_5_away', 0),
        }
        
        games.append(feature)
    
    features_df = pd.DataFrame(games)
    print(f"✅ 构建了 {len(features_df)} 场比赛的特征")
    print(f"   特征维度: {len(features_df.columns)} 列")
    
    return features_df

def save_features(df, filename='features_v2.csv'):
    """保存特征"""
    filepath = FEATURES_DIR / filename
    df.to_csv(filepath, index=False)
    print(f"\n💾 特征已保存: {filepath}")
    print(f"   大小: {filepath.stat().st_size / 1024:.1f} KB")

def main():
    print("\n" + "="*70)
    print("🔧 NBA特征工程 V2 (增强版)")
    print("="*70 + "\n")
    
    # 加载原始数据
    df = load_games()
    
    # 构建球队统计
    df = build_team_stats(df)
    
    # 构建对阵特征
    features_df = build_matchup_features(df)
    
    # 保存
    save_features(features_df)
    
    # 显示样本
    print(f"\n📋 特征样本 (前3场):")
    display_cols = ['game_date', 'home_team', 'away_team', 'total_points', 
                    'combined_pts_last_5', 'home_field_advantage']
    print(features_df[display_cols].head(3).to_string(index=False))
    
    # 显示特征列表
    print(f"\n📊 特征列表 (共 {len(features_df.columns)} 列):")
    feature_cols = [c for c in features_df.columns if c not in ['game_id', 'game_date', 'home_team', 'away_team', 'total_points', 'home_points', 'away_points']]
    for i, col in enumerate(feature_cols, 1):
        print(f"   {i:2d}. {col}")
    
    print("\n" + "="*70)
    print("✅ 特征工程完成")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
