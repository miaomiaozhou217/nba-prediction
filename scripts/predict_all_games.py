#!/usr/bin/env python3
"""
预测所有今日/明日比赛
并记录到日志文件
"""
import sys
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

from predict_v3 import load_model, load_injuries, build_matchup_features, make_prediction

PREDICTIONS_DIR = PROJECT_ROOT / 'data' / 'predictions'
PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)

def get_games_for_date(date_str):
    """获取指定日期的比赛（格式: YYYYMMDD）"""
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
            
            games.append({
                'game_id': event['id'],
                'game_time': event['date'],
                'home_team': home['team']['abbreviation'],
                'away_team': away['team']['abbreviation'],
                'home_name': home['team']['displayName'],
                'away_name': away['team']['displayName'],
                'status': event['status']['type']['detail']
            })
        
        return games
    
    except Exception as e:
        print(f"❌ 获取比赛失败: {e}")
        return []

def predict_game(home_team, away_team, model_package, injuries_df):
    """预测单场比赛"""
    try:
        features_df = build_matchup_features(home_team, away_team, injuries_df)
        if features_df is None:
            return None
        
        predicted_total = make_prediction(model_package, features_df)
        
        # 计算各盘口建议
        lines = [215, 220, 225, 230]
        recommendations = []
        
        for line in lines:
            prediction = 'OVER' if predicted_total > line else 'UNDER'
            deviation = predicted_total - line
            confidence = abs(deviation) / line * 100
            
            if line == 215 and confidence > 3:
                decision = "强烈推荐"
                priority = 5
            elif confidence > 5:
                decision = "建议下注"
                priority = 4
            elif confidence > 2:
                decision = "可考虑"
                priority = 3
            else:
                decision = "不建议"
                priority = 1
            
            recommendations.append({
                'line': int(line),
                'prediction': prediction,
                'confidence': float(confidence),
                'decision': decision,
                'priority': int(priority)
            })
        
        # 找出最佳推荐
        best = max(recommendations, key=lambda x: x['confidence'])
        
        return {
            'predicted_total': predicted_total,
            'recommendations': recommendations,
            'best_line': best['line'],
            'best_prediction': best['prediction'],
            'best_confidence': best['confidence'],
            'priority': best['priority']
        }
    
    except Exception as e:
        print(f"  ⚠️  预测失败: {e}")
        return None

def format_telegram_message(date_str, games, predictions):
    """格式化Telegram消息"""
    date_obj = datetime.strptime(date_str, '%Y%m%d')
    readable_date = date_obj.strftime('%Y年%m月%d日 (%A)')
    
    msg = f"🏀 **NBA大小分预测报告**\n"
    msg += f"📅 日期: {readable_date}\n"
    msg += f"📊 比赛场次: {len(games)}场\n"
    msg += f"🤖 模型: V3 (伤病增强版)\n"
    msg += f"✅ 准确率: 73.5% (@盘口215)\n"
    msg += f"💰 ROI: +40.3%\n\n"
    
    # 按优先级排序
    sorted_games = sorted(
        zip(games, predictions),
        key=lambda x: x[1]['priority'] if x[1] else 0,
        reverse=True
    )
    
    # 重点推荐
    msg += "🎯 **重点推荐** (信心度>3%):\n\n"
    
    has_priority = False
    for game, pred in sorted_games:
        if pred and pred['priority'] >= 4:
            has_priority = True
            game_time = datetime.strptime(game['game_time'], '%Y-%m-%dT%H:%M%SZ')
            adelaide_time = game_time + timedelta(hours=10, minutes=30)
            time_str = adelaide_time.strftime('%H:%M')
            
            msg += f"**{game['away_team']} @ {game['home_team']}** ({time_str})\n"
            msg += f"  预测总分: {pred['predicted_total']:.1f}\n"
            msg += f"  推荐: 盘口{pred['best_line']} {pred['best_prediction']}\n"
            msg += f"  信心度: {pred['best_confidence']:.1f}%\n"
            msg += f"  决策: {pred['recommendations'][0]['decision']}\n\n"
    
    if not has_priority:
        msg += "  (今日无高信心推荐)\n\n"
    
    # 全部场次
    msg += "📋 **所有场次预测**:\n\n"
    
    for game, pred in sorted_games:
        if pred:
            game_time = datetime.strptime(game['game_time'], '%Y-%m-%dT%H:%M%SZ')
            adelaide_time = game_time + timedelta(hours=10, minutes=30)
            time_str = adelaide_time.strftime('%H:%M')
            
            emoji = "🏆" if pred['priority'] >= 4 else "⭐" if pred['priority'] >= 3 else "📌"
            msg += f"{emoji} {time_str} | {game['away_team']} @ {game['home_team']}\n"
            msg += f"   预测: {pred['predicted_total']:.1f} | 推荐: {pred['best_line']} {pred['best_prediction']} ({pred['best_confidence']:.1f}%)\n"
    
    msg += f"\n⚠️ **风险提示**:\n"
    msg += f"- 请在赛前20分钟确认最新伤病报告\n"
    msg += f"- 单场下注≤5%资金池\n"
    msg += f"- 专注盘口215，准确率最高\n"
    
    return msg

def save_predictions(date_str, games, predictions):
    """保存预测记录"""
    filepath = PREDICTIONS_DIR / f'predictions_{date_str}.json'
    
    records = []
    for game, pred in zip(games, predictions):
        if pred:
            records.append({
                'game_id': game['game_id'],
                'date': date_str,
                'game_time': game['game_time'],
                'home_team': game['home_team'],
                'away_team': game['away_team'],
                'predicted_total': float(pred['predicted_total']),
                'best_line': int(pred['best_line']),
                'best_prediction': pred['best_prediction'],
                'best_confidence': float(pred['best_confidence']),
                'priority': int(pred['priority']),
                'recommendations': pred['recommendations'],
                'prediction_time': datetime.now().isoformat()
            })
    
    with open(filepath, 'w') as f:
        json.dump(records, f, indent=2)
    
    print(f"💾 预测已保存: {filepath}")
    
    return filepath

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='预测所有今日/明日比赛')
    parser.add_argument('--date', help='日期 (YYYYMMDD), 默认明天', default=None)
    parser.add_argument('--telegram', action='store_true', help='输出Telegram格式')
    args = parser.parse_args()
    
    # 确定日期
    if args.date:
        date_str = args.date
    else:
        tomorrow = datetime.now() + timedelta(days=1)
        date_str = tomorrow.strftime('%Y%m%d')
    
    print("\n" + "="*70)
    print(f"🏀 NBA全场预测 - {date_str}")
    print("="*70 + "\n")
    
    # 获取比赛
    print(f"📥 获取比赛列表...")
    games = get_games_for_date(date_str)
    
    if not games:
        print("❌ 没有比赛或数据未更新")
        return
    
    print(f"✅ 找到 {len(games)} 场比赛\n")
    
    # 加载模型和伤病数据
    print(f"🤖 加载模型...")
    model_package = load_model()
    if not model_package:
        return
    
    print(f"🏥 加载伤病数据...")
    injuries_df = load_injuries()
    
    # 预测所有比赛
    print(f"\n🔮 开始预测...\n")
    predictions = []
    
    for i, game in enumerate(games, 1):
        print(f"[{i}/{len(games)}] {game['away_team']} @ {game['home_team']}...")
        pred = predict_game(game['home_team'], game['away_team'], model_package, injuries_df)
        predictions.append(pred)
        
        if pred:
            print(f"  ✅ 预测总分: {pred['predicted_total']:.1f} | 推荐: 盘口{pred['best_line']} {pred['best_prediction']} ({pred['best_confidence']:.1f}%)")
    
    # 保存预测
    print(f"\n💾 保存预测记录...")
    save_predictions(date_str, games, predictions)
    
    # 输出Telegram消息
    if args.telegram:
        print(f"\n📱 Telegram消息格式:\n")
        print("="*70)
        msg = format_telegram_message(date_str, games, predictions)
        print(msg)
        print("="*70)
    
    print(f"\n✅ 预测完成")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
