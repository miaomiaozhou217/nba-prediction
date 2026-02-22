# NBA大小分预测 - 快捷命令

.PHONY: help install fetch analyze clean

help:  ## 显示帮助信息
	@echo "NBA大小分预测系统 - 可用命令:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## 安装Python依赖
	pip install -r requirements.txt

fetch:  ## 获取NBA数据（本赛季100场）
	python scripts/fetch_data.py --season 2024-25 --games 100

analyze:  ## 分析数据
	python scripts/analyze.py

clean:  ## 清理数据文件
	rm -rf data/raw/*.csv
	rm -rf data/processed/*.csv
	rm -rf models/*.pkl
	@echo "✅ 数据已清理"

status:  ## 显示项目状态
	@echo "📊 项目状态:"
	@echo ""
	@echo "数据文件:"
	@ls -lh data/raw/ 2>/dev/null || echo "  (空)"
	@echo ""
	@echo "模型文件:"
	@ls -lh models/ 2>/dev/null || echo "  (空)"
