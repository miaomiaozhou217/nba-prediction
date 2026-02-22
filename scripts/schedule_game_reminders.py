#!/usr/bin/env python3
"""
为今日/明日所有比赛创建赛前20分钟提醒
使用OpenClaw cron系统
"""
import json
import requests
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def get_games_for_date(date_str):
    """获取指定日期的比赛"""
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        events = data.get('events', [])
        
        games = []
        for event in events:
            comp = event['competitions'][0]
            
            home = comp['competitors'][0] if comp['competitors'][0]['homeAway'] == 'home' else comp['competitors'][1]
            away = comp['competitors'][1] if comp['competitors'][1]['homeAway'] == 'away' else comp['competitors'][0]
            
            # 比赛时间（UTC）
            game_time = datetime.strptime(event['date'], '%Y-%m-%dT%H:%M%SZ')
            
            # 转换到Adelaide时间
            adelaide_time = game_time + timedelta(hours=10, minutes=30)
            
            # 提醒时间（提前20分钟）
            reminder_time = adelaide_time - timedelta(minutes=20)
            
            games.append({
                'game_id': event['id'],
                'home_team': home['team']['abbreviation'],
                'away_team': away['team']['abbreviation'],
                'game_time_utc': game_time,
                'game_time_adelaide': adelaide_time,
                'reminder_time': reminder_time
            })
        
        return games
    
    except Exception as e:
        print(f"❌ 获取比赛失败: {e}")
        return []

def create_reminder_job(game):
    """使用OpenClaw cron创建提醒任务"""
    reminder_time = game['reminder_time']
    
    # ISO 8601格式
    reminder_iso = reminder_time.isoformat()
    
    job_name = f"NBA提醒: {game['away_team']}@{game['home_team']}"
    
    message = f"""🔔 **比赛即将开始！**

📅 比赛: {game['away_team']} @ {game['home_team']}
⏰ 开赛时间: {game['game_time_adelaide'].strftime('%H:%M')}
🏥 最新伤病: 请确认

执行赛前预测:
cd ~/projects/nba && \\
python3 scripts/fetch_injuries.py && \\
python3 scripts/predict_v3.py --home {game['home_team']} --away {game['away_team']}
"""
    
    # 使用OpenClaw cron API
    job = {
        "name": job_name,
        "schedule": {
            "kind": "at",
            "at": reminder_iso
        },
        "payload": {
            "kind": "agentTurn",
            "message": message,
            "timeoutSeconds": 120
        },
        "sessionTarget": "isolated",
        "delivery": {
            "mode": "announce",
            "channel": "telegram",
            "to": "REDACTED"
        },
        "enabled": True
    }
    
    return job

def add_cron_job_via_cli(job):
    """通过OpenClaw CLI添加cron任务"""
    try:
        # 将job转为JSON
        job_json = json.dumps(job)
        
        # 调用openclaw cron add
        result = subprocess.run(
            ['openclaw', 'cron', 'add'],
            input=job_json,
            text=True,
            capture_output=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    
    except Exception as e:
        return False, str(e)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='设置比赛前20分钟提醒')
    parser.add_argument('--date', help='日期 (YYYYMMDD), 默认明天', default=None)
    parser.add_argument('--dry-run', action='store_true', help='仅生成定义，不实际添加')
    args = parser.parse_args()
    
    # 确定日期（默认明天）
    if args.date:
        date_str = args.date
    else:
        tomorrow = datetime.now() + timedelta(days=1)
        date_str = tomorrow.strftime('%Y%m%d')
    
    print("\n" + "="*70)
    print(f"⏰ 设置比赛提醒 - {date_str}")
    print("="*70 + "\n")
    
    # 获取比赛
    print(f"📥 获取比赛列表...")
    games = get_games_for_date(date_str)
    
    if not games:
        print("❌ 没有比赛")
        return
    
    print(f"✅ 找到 {len(games)} 场比赛\n")
    
    # 为每场比赛创建提醒
    print(f"⏰ 创建提醒任务...\n")
    
    jobs_created = []
    jobs_added = 0
    
    for i, game in enumerate(games, 1):
        # 只为未来的比赛创建提醒
        if game['reminder_time'] > datetime.now():
            job = create_reminder_job(game)
            
            print(f"[{i}/{len(games)}] {game['away_team']} @ {game['home_team']}")
            print(f"  开赛: {game['game_time_adelaide'].strftime('%H:%M')}")
            print(f"  提醒: {game['reminder_time'].strftime('%H:%M')}")
            
            if not args.dry_run:
                # 实际添加到OpenClaw cron
                success, output = add_cron_job_via_cli(job)
                
                if success:
                    print(f"  ✅ 已添加到cron系统\n")
                    jobs_added += 1
                else:
                    print(f"  ❌ 添加失败: {output[:100]}\n")
            else:
                print(f"  💾 已生成定义（dry-run模式）\n")
            
            jobs_created.append(job)
        else:
            print(f"[{i}/{len(games)}] {game['away_team']} @ {game['home_team']} - 已过期，跳过\n")
    
    # 保存所有job定义（备份）
    if jobs_created:
        jobs_file = PROJECT_ROOT / 'data' / f'reminder_jobs_{date_str}.json'
        with open(jobs_file, 'w') as f:
            json.dump(jobs_created, f, indent=2)
        
        print(f"💾 任务定义已保存: {jobs_file}")
    
    if not args.dry_run:
        print(f"\n✅ 完成: 成功添加 {jobs_added}/{len(jobs_created)} 个提醒任务")
    else:
        print(f"\n✅ 完成: 生成了 {len(jobs_created)} 个任务定义（dry-run模式）")
    
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
