#!/usr/bin/env python3
"""
清洗ESPN数据 - 移除全明星赛等非常规赛数据
"""
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'raw'

def clean_data():
    # 加载数据
    filepath = DATA_DIR / 'games_2024-25_espn.csv'
    df = pd.read_csv(filepath)
    
    print(f"📊 原始数据: {len(df)} 行 ({len(df)//2} 场)")
    
    # 移除全明星赛等特殊赛事
    all_star_teams = ['STARS', 'WORLD', 'STRIPES', 'LEGENDS', 'TEAM']
    df_clean = df[~df['TEAM_ABBREVIATION'].isin(all_star_teams)]
    
    print(f"✅ 清洗后: {len(df_clean)} 行 ({len(df_clean)//2} 场)")
    print(f"   移除了 {len(df) - len(df_clean)} 行")
    
    # 统计
    print(f"\n📈 数据统计:")
    print(f"   日期范围: {df_clean['GAME_DATE'].min()} → {df_clean['GAME_DATE'].max()}")
    print(f"   场均得分: {df_clean['PTS'].mean():.1f}")
    print(f"   得分范围: {df_clean['PTS'].min()} - {df_clean['PTS'].max()}")
    
    # 保存
    output_path = DATA_DIR / 'games_2024-25_clean.csv'
    df_clean.to_csv(output_path, index=False)
    print(f"\n💾 已保存: {output_path}")
    
    return df_clean

if __name__ == '__main__':
    clean_data()
