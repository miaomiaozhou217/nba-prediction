#!/usr/bin/env python3
"""
扫描所有今日/明日NBA比赛，对比真实盘口，生成下注建议
"""
import json
import subprocess
import os
import sys

# NBA队伍简称映射
TEAM_MAP = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GS", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NY", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SA",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTAH", "Washington Wizards": "WAS",
}

def get_avg_line(odds_file):
    """从盘口文件获取每场平均line"""
    with open(odds_file) as f:
        records = json.load(f)
    
    games = {}
    for r in records:
        key = (r.get("away_team", ""), r.get("home_team", ""))
        if key not in games:
            games[key] = []
        if r.get("line"):
            games[key].append(r["line"])
    
    result = {}
    for (away, home), lines in games.items():
        away_abbr = TEAM_MAP.get(away, away)
        home_abbr = TEAM_MAP.get(home, home)
        avg = sum(lines) / len(lines)
        result[f"{away_abbr}@{home_abbr}"] = {
            "home": home_abbr, "away": away_abbr,
            "avg_line": round(avg, 1), "n_books": len(lines),
            "min_line": min(lines), "max_line": max(lines),
        }
    return result

def run_prediction(home, away):
    """运行V3预测"""
    cmd = f"cd /Users/tmtat/projects/nba && python3 scripts/predict_v3.py --home {home} --away {away} 2>&1"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    output = result.stdout + result.stderr
    
    for line in output.split('\n'):
        if '预测总分:' in line:
            try:
                return float(line.split(':')[1].strip())
            except:
                pass
    return None

def main():
    # 找最新的odds文件
    odds_dir = "/Users/tmtat/projects/nba/data/odds"
    odds_files = sorted([f for f in os.listdir(odds_dir) if f.startswith("odds_") and f.endswith(".json")])
    if not odds_files:
        print("❌ 无盘口数据")
        return
    
    odds_file = os.path.join(odds_dir, odds_files[-1])
    print(f"📊 盘口数据: {odds_files[-1]}")
    
    games = get_avg_line(odds_file)
    print(f"🏀 共 {len(games)} 场比赛\n")
    
    MAE = 17.09
    results = []
    
    print(f"{'比赛':<15} {'盘口':>6} {'预测':>6} {'偏离':>7} {'信心(L)':>8} {'信心(M)':>8} {'建议':>8}")
    print("-" * 72)
    
    for game_key, info in sorted(games.items()):
        pred = run_prediction(info["home"], info["away"])
        if pred is None:
            print(f"{game_key:<15} {info['avg_line']:>6.1f} {'FAIL':>6} {'':>7} {'':>8} {'':>8} {'跳过':>8}")
            continue
        
        dev = pred - info["avg_line"]
        conf_line = abs(dev) / info["avg_line"] * 100
        conf_mae = abs(dev) / MAE * 100
        direction = "OVER" if dev > 0 else "UNDER"
        
        # 决策逻辑
        if abs(dev) > 20:
            decision = "⚠️异常"
        elif conf_line >= 10:
            decision = f"🔥{direction}"
        elif conf_mae >= 20 and abs(dev) >= 3:
            decision = f"🟡{direction}"
        else:
            decision = "❌跳过"
        
        results.append({
            "game": game_key, "home": info["home"], "away": info["away"],
            "line": info["avg_line"], "min_line": info["min_line"], "max_line": info["max_line"],
            "prediction": pred, "deviation": dev,
            "conf_line": conf_line, "conf_mae": conf_mae,
            "direction": direction, "decision": decision,
        })
        
        print(f"{game_key:<15} {info['avg_line']:>6.1f} {pred:>6.1f} {dev:>+7.1f} {conf_line:>7.1f}% {conf_mae:>7.1f}% {decision:>8}")
    
    # 下注建议
    bets = [r for r in results if "🔥" in r["decision"] or "🟡" in r["decision"]]
    print(f"\n{'='*72}")
    if bets:
        print(f"💰 下注建议 ({len(bets)} 场):")
        for b in sorted(bets, key=lambda x: x["conf_mae"], reverse=True):
            emoji = "🔥" if "🔥" in b["decision"] else "🟡"
            print(f"   {emoji} {b['game']} {b['direction']} {b['line']} | "
                  f"预测{b['prediction']:.1f} | 偏离{b['deviation']:+.1f} | "
                  f"信心 L={b['conf_line']:.1f}% M={b['conf_mae']:.1f}%")
            print(f"      盘口范围: {b['min_line']}-{b['max_line']} ({b['direction']}时选{'最高' if b['direction']=='OVER' else '最低'})")
    else:
        print("😴 无推荐下注")
    
    # 异常场次
    anomalies = [r for r in results if "异常" in r["decision"]]
    if anomalies:
        print(f"\n⚠️ 异常场次 ({len(anomalies)} 场) — 模型可能不可靠:")
        for a in anomalies:
            print(f"   {a['game']} | 偏离{a['deviation']:+.1f} | 预测{a['prediction']:.1f} vs 盘口{a['line']}")

if __name__ == "__main__":
    main()
