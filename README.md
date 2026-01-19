# Paper Find Agent 📚

一个智能的学术论文爬取与筛选系统，使用 LLM 自动生成关键词、并发筛选论文，并生成精美的 HTML 报告。

## ✨ 核心特性

- **🧠 智能关键词生成**：根据需求描述自动生成 4-6 个精准搜索关键词
- **🔑 多层过滤机制**：关键词预过滤 + LLM 智能筛选
- **⚡ 并发推理**：10 倍加速（默认 10 并发）
- **🎓 多数据源支持**：ICLR, NeurIPS, ICML, ACL (OpenReview) + Arxiv
- **📊 引用量过滤**：Arxiv 论文自动过滤低引用（<5）
- **🔄 智能去重**：按标题自动去重
- **📄 双格式输出**：CSV 数据 + 交互式 HTML 报告
- **🎯 灵活跳过**：支持跳过爬取、筛选、只生成 HTML

## 🔄 工作流程

```
用户输入需求描述
       ↓
🧠 生成关键词 + 筛选 Prompt (可交互修改)
       ↓
📚 爬取论文 (关键词预过滤 + 去重)
   ├─ OpenReview: ICLR, NeurIPS, ICML, ACL
   └─ Arxiv: 引用量过滤 (≥5)
       ↓
🎯 DeepSeek 并发筛选 (10x 加速)
       ↓
💾 输出结果
   ├─ papers_raw.csv (爬取数据)
   ├─ papers_filtered.csv (筛选结果)
   └─ papers_report.html (交互式报告)
```

## 📁 项目结构

```
paper_pipeline/
├── main.py                    # CLI 主入口
├── config.py                  # 配置管理
├── prompt_generator.py        # 关键词 + Prompt 生成
├── crawlers/
│   ├── base.py               # PaperData 数据类
│   ├── openreview_crawler.py # OpenReview 爬虫
│   └── arxiv_crawler.py      # Arxiv 爬虫 (含引用过滤)
├── filters/
│   ├── base.py               # LLM 客户端 (支持并发)
│   └── fine_filter.py        # 并发筛选器
└── output/
    ├── csv_writer.py         # CSV 输出
    └── html_writer.py        # HTML 报告生成
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install openreview-py arxiv pandas tqdm openai requests aiohttp
```

### 2. 配置 API Key

```bash
# DeepSeek (通过 SiliconFlow)
export SILICON_API_KEY="your-api-key"
```

获取 API Key：[SiliconFlow](https://cloud.siliconflow.cn/)

### 3. 运行

```bash
# 基础用法
python main.py -d "我想找关于 LLM 置信度估计的论文"

# 指定关键词（在描述中）
python main.py -d "LLM 置信度估计，关键词：llm confidence, uncertainty quantification"

# 非交互模式（自动运行）
python main.py -d "..." --no-interactive
```

## 📖 详细用法

### 命令行参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--description` | `-d` | 研究需求描述（必填） | - |
| `--years` | `-y` | 爬取年份（逗号分隔） | `2024,2025` |
| `--conferences` | `-c` | 会议列表（逗号分隔） | `ICLR,ICML,NEURIPS,ACL` |
| `--no-arxiv` | | 不爬取 Arxiv | `False` |
| `--no-interactive` | | 关闭交互模式 | `False` |
| `--output-dir` | `-o` | 输出目录 | `./output` |
| `--skip-crawl` | | 跳过爬取（使用已有数据） | `False` |
| `--skip-filter` | | 跳过筛选 | `False` |
| `--html-only` | | 只生成 HTML | `False` |

### 使用场景

#### 场景 1：完整流程

```bash
python main.py -d "我想找关于 LLM 评估稳定性的论文"
```

**流程：** 生成关键词 → 爬取 → 筛选 → 输出

#### 场景 2：只爬取，不筛选

```bash
python main.py -d "..." --skip-filter
```

**用途：** 快速获取相关论文列表，稍后再筛选

#### 场景 3：使用已爬取数据

```bash
python main.py -d "..." --skip-crawl
```

**用途：** 修改筛选 prompt 后重新筛选

#### 场景 4：只重新生成 HTML

```bash
python main.py -d "..." --html-only
```

**用途：** HTML 样式调整后重新生成

#### 场景 5：指定年份和会议

```bash
python main.py -d "..." -y 2024 -c ICLR,ICML
```

#### 场景 6：非交互模式（CI/CD）

```bash
python main.py -d "..." --no-interactive
```

## 📊 输出文件

| 文件 | 说明 |
|------|------|
| `output/papers_raw.csv` | 关键词过滤后的原始数据 |
| `output/papers_filtered.csv` | LLM 筛选结果（含理由和中文翻译） |
| `output/papers_report.html` | 交互式 HTML 报告 |

### HTML 报告功能

- 🔍 实时搜索（标题/摘要）
- 🏷️ 按会议过滤
- 📖 展开/收起原文
- 🌐 直接跳转论文链接
- 🎨 深色主题 + 响应式设计

## ⚙️ 高级配置

### 修改并发数

编辑 `config.py`：

```python
concurrency: int = 20  # 默认 10
```

### 修改引用量阈值

编辑 `main.py` 中的 `crawl_papers` 函数：

```python
arxiv_crawler = ArxivCrawler(min_citations=10)  # 默认 5
```

### 自定义筛选 Prompt

使用交互模式，在筛选前编辑 Prompt：

```bash
python main.py -d "..."
# 在 "请确认筛选 Prompt" 步骤选择 [e] 编辑
```

## 🔧 技术栈

- **爬虫**：`openreview-py`, `arxiv`
- **LLM**：DeepSeek-V3 (via SiliconFlow)
- **并发**：`asyncio`, `aiohttp`
- **引用数据**：Semantic Scholar API
- **数据处理**：`pandas`
- **前端**：原生 HTML/CSS/JS

## 📝 工作原理

### 1. 关键词生成

使用 DeepSeek 根据用户描述生成 4-6 个精准关键词，避免过于宽泛的词（如 "LLM", "AI"）。

### 2. 论文爬取

- **OpenReview**：按关键词在标题/摘要/关键词中匹配
- **Arxiv**：
  - 使用关键词构建查询
  - 限制年份范围（会议年份前一年到当前年份）
  - 调用 Semantic Scholar API 获取引用量
  - 过滤低引用论文（<5）

### 3. 去重

按标题去重（忽略大小写和多余空格），避免 OpenReview 和 Arxiv 重复。

### 4. 并发筛选

- 使用 `asyncio` + `aiohttp` 并发调用 LLM API
- 默认 10 并发，可配置
- 自动限流保护
- 预期速度：300 篇论文 ~3-5 分钟

### 5. 结果输出

- **CSV**：包含标题、摘要、作者、机构、会议、年份、URL、筛选理由、中文摘要
- **HTML**：交互式报告，支持搜索和过滤

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT License

## 🙏 致谢

- [OpenReview](https://openreview.net/) - 学术论文平台
- [Arxiv](https://arxiv.org/) - 预印本论文库
- [Semantic Scholar](https://www.semanticscholar.org/) - 引用数据
- [SiliconFlow](https://siliconflow.cn/) - LLM API 服务
