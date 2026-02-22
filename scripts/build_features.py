#!/usr/bin/env python3
"""
特征工程 - 为大小分预测构建特征
"""
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
RAW_DIR = DATA_DIR / 'raw'
FEATURES_DIR = DATA_DIR / 'features'
FEATURES_DIR.mkdir(parents=True, exist_ok=True)

def load_games(season='2024-25'):
    """加载比赛数据"""
    # 优先使用清洗后的真实数据
    filepath_clean = RAW_DIR / 'games_2024-25_clean.csv'
    if filepath_clean.exists():
        filepath = filepath_clean
    else:
        filepath = RAW_DIR / f'games_{season}.csv'
    
    df = pd.read_csv(filepath)
    print(f"📊 加载了 {len(df)//2} 场比赛 (来源: {filepath.name})")
    return df

def build_team_rolling_stats(df, windows=[5, 10]):
    """
    构建球队滑动窗口统计
    
    Args:
        df: 比赛数据
        windows: 滑动窗口大小列表
    
    Returns:
        DataFrame: 带滑动统计的数据
    """
    print(f"\n🔧 计算滑动窗口统计 (窗口: {windows})...")
    
    df = df.sort_values(['TEAM_ABBREVIATION', 'GAME_DATE']).copy()
    
    for window in windows:
        # 场均得分
        df[f'pts_last_{window}'] = df.groupby('TEAM_ABBREVIATION')['PTS'].transform(
            lambda x: x.rolling(window, min_periods=1).mean().shift(1)
        )
        
        # 场均命中率
        df[f'fg_pct_last_{window}'] = df.groupby('TEAM_ABBREVIATION')['FG_PCT'].transform(
            lambda x: x.rolling(window, min_periods=1).mean().shift(1)
        )
        
        # 场均篮板
        df[f'reb_last_{window}'] = df.groupby('TEAM_ABBREVIATION')['REB'].transform(
            lambda x: x.rolling(window, min_periods=1).mean().shift(1)
        )
    
    print(f"✅ 添加了 {len(windows) * 3} 个滑动特征")
    return df

def build_matchup_features(df):
    """构建对阵特征"""
    print(f"\n🔧 构建对阵特征...")
    
    # 每场比赛创建一行（合并主客队）
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
            
            # 主队特征
            'home_team': home_team['TEAM_ABBREVIATION'],
            'home_pts_last_5': home_team.get('pts_last_5', 0),
            'home_pts_last_10': home_team.get('pts_last_10', 0),
            'home_fg_pct_last_5': home_team.get('fg_pct_last_5', 0),
            
            # 客队特征
            'away_team': away_team['TEAM_ABBREVIATION'],
            'away_pts_last_5': away_team.get('pts_last_5', 0),
            'away_pts_last_10': away_team.get('pts_last_10', 0),
            'away_fg_pct_last_5': away_team.get('fg_pct_last_5', 0),
            
            # 组合特征
            'combined_pts_last_5': home_team.get('pts_last_5', 0) + away_team.get('pts_last_5', 0),
            'combined_pts_last_10': home_team.get('pts_last_10', 0) + away_team.get('pts_last_10', 0),
        }
        
        games.append(feature)
    
    features_df = pd.DataFrame(games)
    print(f"✅ 构建了 {len(features_df)} 场比赛的特征")
    print(f"   特征维度: {len(features_df.columns)} 列")
    
    return features_df

def save_features(df, filename='features.csv'):
    """保存特征"""
    filepath = FEATURES_DIR / filename
    df.to_csv(filepath, index=False)
    print(f"\n💾 特征已保存: {filepath}")
    print(f"   大小: {filepath.stat().st_size / 1024:.1f} KB")

def main():
    print("\n" + "="*70)
    print("🔧 NBA特征工程")
    print("="*70 + "\n")
    
    # 加载原始数据
    df = load_games()
    
    # 构建滑动统计
    df = build_team_rolling_stats(df, windows=[5, 10])
    
    # 构建对阵特征
    features_df = build_matchup_features(df)
    
    # 保存
    save_features(features_df)
    
    # 显示样本
    print(f"\n📋 特征样本 (前3场):")
    print(features_df[['game_date', 'home_team', 'away_team', 'total_points', 
                       'combined_pts_last_5', 'combined_pts_last_10']].head(3).to_string())
    
    print("\n" + "="*70)
    print("✅ 特征工程完成")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
