#!/usr/bin/env python3
"""
从ESPN API获取NBA真实历史数据
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'raw'
DATA_DIR.mkdir(parents=True, exist_ok=True)

def fetch_games_on_date(date_str):
    """
    获取指定日期的比赛数据
    
    Args:
        date_str: 格式 YYYYMMDD (e.g., '20260220')
    
    Returns:
        list: 比赛列表
    """
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        games = []
        for event in data.get('events', []):
            comp = event['competitions'][0]
            home_team = comp['competitors'][0] if comp['competitors'][0]['homeAway'] == 'home' else comp['competitors'][1]
            away_team = comp['competitors'][1] if comp['competitors'][1]['homeAway'] == 'away' else comp['competitors'][0]
            
            game = {
                'GAME_ID': event['id'],
                'GAME_DATE': datetime.strptime(event['date'], '%Y-%m-%dT%H:%M%SZ').strftime('%Y-%m-%d'),
                'HOME_TEAM': home_team['team']['abbreviation'],
                'AWAY_TEAM': away_team['team']['abbreviation'],
                'HOME_PTS': int(home_team.get('score', 0)),
                'AWAY_PTS': int(away_team.get('score', 0)),
                'TOTAL_PTS': int(home_team.get('score', 0)) + int(away_team.get('score', 0))
            }
            
            # 跳过未开始的比赛
            if game['HOME_PTS'] == 0 and game['AWAY_PTS'] == 0:
                continue
                
            games.append(game)
        
        return games
    
    except Exception as e:
        print(f"  ❌ {date_str}: {e}")
        return []

def fetch_historical_games(days_back=90):
    """
    获取过去N天的比赛数据
    
    Args:
        days_back: 回溯天数
    
    Returns:
        DataFrame: 所有比赛数据
    """
    print(f"📥 获取过去 {days_back} 天的NBA比赛数据...\n")
    
    all_games = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    current_date = start_date
    progress_bar = tqdm(total=days_back, desc="获取进度")
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        games = fetch_games_on_date(date_str)
        
        if games:
            all_games.extend(games)
            progress_bar.set_postfix({'日期': current_date.strftime('%Y-%m-%d'), '比赛': len(games)})
        
        current_date += timedelta(days=1)
        progress_bar.update(1)
        time.sleep(0.1)  # 避免API限流
    
    progress_bar.close()
    
    df = pd.DataFrame(all_games)
    print(f"\n✅ 共获取 {len(df)} 场比赛")
    
    return df

def expand_to_team_rows(df):
    """
    将每场比赛展开为2行（主队 + 客队）
    保持与原有格式兼容
    """
    print(f"\n🔧 转换为球队格式...")
    
    team_rows = []
    
    for _, row in df.iterrows():
        # 主队行
        team_rows.append({
            'GAME_ID': row['GAME_ID'],
            'GAME_DATE': row['GAME_DATE'],
            'TEAM_ABBREVIATION': row['HOME_TEAM'],
            'MATCHUP': f"{row['HOME_TEAM']} vs. {row['AWAY_TEAM']}",
            'PTS': row['HOME_PTS'],
            'OPP_PTS': row['AWAY_PTS'],
            'FG_PCT': 0.45,  # 默认值（ESPN API没有详细统计）
            'REB': 45  # 默认值
        })
        
        # 客队行
        team_rows.append({
            'GAME_ID': row['GAME_ID'],
            'GAME_DATE': row['GAME_DATE'],
            'TEAM_ABBREVIATION': row['AWAY_TEAM'],
            'MATCHUP': f"{row['AWAY_TEAM']} @ {row['HOME_TEAM']}",
            'PTS': row['AWAY_PTS'],
            'OPP_PTS': row['HOME_PTS'],
            'FG_PCT': 0.45,
            'REB': 45
        })
    
    team_df = pd.DataFrame(team_rows)
    print(f"✅ 转换为 {len(team_df)} 行（{len(df)} 场 × 2 球队）")
    
    return team_df

def save_data(df, filename):
    """保存数据"""
    filepath = DATA_DIR / filename
    df.to_csv(filepath, index=False)
    
    print(f"\n💾 已保存: {filepath}")
    print(f"   文件大小: {filepath.stat().st_size / 1024:.1f} KB")
    print(f"   数据范围: {df['GAME_DATE'].min()} 到 {df['GAME_DATE'].max()}")

def main():
    print("\n" + "="*70)
    print("🏀 ESPN NBA数据获取工具")
    print("="*70 + "\n")
    
    # 获取历史数据（过去90天）
    games_df = fetch_historical_games(days_back=90)
    
    if games_df.empty:
        print("❌ 未获取到任何数据")
        return
    
    # 转换为球队格式
    team_df = expand_to_team_rows(games_df)
    
    # 保存数据
    save_data(team_df, 'games_2024-25_espn.csv')
    
    # 显示样本
    print(f"\n📋 数据样本 (前5场):")
    print(games_df[['GAME_DATE', 'HOME_TEAM', 'AWAY_TEAM', 'HOME_PTS', 'AWAY_PTS', 'TOTAL_PTS']].head(5).to_string(index=False))
    
    print("\n" + "="*70)
    print("✅ 数据获取完成")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
