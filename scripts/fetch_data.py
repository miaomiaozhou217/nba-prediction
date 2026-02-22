#!/usr/bin/env python3
"""
NBA数据获取脚本
从NBA官方API获取比赛数据、球队统计、球员统计
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from nba_api.stats.endpoints import leaguegamefinder, teamgamelogs, leaguedashteamstats
from nba_api.stats.static import teams
import pandas as pd
from tqdm import tqdm
import time

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'raw'
DATA_DIR.mkdir(parents=True, exist_ok=True)

def get_season_games(season='2024-25', max_games=None):
    """
    获取赛季比赛数据
    
    Args:
        season: 赛季（格式: '2024-25'）
        max_games: 最多获取多少场比赛（None=全部）
    
    Returns:
        DataFrame: 比赛数据
    """
    print(f"📥 获取 {season} 赛季比赛数据...")
    
    for attempt in range(3):
        try:
            print(f"  尝试 {attempt + 1}/3...")
            gamefinder = leaguegamefinder.LeagueGameFinder(
                season_nullable=season,
                league_id_nullable='00',  # NBA
                timeout=120  # 增加超时时间
            )
            games = gamefinder.get_data_frames()[0]
            
            if max_games:
                games = games.head(max_games)
            
            print(f"✅ 获取到 {len(games)} 场比赛数据")
            return games
        
        except Exception as e:
            print(f"  ⚠️  失败: {e}")
            if attempt < 2:
                print(f"  等待3秒后重试...")
                time.sleep(3)
            else:
                print(f"❌ 3次尝试均失败")
                return None

def get_team_stats(season='2024-25'):
    """
    获取球队统计数据
    
    Returns:
        DataFrame: 球队赛季统计
    """
    print(f"📥 获取 {season} 球队统计...")
    
    try:
        team_stats = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            per_mode_detailed='PerGame'
        )
        df = team_stats.get_data_frames()[0]
        
        print(f"✅ 获取到 {len(df)} 支球队数据")
        return df
    
    except Exception as e:
        print(f"❌ 获取失败: {e}")
        return None

def save_data(df, filename):
    """保存数据到CSV"""
    if df is None or df.empty:
        print(f"⚠️  数据为空，跳过保存")
        return
    
    filepath = DATA_DIR / filename
    df.to_csv(filepath, index=False)
    print(f"💾 已保存: {filepath}")
    print(f"   行数: {len(df)}, 列数: {len(df.columns)}")

def main():
    parser = argparse.ArgumentParser(description='获取NBA数据')
    parser.add_argument('--season', default='2024-25', help='赛季 (e.g., 2024-25)')
    parser.add_argument('--games', type=int, help='最多获取比赛数（可选）')
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🏀 NBA数据获取工具")
    print("="*70 + "\n")
    
    # 获取比赛数据
    games = get_season_games(args.season, args.games)
    if games is not None:
        save_data(games, f'games_{args.season}.csv')
    
    time.sleep(1)  # API限流
    
    # 获取球队统计
    team_stats = get_team_stats(args.season)
    if team_stats is not None:
        save_data(team_stats, f'team_stats_{args.season}.csv')
    
    print("\n✅ 数据获取完成")
    print(f"数据目录: {DATA_DIR}")

if __name__ == '__main__':
    main()
