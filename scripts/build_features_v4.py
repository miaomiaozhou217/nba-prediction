#!/usr/bin/env python3
"""
特征工程 V4 - Phase 1: 防守效率 + 节奏
在V3基础上新增4个特征:
- home_def_rating_last_10 (防守效率 = 对手场均得分)
- away_def_rating_last_10
- home_pace_last_10 (节奏 = 双方总分均值)
- away_pace_last_10

总特征: 18 (V2) + 2 (V3伤病) + 4 (V4节奏防守) = 24维
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
    df = df[df['status'] == 'Out']
    print(f"🏥 加载了 {len(df)} 条伤病记录（确定缺阵）")
    
    return df

def calc_injury_impact(team, injuries_df):
    """计算球队伤病影响分"""
    team_injuries = injuries_df[injuries_df['team'] == team]
    
    total_impact = 0
    affected_players = []
    
    for _, injury in team_injuries.iterrows():
        player = injury['player']
        if player in PLAYER_STATS:
            ppg = PLAYER_STATS[player]['ppg']
            impact = ppg / 5
            total_impact += impact
            affected_players.append(f"{player}({ppg:.1f}PPG)")
    
    if affected_players:
        print(f"      {team}: {', '.join(affected_players[:2])} → 影响-{total_impact:.1f}分")
    
    return total_impact

def build_team_stats(df):
    """构建球队滑动窗口统计（V4扩展）"""
    print(f"\n🔧 计算球队滑动统计（含防守&节奏）...")
    
    df = df.sort_values(['TEAM_ABBREVIATION', 'GAME_DATE']).copy()
    
    # V2原有特征
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
    
    # 🆕 V4新增: 防守效率（对手得分越低 = 防守越好）
    df['def_rating_last_10'] = df.groupby('TEAM_ABBREVIATION')['OPP_PTS'].transform(
        lambda x: x.rolling(10, min_periods=1).mean().shift(1)
    )
    
    # 🆕 V4新增: 节奏（总分 = 自己得分 + 对手得分）
    df['total_pts'] = df['PTS'] + df['OPP_PTS']
    df['pace_last_10'] = df.groupby('TEAM_ABBREVIATION')['total_pts'].transform(
        lambda x: x.rolling(10, min_periods=1).mean().shift(1)
    )
    
    print(f"✅ V2特征: {len([c for c in df.columns if 'last' in c or 'std' in c]) - 2} 个")
    print(f"✅ V4新增: def_rating_last_10, pace_last_10 (2个)")
    
    return df

def build_matchup_features(df, injuries_df):
    """构建对阵特征（V4扩展）"""
    print(f"\n🔧 构建对阵特征（V4: 伤病 + 防守 + 节奏）...")
    
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
        
        # V2基础特征
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
        
        # V3伤病特征
        if not injuries_df.empty:
            feature['home_injury_impact'] = calc_injury_impact(home_team['TEAM_ABBREVIATION'], injuries_df)
            feature['away_injury_impact'] = calc_injury_impact(away_team['TEAM_ABBREVIATION'], injuries_df)
        else:
            feature['home_injury_impact'] = 0
            feature['away_injury_impact'] = 0
        
        # 🆕 V4防守 + 节奏特征
        feature['home_def_rating_last_10'] = home_team.get('def_rating_last_10', 0)
        feature['away_def_rating_last_10'] = away_team.get('def_rating_last_10', 0)
        feature['home_pace_last_10'] = home_team.get('pace_last_10', 0)
        feature['away_pace_last_10'] = away_team.get('pace_last_10', 0)
        
        games.append(feature)
    
    features_df = pd.DataFrame(games)
    print(f"\n✅ 构建了 {len(features_df)} 场比赛的特征")
    print(f"   特征维度: {len(features_df.columns)} 列")
    print(f"   - V2基础: 18维")
    print(f"   - V3伤病: 2维")
    print(f"   - V4防守节奏: 4维")
    
    return features_df

def save_features(df, filename='features_v4.csv'):
    """保存特征"""
    filepath = FEATURES_DIR / filename
    df.to_csv(filepath, index=False)
    print(f"\n💾 特征已保存: {filepath}")
    print(f"   大小: {filepath.stat().st_size / 1024:.1f} KB")

def main():
    print("\n" + "="*70)
    print("🔧 NBA特征工程 V4 - Phase 1 (防守效率 + 节奏)")
    print("="*70 + "\n")
    
    df = load_games()
    injuries_df = load_injuries()
    df = build_team_stats(df)
    features_df = build_matchup_features(df, injuries_df)
    save_features(features_df)
    
    # 显示样本
    print(f"\n📋 特征样本 (前3场):")
    display_cols = ['game_date', 'home_team', 'away_team', 'total_points', 
                    'combined_pts_last_5', 'home_def_rating_last_10', 'home_pace_last_10']
    print(features_df[display_cols].head(3).to_string(index=False))
    
    # 特征分组统计
    feature_cols = [c for c in features_df.columns if c not in ['game_id', 'game_date', 'home_team', 'away_team', 'total_points', 'home_points', 'away_points']]
    print(f"\n📊 特征列表 (共 {len(feature_cols)} 个训练特征):")
    print(f"   V2基础: home/away_pts_last_X, combined_pts, off_vs_def, field_advantage (18个)")
    print(f"   V3伤病: home/away_injury_impact (2个)")
    print(f"   🆕 V4防守: home/away_def_rating_last_10 (2个)")
    print(f"   🆕 V4节奏: home/away_pace_last_10 (2个)")
    
    print("\n" + "="*70)
    print("✅ 特征工程 V4 Phase 1 完成")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
