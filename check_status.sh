#!/bin/bash
# Check meme miner status - Run this tomorrow morning

cd /home/lobst/.openclaw/workspace/xin-sanguo-meme-miner

echo "=== Meme Miner 10小时运行状态 ==="
echo ""
echo "当前时间: $(date)"
echo ""

# Check if process is still running
if pgrep -f "python3 runner.py" > /dev/null; then
    echo "✅ 进程正在运行"
    echo "进程信息:"
    ps aux | grep "python3 runner.py" | grep -v grep
else
    echo "⏹️ 进程已结束"
fi

echo ""
echo "=== 运行日志 ==="
tail -30 data/runner_output.log

echo ""
echo "=== 统计信息 ==="
if [ -f data/runner_stats.json ]; then
    cat data/runner_stats.json
else
    echo "暂无统计信息"
fi

echo ""
echo "=== 数据文件 ==="
ls -lh data/*.jsonl

echo ""
echo "=== 梗数量统计 ==="
for f in data/*.jsonl; do
    if [ -f "$f" ]; then
        count=$(wc -l < "$f")
        echo "$f: $count 条记录"
    fi
done
