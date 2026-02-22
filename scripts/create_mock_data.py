#!/usr/bin/env python3
"""
创建模拟NBA数据用于测试
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'raw'
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 生成模拟比赛数据
np.random.seed(42)

teams = [
    'LAL', 'GSW', 'BOS', 'MIA', 'PHX', 'DAL', 'DEN', 'MIL', 
    'PHI', 'BKN', 'CHI', 'ATL', 'CLE', 'MEM', 'SAC', 'NYK'
]

num_games = 100
games = []

for i in range(num_games):
    # 随机选两支球队
    team_a, team_b = np.random.choice(teams, 2, replace=False)
    
    # 模拟得分（平均110分，标准差12）
    pts_a = int(np.random.normal(110, 12))
    pts_b = int(np.random.normal(110, 12))
    
    # 总分
    total = pts_a + pts_b
    
    # 主客场
    home_team = team_a
    away_team = team_b
    
    # 日期
    game_date = (datetime.now() - timedelta(days=num_games-i)).strftime('%Y-%m-%d')
    
    # 添加主队数据
    games.append({
        'GAME_ID': f'002{2400000 + i:05d}',
        'GAME_DATE': game_date,
        'TEAM_ABBREVIATION': home_team,
        'TEAM_NAME': f'{home_team} Team',
        'MATCHUP': f'{home_team} vs. {away_team}',
        'WL': 'W' if pts_a > pts_b else 'L',
        'PTS': pts_a,
        'FGM': int(pts_a * 0.38),
        'FGA': int(pts_a * 0.85),
        'FG_PCT': round(0.45 + np.random.uniform(-0.05, 0.05), 3),
        'FG3M': int(pts_a * 0.12),
        'FG3A': int(pts_a * 0.30),
        'FG3_PCT': round(0.36 + np.random.uniform(-0.05, 0.05), 3),
        'REB': int(np.random.normal(45, 5)),
        'AST': int(np.random.normal(25, 5)),
       'TOV': int(np.random.normal(12, 3)),
        'PLUS_MINUS': pts_a - pts_b,
    })
    
    # 添加客队数据  
    games.append({
        'GAME_ID': f'002{2400000 + i:05d}',
        'GAME_DATE': game_date,
        'TEAM_ABBREVIATION': away_team,
        'TEAM_NAME': f'{away_team} Team',
        'MATCHUP': f'{away_team} @ {home_team}',
        'WL': 'W' if pts_b > pts_a else 'L',
        'PTS': pts_b,
        'FGM': int(pts_b * 0.38),
        'FGA': int(pts_b * 0.85),
        'FG_PCT': round(0.45 + np.random.uniform(-0.05, 0.05), 3),
        'FG3M': int(pts_b * 0.12),
        'FG3A': int(pts_b * 0.30),
        'FG3_PCT': round(0.36 + np.random.uniform(-0.05, 0.05), 3),
        'REB': int(np.random.normal(45, 5)),
        'AST': int(np.random.normal(25, 5)),
        'TOV': int(np.random.normal(12, 3)),
        'PLUS_MINUS': pts_b - pts_a,
    })

df = pd.DataFrame(games)

# 保存
filepath = DATA_DIR / 'games_2024-25.csv'
df.to_csv(filepath, index=False)
print(f"✅ 已生成模拟数据: {filepath}")
print(f"   行数: {len(df)}, 列数: {len(df.columns)}")
print(f"   总分范围: {df.groupby('GAME_ID')['PTS'].sum().min():.0f} - {df.groupby('GAME_ID')['PTS'].sum().max():.0f}")
print(f"   总分均值: {df.groupby('GAME_ID')['PTS'].sum().mean():.1f}")
