# Meme Miner - 新三国梗/名台词挖掘器

从B站等视频平台挖掘"新三国"相关梗和名台词的Python工具。

## 功能特性

- 🔍 **B站视频搜索** - 按关键词搜索相关视频
- 💬 **弹幕抓取** - 获取视频弹幕并进行分析
- 🎯 **智能检测** - 基于启发式算法识别梗和名台词
  - 检测6-30字的中文文本
  - 识别标点符号特征（——！？……）
 - 识别三国角色名（曹操、刘备、诸葛亮等）
  - 基于频率和角色提及进行评分
- 💾 **JSONL输出** - 结果保存为结构化JSONL格式
- 🖥️ **友好的CLI** - 使用Typer和Rich的交互式命令行

## 安装

```bash
cd xin-sanguo-meme-miner
pip install -e .
```

## 使用方法

### 基础用法

```bash
# 搜索"新三国"相关视频并提取梗
python -m meme_miner collect --keyword "新三国" --platform bilibili --limit 20

# 指定输出文件前缀
python -m meme_miner collect -k "新三国" -p bilibili -l 20 -o my_output

# 开启详细日志
python -m meme_miner collect -k "新三国" -p bilibili -l 20 -v
```

### 命令行参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--keyword` | `-k` | 搜索关键词 | 必填 |
| `--platform` | `-p` | 平台（目前仅支持bilibili） | bilibili |
| `--limit` | `-l` | 处理视频数量 | 20 |
| `--output` | `-o` | 输出文件前缀 | xin_sanguo |
| `--verbose` | `-v` | 详细输出 | False |

## 输出格式

结果保存在 `data/` 目录下的JSONL文件中，格式如下：

```json
{
  "quote": "曹操——乱世奸雄！",
  "context": "新三国 第1集 群雄逐鹿",
  "source_platform": "bilibili",
  "source_url": "https://www.bilibili.com/video/BVxxxxx",
  "evidence": [
    {"text": "曹操——乱世奸雄！", "timestamp": 120.5, "likes": 42},
    {"text": "曹操乱世奸雄", "timestamp": 121.0, "likes": 10}
  ],
  "score": 85.5,
  "scraped_at": "2026-03-08T20:00:00"
}
```

## 项目结构

```
meme_miner/
├── models.py          # Pydantic数据模型
├── config.py          # 配置管理
├── cli.py             # Typer命令行入口
├── platforms/
│   ├── base.py        # 平台抽象基类
│   └── bilibili.py    # B站爬虫实现
├── analysis/
│   └── heuristics.py  # 梗检测启发式算法
└── storage/
    └── writer.py      # JSONL输出
```

## 扩展新平台

1. 继承 `BasePlatform` 创建新的平台类
2. 实现 `search_videos()` 和 `get_danmaku()` 方法
3. 在 `cli.py` 中注册新平台

示例：

```python
from meme_miner.platforms.base import BasePlatform

class DouyinPlatform(BasePlatform):
    def get_platform_name(self) -> str:
        return "douyin"
    
    async def search_videos(self, keyword: str, limit: int = 20):
        # 实现搜索逻辑
        pass
    
    async def get_danmaku(self, video_id: str):
        # 实现弹幕获取
        pass
```

## 运行测试

```bash
pytest tests/ -v
```

## ⚠️ 注意事项

- 请尊重B站的robots.txt和频率限制
- 默认请求间隔为1.5秒，避免对服务器造成压力
- 仅用于学习和研究目的，请遵守相关平台的使用条款

## 依赖

- Python >= 3.11
- httpx >= 0.27.0
- pydantic >= 2.6.0
- typer >= 0.12.0
- rich >= 13.7.0
- tenacity >= 8.2.0

## License

MIT License
