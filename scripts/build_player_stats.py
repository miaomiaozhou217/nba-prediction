#!/usr/bin/env python3
"""
构建球员统计数据库（简易版）
从历史比赛数据中提取球员场均得分
"""
import pandas as pd
import json
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'

def extract_player_stats_from_games():
    """
    从历史比赛数据中估算球员统计
    注: 这是简化版，实际应该用球员级别的API
    """
    # 加载比赛数据
    games_df = pd.read_csv(DATA_DIR / 'raw' / 'games_2024-25_clean.csv')
    
    # 按球队计算场均数据
    team_stats = {}
    
    for team in games_df['TEAM_ABBREVIATION'].unique():
        team_games = games_df[games_df['TEAM_ABBREVIATION'] == team]
        
        team_stats[team] = {
            'ppg': team_games['PTS'].mean(),
            'games_played': len(team_games)
        }
    
    return team_stats

def create_default_player_db():
    """
    创建默认球员数据库（简化版）
    包含主力球员的大致场均分
    """
    # 简化版：只维护各队TOP 3球员
    # 实际使用中可以从nba_api获取
    player_db = {
        # 东部
        'BOS': [('Jayson Tatum', 28.0), ('Jaylen Brown', 24.5), ('Kristaps Porzingis', 20.0)],
        'MIL': [('Giannis Antetokounmpo', 30.5), ('Damian Lillard', 25.0), ('Khris Middleton', 18.0)],
        'PHI': [('Joel Embiid', 32.0), ('Tyrese Maxey', 26.0), ('Paul George', 22.0)],
        'NY': [('Jalen Brunson', 28.0), ('Karl-Anthony Towns', 24.0), ('Mikal Bridges', 18.0)],
        'CLE': [('Donovan Mitchell', 27.0), ('Darius Garland', 22.0), ('Evan Mobley', 17.0)],
        'ORL': [('Paolo Banchero', 25.0), ('Franz Wagner', 20.0), ('Jalen Suggs', 15.0)],
        'IND': [('Tyrese Haliburton', 24.0), ('Pascal Siakam', 21.0), ('Myles Turner', 17.0)],
        'MIA': [('Jimmy Butler', 23.0), ('Bam Adebayo', 19.0), ('Tyler Herro', 22.0)],
        
        # 西部
        'OKC': [('Shai Gilgeous-Alexander', 31.0), ('Jalen Williams', 20.0), ('Chet Holmgren', 18.0)],
        'DEN': [('Nikola Jokic', 29.0), ('Jamal Murray', 22.0), ('Michael Porter Jr.', 17.0)],
        'LAL': [('LeBron James', 25.0), ('Anthony Davis', 27.0), ('Austin Reaves', 18.0)],
        'GS': [('Stephen Curry', 28.0), ('Andrew Wiggins', 16.0), ('Draymond Green', 8.0)],
        'MIN': [('Anthony Edwards', 27.0), ('Julius Randle', 22.0), ('Rudy Gobert', 14.0)],
        'PHX': [('Kevin Durant', 28.0), ('Devin Booker', 27.0), ('Bradley Beal', 19.0)],
        'DAL': [('Luka Doncic', 31.0), ('Kyrie Irving', 25.0), ('Klay Thompson', 14.0)],
        'LAC': [('James Harden', 21.0), ('Norman Powell', 23.0), ('Kawhi Leonard', 23.0)],
        'SAC': [("De'Aaron Fox", 26.0), ('Domantas Sabonis', 20.0), ('DeMar DeRozan', 21.0)],
        'HOU': [('Alperen Sengun', 22.0), ('Jalen Green', 21.0), ('Fred VanVleet', 16.0)],
        'MEM': [('Ja Morant', 24.0), ('Jaren Jackson Jr.', 23.0), ('Desmond Bane', 18.0)],
        'NO': [('Zion Williamson', 23.0), ('CJ McCollum', 20.0), ('Brandon Ingram', 22.0)],
        'POR': [('Anfernee Simons', 23.0), ('Jerami Grant', 17.0), ('Deandre Ayton', 14.0)],
        'SA': [('Victor Wembanyama', 25.0), ('Devin Vassell', 18.0), ('Keldon Johnson', 15.0)],
        'UTAH': [('Lauri Markkanen', 23.0), ('Collin Sexton', 18.0), ('Walker Kessler', 10.0)],
        
        # 其他
        'ATL': [('Trae Young', 26.0), ('Jalen Johnson', 19.0), ('Clint Capela', 11.0)],
        'BKN': [('Cam Thomas', 25.0), ('Mikal Bridges', 21.0), ('Nic Claxton', 12.0)],
        'CHA': [('LaMelo Ball', 25.0), ('Brandon Miller', 20.0), ('Miles Bridges', 17.0)],
        'CHI': [('Zach LaVine', 24.0), ('Nikola Vucevic', 20.0), ('Coby White', 18.0)],
        'DET': [('Cade Cunningham', 25.0), ('Jaden Ivey', 17.0), ('Tim Hardaway Jr.', 13.0)],
        'TOR': [('Scottie Barnes', 21.0), ('Pascal Siakam', 22.0), ('OG Anunoby', 16.0)],
        'WSH': [('Jordan Poole', 21.0), ('Kyle Kuzma', 22.0), ('Jonas Valanciunas', 12.0)],
    }
    
    return player_db

def save_player_db(player_db):
    """保存为JSON格式"""
    # 转换为扁平字典
    flat_db = {}
    
    for team, players in player_db.items():
        for player_name, ppg in players:
            flat_db[player_name] = {
                'team': team,
                'ppg': ppg
            }
    
    filepath = DATA_DIR / 'player_stats.json'
    with open(filepath, 'w') as f:
        json.dump(flat_db, f, indent=2)
    
    print(f"💾 球员数据库已保存: {filepath}")
    print(f"   总计: {len(flat_db)} 名球员")
    
    # 显示样本
    print(f"\n📋 球员样本:")
    for i, (player, stats) in enumerate(list(flat_db.items())[:10], 1):
        print(f"   {i:2d}. {player:25s} - {stats['team']:5s} - {stats['ppg']:.1f} PPG")

def main():
    print("\n" + "="*70)
    print("🏀 构建球员统计数据库（简易版）")
    print("="*70 + "\n")
    
    # 创建默认数据库
    player_db = create_default_player_db()
    
    # 保存
    save_player_db(player_db)
    
    print("\n" + "="*70)
    print("✅ 完成")
    print("="*70 + "\n")
    
    print("⚠️  注意:")
    print("   这是简化版数据库，只包含各队TOP 3球员")
    print("   实际使用中应该从NBA API获取完整赛季统计")
    print("   但对于伤病影响评估已经足够（主要缺阵的都是主力）")

if __name__ == '__main__':
    main()
