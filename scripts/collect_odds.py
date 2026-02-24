#!/usr/bin/env python3
"""
NBA盘口数据收集器
使用The Odds API免费plan（500 credits/月）
每天运行1次，收集当天/明天所有NBA比赛的totals盘口
每次消耗1 credit → 30天约30 credits，远低于500上限

用法: python3 collect_odds.py --api-key YOUR_KEY
"""
import requests
import json
import os
import sys
from datetime import datetime

API_BASE = "https://api.the-odds-api.com/v4"
SPORT = "basketball_nba"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "odds")

def fetch_odds(api_key, regions="au,us", markets="totals"):
    """获取当前NBA totals盘口"""
    url = f"{API_BASE}/sports/{SPORT}/odds/"
    params = {
        "apiKey": api_key,
        "regions": regions,
        "markets": markets,
        "oddsFormat": "decimal",
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    
    remaining = resp.headers.get("x-requests-remaining", "?")
    used = resp.headers.get("x-requests-used", "?")
    print(f"📊 API Credits: used={used}, remaining={remaining}")
    
    return resp.json()

def parse_totals(data):
    """提取totals盘口数据"""
    records = []
    for game in data:
        game_id = game["id"]
        home = game["home_team"]
        away = game["away_team"]
        commence = game["commence_time"]
        
        for bm in game.get("bookmakers", []):
            for market in bm.get("markets", []):
                if market["key"] == "totals":
                    for outcome in market["outcomes"]:
                        if outcome["name"] == "Over":
                            records.append({
                                "game_id": game_id,
                                "date": commence[:10],
                                "commence_time": commence,
                                "home_team": home,
                                "away_team": away,
                                "bookmaker": bm["key"],
                                "line": outcome.get("point"),
                                "over_price": outcome.get("price"),
                                "collected_at": datetime.utcnow().isoformat(),
                            })
                        elif outcome["name"] == "Under":
                            # 找到对应的over记录并添加under价格
                            for r in records:
                                if r["game_id"] == game_id and r["bookmaker"] == bm["key"]:
                                    r["under_price"] = outcome.get("price")
    return records

def save_odds(records):
    """保存到日期文件"""
    os.makedirs(DATA_DIR, exist_ok=True)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    filepath = os.path.join(DATA_DIR, f"odds_{today}.json")
    
    # 追加模式：如果文件已存在，合并
    existing = []
    if os.path.exists(filepath):
        with open(filepath) as f:
            existing = json.load(f)
    
    # 去重（同一game_id+bookmaker只保留最新）
    seen = {(r["game_id"], r["bookmaker"]) for r in existing}
    for r in records:
        key = (r["game_id"], r["bookmaker"])
        if key not in seen:
            existing.append(r)
            seen.add(key)
    
    with open(filepath, "w") as f:
        json.dump(existing, f, indent=2)
    
    print(f"💾 保存 {len(records)} 条盘口到 {filepath}（总计{len(existing)}条）")
    return filepath

def main():
    api_key = os.environ.get("ODDS_API_KEY") or ""
    
    # 也支持命令行参数
    for i, arg in enumerate(sys.argv):
        if arg == "--api-key" and i + 1 < len(sys.argv):
            api_key = sys.argv[i + 1]
    
    if not api_key:
        print("❌ 需要API key: python3 collect_odds.py --api-key YOUR_KEY")
        print("   或设置环境变量: export ODDS_API_KEY=YOUR_KEY")
        print("\n   免费注册: https://the-odds-api.com/#get-access")
        sys.exit(1)
    
    print(f"🏀 获取NBA totals盘口...")
    data = fetch_odds(api_key)
    print(f"   找到 {len(data)} 场比赛")
    
    records = parse_totals(data)
    print(f"   解析 {len(records)} 条盘口记录")
    
    if records:
        save_odds(records)
        
        # 打印摘要
        print(f"\n📋 盘口摘要:")
        games = {}
        for r in records:
            key = f"{r['away_team']} @ {r['home_team']}"
            if key not in games:
                games[key] = []
            games[key].append(r)
        
        for game, odds in games.items():
            lines = [f"{o['bookmaker']}:{o['line']}" for o in odds]
            avg_line = sum(o['line'] for o in odds) / len(odds)
            print(f"   {game} | avg={avg_line:.1f} | {', '.join(lines[:3])}")
    else:
        print("   无盘口数据")

if __name__ == "__main__":
    main()
