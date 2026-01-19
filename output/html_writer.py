"""
HTML 报告生成模块 - 使用 string.Template 避免 CSS 冲突
"""
import os
import pandas as pd
from string import Template
from typing import List, Optional
from datetime import datetime
from crawlers.base import PaperData


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>论文筛选报告</title>
    <style>
        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --bg: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --text: #e2e8f0;
            --text-muted: #94a3b8;
            --border: #334155;
            --success: #22c55e;
            --warning: #f59e0b;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        header {
            text-align: center;
            margin-bottom: 3rem;
            padding: 2rem;
            background: linear-gradient(135deg, var(--bg-card), var(--bg));
            border-radius: 1rem;
            border: 1px solid var(--border);
        }
        
        h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--primary), #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .subtitle {
            color: var(--text-muted);
            font-size: 1.1rem;
        }
        
        .stats {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 1.5rem;
        }
        
        .stat {
            text-align: center;
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: var(--primary);
        }
        
        .stat-label {
            color: var(--text-muted);
            font-size: 0.9rem;
        }
        
        .search-bar {
            margin-bottom: 2rem;
            display: flex;
            gap: 1rem;
        }
        
        .search-input {
            flex: 1;
            padding: 0.75rem 1rem;
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            background: var(--bg-card);
            color: var(--text);
            font-size: 1rem;
        }
        
        .search-input:focus {
            outline: none;
            border-color: var(--primary);
        }
        
        .filter-select {
            padding: 0.75rem 1rem;
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            background: var(--bg-card);
            color: var(--text);
            font-size: 1rem;
            cursor: pointer;
        }
        
        .paper-list {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }
        
        .paper-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 1rem;
            padding: 1.5rem;
            transition: all 0.3s ease;
        }
        
        .paper-card:hover {
            background: var(--bg-card-hover);
            transform: translateY(-2px);
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        }
        
        .paper-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
            margin-bottom: 1rem;
        }
        
        .paper-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text);
        }
        
        .paper-title a {
            color: inherit;
            text-decoration: none;
        }
        
        .paper-title a:hover {
            color: var(--primary);
        }
        
        .paper-meta {
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
            margin-bottom: 1rem;
        }
        
        .tag {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        
        .tag-venue {
            background: rgba(99, 102, 241, 0.2);
            color: var(--primary);
        }
        
        .tag-year {
            background: rgba(34, 197, 94, 0.2);
            color: var(--success);
        }
        
        .paper-reason {
            background: rgba(245, 158, 11, 0.1);
            border-left: 3px solid var(--warning);
            padding: 0.75rem 1rem;
            margin-bottom: 1rem;
            border-radius: 0 0.5rem 0.5rem 0;
            font-size: 0.95rem;
        }
        
        .paper-reason-label {
            color: var(--warning);
            font-weight: 600;
            margin-bottom: 0.25rem;
        }
        
        .paper-abstract {
            color: var(--text-muted);
            font-size: 0.95rem;
            line-height: 1.7;
        }
        
        .paper-abstract-zh {
            background: var(--bg);
            padding: 1rem;
            border-radius: 0.5rem;
            margin-top: 1rem;
            border: 1px solid var(--border);
        }
        
        .paper-abstract-label {
            color: var(--primary);
            font-weight: 600;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
        }
        
        .paper-authors {
            margin-top: 1rem;
            color: var(--text-muted);
            font-size: 0.85rem;
        }
        
        .toggle-btn {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            cursor: pointer;
            font-size: 0.85rem;
            transition: all 0.2s;
        }
        
        .toggle-btn:hover {
            border-color: var(--primary);
            color: var(--primary);
        }
        
        .hidden {
            display: none;
        }
        
        footer {
            text-align: center;
            margin-top: 3rem;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.9rem;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            h1 {
                font-size: 1.75rem;
            }
            
            .stats {
                flex-direction: column;
                gap: 1rem;
            }
            
            .search-bar {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📚 论文筛选报告</h1>
            <p class="subtitle">$report_subtitle</p>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">$total_papers</div>
                    <div class="stat-label">筛选论文</div>
                </div>
                <div class="stat">
                    <div class="stat-value">$venue_count</div>
                    <div class="stat-label">会议/来源</div>
                </div>
            </div>
        </header>
        
        <div class="search-bar">
            <input type="text" class="search-input" id="searchInput" placeholder="🔍 搜索论文标题或摘要...">
            <select class="filter-select" id="venueFilter">
                <option value="">全部会议</option>
                $venue_options
            </select>
        </div>
        
        <div class="paper-list" id="paperList">
            $paper_cards
        </div>
        
        <footer>
            <p>生成时间: $generated_time</p>
            <p>Powered by Paper Pipeline 🚀</p>
        </footer>
    </div>
    
    <script>
        const searchInput = document.getElementById('searchInput');
        const venueFilter = document.getElementById('venueFilter');
        const paperCards = document.querySelectorAll('.paper-card');
        
        function filterPapers() {
            const searchTerm = searchInput.value.toLowerCase();
            const selectedVenue = venueFilter.value;
            
            paperCards.forEach(card => {
                const title = card.dataset.title.toLowerCase();
                const abstract = card.dataset.abstract.toLowerCase();
                const venue = card.dataset.venue;
                
                const matchesSearch = title.includes(searchTerm) || abstract.includes(searchTerm);
                const matchesVenue = !selectedVenue || venue === selectedVenue;
                
                card.style.display = matchesSearch && matchesVenue ? 'block' : 'none';
            });
        }
        
        searchInput.addEventListener('input', filterPapers);
        venueFilter.addEventListener('change', filterPapers);
        
        function toggleAbstract(btn) {
            const abstractDiv = btn.parentElement.nextElementSibling;
            abstractDiv.classList.toggle('hidden');
            btn.textContent = abstractDiv.classList.contains('hidden') ? '展开原文' : '收起原文';
        }
    </script>
</body>
</html>
"""


def escape_html(text: str) -> str:
    """转义 HTML 特殊字符"""
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;"))


def generate_paper_card(paper: PaperData, index: int) -> str:
    """生成单个论文卡片的 HTML"""
    reason_html = ""
    if paper.reason_zh:
        reason_html = f"""
        <div class="paper-reason">
            <div class="paper-reason-label">📌 筛选理由</div>
            <div>{escape_html(paper.reason_zh)}</div>
        </div>
        """
    
    abstract_zh_html = ""
    if paper.abstract_zh:
        abstract_zh_html = f"""
        <div class="paper-abstract-zh">
            <div class="paper-abstract-label">📖 中文摘要</div>
            <div>{escape_html(paper.abstract_zh)}</div>
        </div>
        """
    
    # 转义数据属性中的特殊字符
    title_escaped = escape_html(paper.title)
    abstract_escaped = escape_html(paper.abstract[:500])
    authors_display = paper.authors[:200] + "..." if len(paper.authors) > 200 else paper.authors
    
    return f"""
    <div class="paper-card" data-title="{title_escaped}" data-abstract="{abstract_escaped}" data-venue="{paper.venue}">
        <div class="paper-header">
            <h3 class="paper-title">
                <a href="{paper.url}" target="_blank">{title_escaped}</a>
            </h3>
        </div>
        <div class="paper-meta">
            <span class="tag tag-venue">{paper.venue}</span>
            <span class="tag tag-year">{paper.year}</span>
        </div>
        {reason_html}
        {abstract_zh_html}
        <div>
            <button class="toggle-btn" onclick="toggleAbstract(this)">展开原文</button>
        </div>
        <div class="paper-abstract hidden">
            <p style="margin-top: 1rem;">{escape_html(paper.abstract)}</p>
        </div>
        <div class="paper-authors">
            👥 {escape_html(authors_display)}
        </div>
    </div>
    """


def write_html(papers: List[PaperData], output_path: str, subtitle: str = ""):
    """
    生成 HTML 报告
    
    Args:
        papers: 论文列表
        output_path: 输出文件路径
        subtitle: 报告副标题
    """
    if not papers:
        print("⚠️ 没有论文可生成报告")
        return
    
    # 确保目录存在
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    # 统计会议
    venues = sorted(set(p.venue for p in papers))
    venue_options = "\n".join(f'<option value="{v}">{v}</option>' for v in venues)
    
    # 生成论文卡片
    paper_cards = "\n".join(
        generate_paper_card(paper, i) 
        for i, paper in enumerate(papers)
    )
    
    # 使用 string.Template（使用 $ 而不是 {}）
    template = Template(HTML_TEMPLATE)
    html_content = template.substitute(
        report_subtitle=subtitle or f"共筛选出 {len(papers)} 篇相关论文",
        total_papers=len(papers),
        venue_count=len(venues),
        venue_options=venue_options,
        paper_cards=paper_cards,
        generated_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"📄 已生成 HTML 报告: {os.path.abspath(output_path)}")


def write_html_from_csv(csv_path: str, output_path: str, subtitle: str = ""):
    """
    从 CSV 文件生成 HTML 报告
    
    Args:
        csv_path: CSV 文件路径
        output_path: 输出文件路径
        subtitle: 报告副标题
    """
    if not os.path.exists(csv_path):
        print(f"❌ 找不到 CSV 文件: {csv_path}")
        return
    
    df = pd.read_csv(csv_path)
    papers = [PaperData.from_dict(row) for _, row in df.iterrows()]
    
    print(f"📖 从 CSV 加载了 {len(papers)} 篇论文")
    write_html(papers, output_path, subtitle)
