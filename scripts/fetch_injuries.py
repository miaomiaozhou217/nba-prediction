#!/usr/bin/env python3
"""
获取NBA每日伤病报告
数据源: Basketball Reference
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from pathlib import Path
import time

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'injuries'
DATA_DIR.mkdir(parents=True, exist_ok=True)

def fetch_injury_report():
    """爬取Basketball Reference伤病报告"""
    url = 'https://www.basketball-reference.com/friv/injuries.fcgi'
    
    print(f"📥 获取伤病报告: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        injuries = []
        
        # 找到伤病表格
        table = soup.find('table', {'id': 'injuries'})
        
        if not table:
            print("⚠️  未找到伤病表格")
            return pd.DataFrame()
        
        # 解析每一行 (新结构: <th>球员</th> <td>球队</td> <td>日期</td> <td>描述</td>)
        for row in table.find_all('tr'):
            # 第一列是<th>（球员），后面是<td>
            player_cell = row.find('th')
            cols = row.find_all('td')
            
            if player_cell and len(cols) >= 3:
                # 提取球员名字
                player = player_cell.text.strip()
                
                # 提取球队（第1个td）
                team_cell = cols[0]
                team_link = team_cell.find('a')
                if team_link and 'href' in team_link.attrs:
                    team = team_link['href'].split('/teams/')[1].split('/')[0]
                else:
                    team = team_cell.text.strip()
                
                # 提取更新日期（第2个td）
                update_date = cols[1].text.strip()
                
                # 提取伤病描述（第3个td）
                description = cols[2].text.strip()
                
                # 判断状态
                desc_lower = description.lower()
                if 'out' in desc_lower:
                    status = 'Out'
                elif 'doubtful' in desc_lower:
                    status = 'Doubtful'
                elif 'questionable' in desc_lower:
                    status = 'Questionable'
                elif 'probable' in desc_lower:
                    status = 'Probable'
                else:
                    status = 'Unknown'
                
                injuries.append({
                    'team': team.upper(),
                    'player': player,
                    'status': status,
                    'description': description,
                    'update_date': update_date,
                    'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
        
        df = pd.DataFrame(injuries)
        print(f"✅ 获取到 {len(df)} 条伤病记录")
        
        return df
    
    except Exception as e:
        print(f"❌ 爬取失败: {e}")
        return pd.DataFrame()

def save_injury_report(df):
    """保存伤病报告"""
    if df.empty:
        print("⚠️  没有数据可保存")
        return
    
    today = datetime.now().strftime('%Y-%m-%d')
    filepath = DATA_DIR / f'injuries_{today}.csv'
    
    df.to_csv(filepath, index=False)
    print(f"\n💾 已保存: {filepath}")
    print(f"   文件大小: {filepath.stat().st_size / 1024:.1f} KB")
    
    # 同时保存为latest.csv（方便调用）
    latest_path = DATA_DIR / 'injuries_latest.csv'
    df.to_csv(latest_path, index=False)
    print(f"   最新版本: {latest_path}")

def show_summary(df):
    """显示伤病摘要"""
    if df.empty:
        return
    
    print(f"\n📊 伤病摘要:")
    print(f"   总计: {len(df)} 人")
    
    # 按状态分组
    status_counts = df['status'].value_counts()
    for status, count in status_counts.items():
        print(f"   {status}: {count} 人")
    
    # 按球队分组
    print(f"\n   受影响球队: {df['team'].nunique()} 支")
    
    # 显示确定缺阵的球员
    out_players = df[df['status'] == 'Out']
    if len(out_players) > 0:
        print(f"\n🚨 确定缺阵球员 ({len(out_players)} 人):")
        for _, row in out_players.head(10).iterrows():
            print(f"   {row['team']:5s} - {row['player']:20s} ({row['description'][:40]}...)")
        
        if len(out_players) > 10:
            print(f"   ... 还有 {len(out_players) - 10} 人")

def main():
    print("\n" + "="*70)
    print("🏥 NBA伤病报告爬虫")
    print("="*70 + "\n")
    
    # 获取数据
    df = fetch_injury_report()
    
    # 显示摘要
    show_summary(df)
    
    # 保存
    save_injury_report(df)
    
    print("\n" + "="*70)
    print("✅ 完成")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
