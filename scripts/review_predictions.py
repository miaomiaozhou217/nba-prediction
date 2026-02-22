#!/usr/bin/env python3
"""
赛后回顾预测准确率
对比预测值与实际比分
"""
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
PREDICTIONS_DIR = PROJECT_ROOT / 'data' / 'predictions'
REVIEWS_DIR = PROJECT_ROOT / 'data' / 'reviews'
REVIEWS_DIR.mkdir(parents=True, exist_ok=True)

def load_predictions(date_str):
    """加载预测记录"""
    filepath = PREDICTIONS_DIR / f'predictions_{date_str}.json'
    
    if not filepath.exists():
        print(f"❌ 预测文件不存在: {filepath}")
        return None
    
    with open(filepath, 'r') as f:
        predictions = json.load(f)
    
    return predictions

def get_actual_scores(date_str):
    """获取实际比分"""
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        events = data.get('events', [])
        
        scores = {}
        for event in events:
            comp = event['competitions'][0]
            
            # 只处理已完成的比赛
            if event['status']['type']['completed']:
                home = comp['competitors'][0] if comp['competitors'][0]['homeAway'] == 'home' else comp['competitors'][1]
                away = comp['competitors'][1] if comp['competitors'][1]['homeAway'] == 'away' else comp['competitors'][0]
                
                home_score = int(home['score'])
                away_score = int(away['score'])
                total_score = home_score + away_score
                
                scores[event['id']] = {
                    'home_team': home['team']['abbreviation'],
                    'away_team': away['team']['abbreviation'],
                    'home_score': home_score,
                    'away_score': away_score,
                    'total_score': total_score
                }
        
        return scores
    
    except Exception as e:
        print(f"❌ 获取比分失败: {e}")
        return {}

def analyze_predictions(predictions, actual_scores):
    """分析预测准确率"""
    results = []
    
    for pred in predictions:
        game_id = pred['game_id']
        
        if game_id not in actual_scores:
            continue  # 比赛未完成
        
        actual = actual_scores[game_id]
        
        # 计算预测误差
        error = abs(pred['predicted_total'] - actual['total_score'])
        error_pct = error / actual['total_score'] * 100
        
        # 判断推荐是否正确
        best_line = pred['best_line']
        best_prediction = pred['best_prediction']
        
        if best_prediction == 'OVER':
            correct = actual['total_score'] > best_line
        else:
            correct = actual['total_score'] <= best_line
        
        results.append({
            'game_id': game_id,
            'home_team': pred['home_team'],
            'away_team': pred['away_team'],
            'predicted_total': pred['predicted_total'],
            'actual_total': actual['total_score'],
            'error': error,
            'error_pct': error_pct,
            'best_line': best_line,
            'best_prediction': best_prediction,
            'best_confidence': pred['best_confidence'],
            'priority': pred['priority'],
            'correct': correct,
            'home_score': actual['home_score'],
            'away_score': actual['away_score']
        })
    
    return results

def generate_review_report(date_str, results):
    """生成回顾报告"""
    if not results:
        return "今日比赛尚未完成，暂无数据"
    
    df = pd.DataFrame(results)
    
    # 统计数据
    total_games = len(df)
    correct_count = df['correct'].sum()
    accuracy = correct_count / total_games * 100 if total_games > 0 else 0
    
    avg_error = df['error'].mean()
    avg_error_pct = df['error_pct'].mean()
    
    # 按优先级分组统计
    priority_stats = df.groupby('priority').agg({
        'correct': ['sum', 'count']
    }).reset_index()
    
    # 生成报告
    date_obj = datetime.strptime(date_str, '%Y%m%d')
    readable_date = date_obj.strftime('%Y年%m月%d日')
    
    msg = f"📊 **NBA预测回顾报告**\n"
    msg += f"📅 日期: {readable_date}\n\n"
    
    msg += f"🎯 **总体表现**:\n"
    msg += f"  总场次: {total_games}\n"
    msg += f"  预测正确: {correct_count}场\n"
    msg += f"  准确率: {accuracy:.1f}%\n"
    msg += f"  平均误差: {avg_error:.1f}分 ({avg_error_pct:.1f}%)\n\n"
    
    # ROI计算（假设赔率1.91）
    wins = correct_count
    losses = total_games - correct_count
    roi = (wins * 0.91 - losses) / total_games * 100 if total_games > 0 else 0
    
    msg += f"💰 **理论盈利**:\n"
    msg += f"  {wins}胜 / {losses}负\n"
    msg += f"  ROI: {roi:+.1f}%\n"
    
    if roi > 0:
        msg += f"  ✅ 盈利 (每$100赚${roi:.2f})\n\n"
    else:
        msg += f"  ❌ 亏损\n\n"
    
    # 详细结果
    msg += f"📋 **详细结果**:\n\n"
    
    for _, row in df.iterrows():
        emoji = "✅" if row['correct'] else "❌"
        priority_emoji = "🏆" if row['priority'] >= 4 else "⭐" if row['priority'] >= 3 else "📌"
        
        msg += f"{emoji} {priority_emoji} {row['away_team']} @ {row['home_team']}\n"
        msg += f"   预测: {row['predicted_total']:.1f} | 实际: {row['actual_total']} ({row['home_score']}-{row['away_score']})\n"
        msg += f"   推荐: 盘口{row['best_line']} {row['best_prediction']} ({row['best_confidence']:.1f}%) | 误差: {row['error']:.1f}分\n\n"
    
    # 改进建议
    msg += f"💡 **改进建议**:\n"
    
    if accuracy < 60:
        msg += f"  ⚠️ 准确率偏低，建议观察更多场次\n"
    elif accuracy >= 70:
        msg += f"  ✅ 准确率优秀，符合模型预期\n"
    
    if avg_error > 20:
        msg += f"  ⚠️ 平均误差较大，可能需要调整特征权重\n"
    
    return msg

def save_review(date_str, results, report):
    """保存回顾记录"""
    filepath = REVIEWS_DIR / f'review_{date_str}.json'
    
    data = {
        'date': date_str,
        'review_time': datetime.now().isoformat(),
        'results': results,
        'report': report
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"💾 回顾已保存: {filepath}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='回顾预测准确率')
    parser.add_argument('--date', help='日期 (YYYYMMDD), 默认今天', default=None)
    parser.add_argument('--telegram', action='store_true', help='输出Telegram格式')
    args = parser.parse_args()
    
    # 确定日期
    if args.date:
        date_str = args.date
    else:
        date_str = datetime.now().strftime('%Y%m%d')
    
    print("\n" + "="*70)
    print(f"📊 NBA预测回顾 - {date_str}")
    print("="*70 + "\n")
    
    # 加载预测
    print(f"📥 加载预测记录...")
    predictions = load_predictions(date_str)
    
    if not predictions:
        return
    
    print(f"✅ 找到 {len(predictions)} 场预测\n")
    
    # 获取实际比分
    print(f"📥 获取实际比分...")
    actual_scores = get_actual_scores(date_str)
    
    print(f"✅ 找到 {len(actual_scores)} 场已完成比赛\n")
    
    if not actual_scores:
        print("⚠️  比赛尚未完成，暂无数据分析")
        return
    
    # 分析预测
    print(f"📊 分析预测准确率...\n")
    results = analyze_predictions(predictions, actual_scores)
    
    # 生成报告
    report = generate_review_report(date_str, results)
    
    # 保存回顾
    save_review(date_str, results, report)
    
    # 输出报告
    if args.telegram:
        print(f"\n📱 Telegram消息格式:\n")
        print("="*70)
        print(report)
        print("="*70)
    else:
        print(report)
    
    print(f"\n✅ 回顾完成")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
