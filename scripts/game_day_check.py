#!/usr/bin/env python3
"""
比赛日最终确认脚本
1. 刷新伤病数据
2. 重新运行预测
3. 对比盘口
4. 生成下注建议
"""
import subprocess
import sys
import json
from datetime import datetime

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

def main():
    print(f"{'='*60}")
    print(f"🏀 NBA比赛日确认 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")
    
    # 1. 刷新伤病数据
    print("\n📋 Step 1: 刷新伤病数据...")
    out, err, code = run_cmd("cd /Users/tmtat/projects/nba && python3 scripts/fetch_injuries.py")
    if code == 0:
        print("   ✅ 伤病数据已更新")
    else:
        print(f"   ⚠️ 伤病更新失败: {err[:200]}")
        print("   继续使用缓存数据...")
    
    # 2. 运行预测
    games = [
        {"home": "DET", "away": "SA", "time": "11:10", "line": 230.0},
        {"home": "MEM", "away": "SAC", "time": "12:10", "line": 233.0},
        {"home": "HOU", "away": "UTAH", "time": "13:40", "line": 228.5},
    ]
    
    print("\n🎯 Step 2: 运行预测...")
    results = []
    
    for game in games:
        print(f"\n   {game['away']} @ {game['home']} ({game['time']})...")
        out, err, code = run_cmd(
            f"cd /Users/tmtat/projects/nba && python3 scripts/predict_v3.py "
            f"--home {game['home']} --away {game['away']} 2>&1"
        )
        
        # 解析预测值
        prediction = None
        for line in out.split('\n'):
            if '预测总分:' in line:
                try:
                    prediction = float(line.split(':')[1].strip())
                except:
                    pass
        
        if prediction:
            deviation = prediction - game['line']
            mae = 17.09  # V3 MAE
            # 统一使用line法（与predict_v3.py回测一致）
            confidence_line = abs(deviation) / game['line'] * 100
            confidence_mae = abs(deviation) / mae * 100  # 仅供参考
            
            result = {
                'game': f"{game['away']}@{game['home']}",
                'time': game['time'],
                'prediction': prediction,
                'line': game['line'],
                'deviation': deviation,
                'confidence': confidence_line,
                'confidence_mae': confidence_mae,
                'direction': 'OVER' if deviation > 0 else 'UNDER',
            }
            results.append(result)
            
            status = "✅" if confidence_line >= 10 else ("🟡" if confidence_mae >= 10 else "❌")
            anomaly = " ⚠️异常" if abs(deviation) > 20 else ""
            print(f"   {status} 预测{prediction:.1f} vs 盘口{game['line']} | "
                  f"偏离{deviation:+.1f} | 信心{confidence_line:.1f}%(line) {confidence_mae:.1f}%(mae){anomaly}")
        else:
            print(f"   ❌ 预测失败")
    
    # 3. 生成下注建议
    print(f"\n{'='*60}")
    print("💰 下注建议（10%阈值，排除>20分异常）:")
    print(f"{'='*60}")
    
    bets = []
    for r in results:
        # Edge分析结论：偏离≥6分有真实edge(65.7%准确率)，<4分无edge，>20分异常
        qualifies = abs(r['deviation']) >= 6
        if qualifies and abs(r['deviation']) <= 20:
            bet_amount = 15  # AUD
            print(f"\n   🔥 {r['game']} ({r['time']})")
            print(f"      {r['direction']} {r['line']} @ 1.90")
            print(f"      预测: {r['prediction']:.1f}, 信心: {r['confidence']:.1f}%")
            print(f"      下注: ${bet_amount} AUD")
            bets.append({**r, 'amount': bet_amount})
        elif r['confidence'] >= 10 or r['confidence_mae'] >= 20:
            print(f"\n   ⚠️ {r['game']} - 信心{r['confidence']:.1f}%但偏离{r['deviation']:+.1f}（异常，跳过）")
        else:
            print(f"\n   ❌ {r['game']} - 信心{r['confidence']:.1f}%（不足）")
    
    if not bets:
        print("\n   😴 今日无推荐下注")
    
    # 4. 输出TG消息格式
    if bets:
        print(f"\n{'='*60}")
        print("📱 TG消息（发给细菌）:")
        print(f"{'='*60}")
        msg = "🏀 NBA下注提醒\n\n"
        for b in bets:
            msg += f"📊 {b['game']} ({b['time']} Adelaide)\n"
            msg += f"   {b['direction']} {b['line']} | ${b['amount']} AUD\n"
            msg += f"   预测: {b['prediction']:.1f} | 信心: {b['confidence']:.1f}%\n\n"
        msg += "请在Bet365下注后回复确认。"
        print(msg)
    
    return bets

if __name__ == "__main__":
    bets = main()
