#!/usr/bin/env python3
"""
特征工程 V3 - 集成伤病数据
新增特征: home_injury_impact, away_injury_impact (+2维,总20维)
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
RAW_DIR = DATA_DIR / 'raw'
FEATURES_DIR = DATA_DIR / 'features'
INJURIES_DIR = DATA_DIR / 'injuries'
FEATURES_DIR.mkdir(parents=True, exist_ok=True)

# 加载球员数据库
with open(DATA_DIR / 'player_stats.json', 'r') as f:
    PLAYER_STATS = json.load(f)

def load_games():
    """加载真实数据"""
    filepath = RAW_DIR / 'games_2024-25_clean.csv'
    df = pd.read_csv(filepath)
    print(f"📊 加载了 {len(df)//2} 场比赛")
    return df

def load_injuries():
    """加载最新伤病报告"""
    filepath = INJURIES_DIR / 'injuries_latest.csv'
    
    if not filepath.exists():
        print("⚠️  伤病数据不存在，运行: python scripts/fetch_injuries.py")
        return pd.DataFrame()
    
    df = pd.read_csv(filepath)
    # 只保留确定缺阵的球员
    df = df[df['status'] == 'Out']
    
    print(f"🏥 加载了 {len(df)} 条伤病记录（确定缺阵）")
    
    return df

def calc_injury_impact(team, injuries_df):
    """
    计算球队伤病影响分
    公式: sum(缺阵球员PPG) / 5 (简化版)
    """
    # 找出该队缺阵球员
    team_injuries = injuries_df[injuries_df['team'] == team]
    
    total_impact = 0
    affected_players = []
    
    for _, injury in team_injuries.iterrows():
        player = injury['player']
        
        # 从数据库查找球员统计
        if player in PLAYER_STATS:
            ppg = PLAYER_STATS[player]['ppg']
            impact = ppg / 5  # 简化公式
            total_impact += impact
            affected_players.append(f"{player}({ppg:.1f}PPG)")
    
    if affected_players:
        print(f"      {team}: {', '.join(affected_players[:2])} → 影响-{total_impact:.1f}分")
    
    return total_impact

def build_team_stats(df):
    """构建球队滑动窗口统计（复用V2逻辑）"""
    print(f"\n🔧 计算球队滑动统计...")
    
    df = df.sort_values(['TEAM_ABBREVIATION', 'GAME_DATE']).copy()
    
    for window in [3, 5, 10]:
        df[f'pts_last_{window}'] = df.groupby('TEAM_ABBREVIATION')['PTS'].transform(
            lambda x: x.rolling(window, min_periods=1).mean().shift(1)
        )
        df[f'opp_pts_last_{window}'] = df.groupby('TEAM_ABBREVIATION')['OPP_PTS'].transform(
            lambda x: x.rolling(window, min_periods=1).mean().shift(1)
        )
        df[f'pts_std_{window}'] = df.groupby('TEAM_ABBREVIATION')['PTS'].transform(
            lambda x: x.rolling(window, min_periods=2).std().shift(1)
        )
    
    df['is_home'] = df['MATCHUP'].str.contains('vs')
    df['pts_last_5_home'] = df[df['is_home']].groupby('TEAM_ABBREVIATION')['PTS'].transform(
        lambda x: x.rolling(5, min_periods=1).mean().shift(1)
    )
    df['pts_last_5_away'] = df[~df['is_home']].groupby('TEAM_ABBREVIATION')['PTS'].transform(
        lambda x: x.rolling(5, min_periods=1).mean().shift(1)
    )
    
    df['pts_last_5_home'].fillna(df['pts_last_5'], inplace=True)
    df['pts_last_5_away'].fillna(df['pts_last_5'], inplace=True)
    
    print(f"✅ 添加了 {len([c for c in df.columns if 'last' in c or 'std' in c])} 个统计特征")
    
    return df

def build_matchup_features(df, injuries_df):
    """构建对阵特征（V3 - 新增伤病）"""
    print(f"\n🔧 构建对阵特征（含伤病数据）...")
    
    if not injuries_df.empty:
        print(f"   伤病影响计算:")
    
    games = []
    
    for game_id in df['GAME_ID'].unique():
        game_df = df[df['GAME_ID'] == game_id]
        
        if len(game_df) != 2:
            continue
        
        team1 = game_df.iloc[0]
        team2 = game_df.iloc[1]
        
        is_home_1 = 'vs' in team1['MATCHUP']
        home_team = team1 if is_home_1 else team2
        away_team = team2 if is_home_1 else team1
        
        # V2特征
        feature = {
            'game_id': game_id,
            'game_date': team1['GAME_DATE'],
            'total_points': team1['PTS'] + team2['PTS'],
            'home_points': home_team['PTS'],
            'away_points': away_team['PTS'],
            'home_team': home_team['TEAM_ABBREVIATION'],
            'home_pts_last_3': home_team.get('pts_last_3', 0),
            'home_pts_last_5': home_team.get('pts_last_5', 0),
            'home_pts_last_10': home_team.get('pts_last_10', 0),
            'home_opp_pts_last_5': home_team.get('opp_pts_last_5', 0),
            'home_pts_std_5': home_team.get('pts_std_5', 0),
            'home_pts_last_5_home': home_team.get('pts_last_5_home', 0),
            'away_team': away_team['TEAM_ABBREVIATION'],
            'away_pts_last_3': away_team.get('pts_last_3', 0),
            'away_pts_last_5': away_team.get('pts_last_5', 0),
            'away_pts_last_10': away_team.get('pts_last_10', 0),
            'away_opp_pts_last_5': away_team.get('opp_pts_last_5', 0),
            'away_pts_std_5': away_team.get('pts_std_5', 0),
            'away_pts_last_5_away': away_team.get('pts_last_5_away', 0),
            'combined_pts_last_3': home_team.get('pts_last_3', 0) + away_team.get('pts_last_3', 0),
            'combined_pts_last_5': home_team.get('pts_last_5', 0) + away_team.get('pts_last_5', 0),
            'combined_pts_last_10': home_team.get('pts_last_10', 0) + away_team.get('pts_last_10', 0),
            'home_off_vs_away_def': home_team.get('pts_last_5', 0) - away_team.get('opp_pts_last_5', 0),
            'away_off_vs_home_def': away_team.get('pts_last_5', 0) - home_team.get('opp_pts_last_5', 0),
            'home_field_advantage': home_team.get('pts_last_5_home', 0) - away_team.get('pts_last_5_away', 0),
        }
        
        # 🏥 V3新增: 伤病影响
        if not injuries_df.empty:
            feature['home_injury_impact'] = calc_injury_impact(home_team['TEAM_ABBREVIATION'], injuries_df)
            feature['away_injury_impact'] = calc_injury_impact(away_team['TEAM_ABBREVIATION'], injuries_df)
        else:
            feature['home_injury_impact'] = 0
            feature['away_injury_impact'] = 0
        
        games.append(feature)
    
    features_df = pd.DataFrame(games)
    print(f"\n✅ 构建了 {len(features_df)} 场比赛的特征")
    print(f"   特征维度: {len(features_df.columns)} 列")
    
    return features_df

def save_features(df, filename='features_v3.csv'):
    """保存特征"""
    filepath = FEATURES_DIR / filename
    df.to_csv(filepath, index=False)
    print(f"\n💾 特征已保存: {filepath}")
    print(f"   大小: {filepath.stat().st_size / 1024:.1f} KB")

def main():
    print("\n" + "="*70)
    print("🔧 NBA特征工程 V3 (集成伤病数据)")
    print("="*70 + "\n")
    
    # 加载原始数据
    df = load_games()
    
    # 加载伤病数据
    injuries_df = load_injuries()
    
    # 构建球队统计
    df = build_team_stats(df)
    
    # 构建对阵特征（含伤病）
    features_df = build_matchup_features(df, injuries_df)
    
    # 保存
    save_features(features_df)
    
    # 显示样本
    print(f"\n📋 特征样本 (前3场):")
    display_cols = ['game_date', 'home_team', 'away_team', 'total_points', 
                    'combined_pts_last_5', 'home_injury_impact', 'away_injury_impact']
    print(features_df[display_cols].head(3).to_string(index=False))
    
    # 显示特征列表
    print(f"\n📊 特征列表 (共 {len(features_df.columns)} 列):")
    feature_cols = [c for c in features_df.columns if c not in ['game_id', 'game_date', 'home_team', 'away_team', 'total_points', 'home_points', 'away_points']]
    print(f"   基础特征 (V2): 18 个")
    print(f"   🏥 伤病特征 (V3): 2 个 (home/away_injury_impact)")
    print(f"   总计: {len(feature_cols)} 个")
    
    print("\n" + "="*70)
    print("✅ 特征工程完成")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
