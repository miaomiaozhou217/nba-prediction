#!/bin/bash
# Telegram消息发送脚本

BOT_TOKEN="REDACTED"
CHAT_ID="REDACTED"

MESSAGE="$1"

if [ -z "$MESSAGE" ]; then
    echo "用法: $0 <消息内容>"
    exit 1
fi

# 发送Telegram消息
curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  -d "text=${MESSAGE}" \
  -d "parse_mode=Markdown" \
  > /dev/null

if [ $? -eq 0 ]; then
    echo "✅ Telegram消息已发送"
else
    echo "❌ Telegram消息发送失败"
    exit 1
fi
