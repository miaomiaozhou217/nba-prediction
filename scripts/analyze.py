#!/usr/bin/env python3
"""
NBA数据分析脚本 - 大小分规律分析
"""
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'raw'

def load_games(season='2024-25'):
    """加载比赛数据"""
    filepath = DATA_DIR / f'games_{season}.csv'
    if not filepath.exists():
        print(f"❌ 文件不存在: {filepath}")
        print("请先运行: python scripts/create_mock_data.py")
        return None
    
    df = pd.read_csv(filepath)
    print(f"📊 加载了 {len(df)} 行数据 ({len(df)//2} 场比赛)")
    return df

def analyze_totals(df):
    """分析总分分布"""
    print("\n" + "="*70)
    print("📈 总分分布分析")
    print("="*70)
    
    # 每场比赛的总分（合并主客队）
    totals = df.groupby('GAME_ID')['PTS'].sum()
    
    print(f"\n📊 总分统计:")
    print(f"  平均总分: {totals.mean():.1f}")
    print(f"  中位数: {totals.median():.1f}")
    print(f"  标准差: {totals.std():.1f}")
    print(f"  最高: {totals.max():.0f}")
    print(f"  最低: {totals.min():.0f}")
    
    # 分段统计
    print(f"\n📊 总分区间分布:")
    bins = [0, 200, 210, 220, 230, 240, 300]
    labels = ['<200', '200-210', '210-220', '220-230', '230-240', '240+']
    counts = pd.cut(totals, bins=bins, labels=labels).value_counts().sort_index()
    
    for label, count in counts.items():
        pct = count / len(totals) * 100
        print(f"  {label:10s}: {count:3d} 场 ({pct:5.1f}%)")
    
    return totals

def analyze_team_scoring(df):
    """分析各队得分"""
    print("\n" + "="*70)
    print("🏀 球队得分分析")
    print("="*70)
    
    team_stats = df.groupby('TEAM_ABBREVIATION').agg({
        'PTS': ['mean', 'std', 'min', 'max', 'count']
    }).round(1)
    
    team_stats.columns = ['场均得分', '标准差', '最低', '最高', '场次']
    team_stats = team_stats.sort_values('场均得分', ascending=False)
    
    print(f"\n前10名高分球队:")
    print(team_stats.head(10).to_string())
    
    return team_stats

def analyze_over_under_strategy(df):
    """分析简单的Over/Under策略"""
    print("\n" + "="*70)
    print("🎯 简单策略回测")
    print("="*70)
    
    # 计算每场比赛总分
    game_totals = df.groupby('GAME_ID').agg({
        'PTS': 'sum',
        'GAME_DATE': 'first'
    }).reset_index()
    game_totals.columns = ['GAME_ID', 'TOTAL', 'DATE']
    
    # 设定盘口线（通常220左右）
    line = 220
    
    print(f"\n假设盘口线: {line} 分")
    
    # 统计Over/Under比例
    overs = (game_totals['TOTAL'] > line).sum()
    unders = (game_totals['TOTAL'] <= line).sum()
    total_games = len(game_totals)
    
    print(f"\nOver: {overs} 场 ({overs/total_games*100:.1f}%)")
    print(f"Under: {unders} 场 ({unders/total_games*100:.1f}%)")
    
    # 简单策略：如果平均总分 > 盘口，押Over
    avg_total = game_totals['TOTAL'].mean()
    print(f"\n平均总分: {avg_total:.1f}")
    
    if avg_total > line:
        strategy = 'OVER'
        wins = overs
    else:
        strategy = 'UNDER'
        wins = unders
    
    win_rate = wins / total_games * 100
    print(f"\n💡 简单策略: 全押 {strategy}")
    print(f"   胜率: {win_rate:.1f}%")
    print(f"   盈亏: {wins}胜 / {total_games - wins}负")
    
    # 盈利计算（假设赔率1.91，-110美式赔率）
    roi = (wins * 0.91 - (total_games - wins)) / total_games * 100
    print(f"   ROI: {roi:+.1f}%")

def main():
    print("\n" + "="*70)
    print("🏀 NBA大小分数据分析")
    print("="*70 + "\n")
    
    # 加载数据
    df = load_games()
    if df is None:
        return
    
    # 分析总分
    totals = analyze_totals(df)
    
    # 分析球队得分
    team_stats = analyze_team_scoring(df)
    
    # 简单策略回测
    analyze_over_under_strategy(df)
    
    print("\n" + "="*70)
    print("✅ 分析完成")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
