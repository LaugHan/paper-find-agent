"""
Paper Pipeline 主入口
支持: 爬取 -> 筛选 -> HTML 生成 (每个步骤可单独跳过)
"""
import argparse
import os
import pandas as pd
from typing import List, Optional

from config import Config, load_config
from crawlers import OpenReviewCrawler, ArxivCrawler, PaperData
from filters import FineFilter
from prompt_generator import generate_all
from output import write_csv, write_html
from output.html_writer import write_html_from_csv


def interactive_confirm_keywords(keywords: List[str]) -> List[str]:
    """交互式确认关键词"""
    print("\n" + "="*60)
    print("🔑 请确认搜索关键词")
    print("="*60)
    print("LLM 生成的关键词:")
    for i, kw in enumerate(keywords, 1):
        print(f"  {i}. {kw}")
    
    print("\n选项:")
    print("  [Enter] 使用当前关键词继续")
    print("  [e] 编辑关键词（输入新的关键词，用逗号分隔）")
    print("  [q] 退出")
    
    choice = input("\n请选择 [Enter/e/q]: ").strip().lower()
    
    if choice == 'q':
        print("用户取消")
        exit(0)
    elif choice == 'e':
        new_keywords = input("请输入新的关键词（用逗号分隔）: ").strip()
        if new_keywords:
            keywords = [kw.strip() for kw in new_keywords.split(",") if kw.strip()]
            print(f"✅ 更新关键词: {keywords}")
    
    return keywords


def interactive_confirm_prompt(prompt_type: str, prompt: str) -> str:
    """交互式确认 Prompt"""
    print("\n" + "="*60)
    print(f"📝 请确认{prompt_type} Prompt")
    print("="*60)
    print(prompt[:600] + "..." if len(prompt) > 600 else prompt)
    
    print("\n选项:")
    print("  [Enter] 使用当前 Prompt 继续")
    print("  [e] 编辑 Prompt")
    print("  [q] 退出")
    
    choice = input("\n请选择 [Enter/e/q]: ").strip().lower()
    
    if choice == 'q':
        print("用户取消")
        exit(0)
    elif choice == 'e':
        print("请输入新的 Prompt（输入空行结束）:")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        if lines:
            prompt = "\n".join(lines)
            print(f"✅ Prompt 已更新")
    
    return prompt


def interactive_confirm_crawl_result(paper_count: int) -> bool:
    """确认是否继续进行 LLM 筛选"""
    print("\n" + "="*60)
    print(f"📊 共爬取 {paper_count} 篇论文")
    print("="*60)
    print("选项:")
    print("  [Enter] 继续进行 LLM 筛选")
    print("  [q] 退出（保留已爬取的数据）")
    
    choice = input("\n请选择 [Enter/q]: ").strip().lower()
    return choice != 'q'


def deduplicate_papers(papers: List[PaperData]) -> List[PaperData]:
    """按标题去重"""
    seen_titles = set()
    unique_papers = []
    
    for paper in papers:
        normalized_title = ' '.join(paper.title.lower().strip().split())
        if normalized_title not in seen_titles:
            seen_titles.add(normalized_title)
            unique_papers.append(paper)
    
    return unique_papers


def crawl_papers(config: Config, keywords: List[str]) -> List[PaperData]:
    """爬取论文"""
    all_papers = []
    
    print("\n" + "="*60)
    print("📚 步骤 2/4: 爬取论文")
    print("="*60)
    print(f"🔑 使用关键词: {', '.join(keywords)}")
    
    # 爬取 OpenReview 会议
    for year in config.years:
        crawler = OpenReviewCrawler(year)
        for conf in config.conferences:
            print(f"\n--- {conf} {year} ---")
            papers = crawler.crawl(conf, keywords=keywords)
            all_papers.extend(papers)
    
    openreview_count = len(all_papers)
    
    # 爬取 Arxiv
    if config.crawl_arxiv and keywords:
        print(f"\n--- Arxiv ---")
        arxiv_crawler = ArxivCrawler(min_citations=5)
        arxiv_years = list(range(min(config.years) - 1, max(config.years) + 1))
        papers = arxiv_crawler.crawl(
            keywords, 
            years=arxiv_years,
            max_results=config.arxiv_max_results,
            filter_by_keywords=True,
            filter_by_citations=True
        )
        all_papers.extend(papers)
    
    # 去重
    print(f"\n🔄 去重中...")
    before_dedup = len(all_papers)
    all_papers = deduplicate_papers(all_papers)
    
    if before_dedup > len(all_papers):
        print(f"   移除 {before_dedup - len(all_papers)} 篇重复论文")
    
    print(f"\n📊 总计: {len(all_papers)} 篇论文")
    
    # 保存原始数据
    write_csv(all_papers, config.raw_papers_path, include_filter_results=False)
    
    return all_papers


def run_pipeline(
    user_description: str,
    config: Optional[Config] = None,
    skip_crawl: bool = False,
    skip_filter: bool = False,
    html_only: bool = False,
    interactive: bool = True,
):
    """
    运行论文筛选 Pipeline
    
    Args:
        user_description: 用户的研究需求描述
        config: Pipeline 配置
        skip_crawl: 跳过爬取步骤
        skip_filter: 跳过筛选步骤（直接从 raw 或 filtered CSV 生成 HTML）
        html_only: 只生成 HTML（从 papers_filtered.csv）
        interactive: 是否启用交互模式
    """
    if config is None:
        config = load_config()
    
    # 只生成 HTML
    if html_only:
        print("\n" + "="*60)
        print("📄 只生成 HTML 报告")
        print("="*60)
        write_html_from_csv(
            config.output_csv_path, 
            config.output_html_path,
            subtitle=f"基于: {user_description[:50]}..."
        )
        return
    
    print("\n" + "="*60)
    print("🚀 Paper Pipeline 启动")
    print("="*60)
    print(f"📅 年份: {config.years}")
    print(f"🎓 会议: {config.conferences}")
    print(f"📁 输出目录: {config.output_dir}")
    print(f"🔄 交互模式: {'开启' if interactive else '关闭'}")
    
    # Step 1: 生成关键词和 Prompt（如果需要）
    keywords = []
    filter_prompt = ""
    
    if not skip_crawl or not skip_filter:
        print("\n" + "="*60)
        print("🧠 步骤 1/4: 生成关键词和筛选 Prompt")
        print("="*60)
        
        generated = generate_all(user_description, config.large_llm)
        keywords = generated["keywords"]
        filter_prompt = generated["fine_prompt"]
        
        if not keywords and not skip_crawl:
            print("❌ 未生成关键词，流程终止。请检查 API 配置。")
            return
        
        # 交互确认关键词
        if interactive and not skip_crawl:
            keywords = interactive_confirm_keywords(keywords)
    
    # Step 2: 爬取论文
    if skip_crawl and os.path.exists(config.raw_papers_path):
        print("\n⏭️ 跳过爬取，加载已有数据...")
        df = pd.read_csv(config.raw_papers_path)
        papers = [PaperData.from_dict(row) for _, row in df.iterrows()]
        print(f"   加载了 {len(papers)} 篇论文")
    else:
        papers = crawl_papers(config, keywords)
    
    if not papers:
        print("❌ 未获取到论文，流程终止")
        return
    
    # 交互确认是否继续
    if interactive:
        if not interactive_confirm_crawl_result(len(papers)):
            print("✅ 数据已保存，流程终止")
            return
    
    # Step 3: LLM 筛选
    if skip_filter:
        print("\n⏭️ 跳过筛选，直接生成 HTML...")
        filtered_papers = papers
    else:
        print("\n" + "="*60)
        print("🎯 步骤 3/4: DeepSeek 筛选")
        print("="*60)
        
        if interactive:
            filter_prompt = interactive_confirm_prompt("筛选", filter_prompt)
        
        llm_filter = FineFilter(config.large_llm, filter_prompt, concurrency=config.concurrency)
        filtered_papers = llm_filter.filter_papers(papers)
        
        if not filtered_papers:
            print("⚠️ 筛选后无论文通过")
            return
        
        # 保存筛选结果
        write_csv(filtered_papers, config.output_csv_path, include_filter_results=True)
    
    # Step 4: 输出 HTML
    print("\n" + "="*60)
    print("💾 步骤 4/4: 输出结果")
    print("="*60)
    
    write_html(
        filtered_papers, 
        config.output_html_path,
        subtitle=f"基于: {user_description[:50]}..."
    )
    
    # 完成
    print("\n" + "="*60)
    print("🎉 Pipeline 完成!")
    print("="*60)
    print(f"📊 统计:")
    print(f"   - 爬取论文: {len(papers)} 篇")
    print(f"   - 筛选通过: {len(filtered_papers)} 篇")
    print(f"\n📁 输出文件:")
    print(f"   - CSV: {os.path.abspath(config.output_csv_path)}")
    print(f"   - HTML: {os.path.abspath(config.output_html_path)}")


def main():
    parser = argparse.ArgumentParser(
        description="论文爬取与筛选 Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py -d "LLM 置信度估计的研究"
  python main.py -d "..." --skip-crawl          # 跳过爬取
  python main.py -d "..." --skip-filter         # 跳过筛选
  python main.py -d "..." --html-only           # 只生成 HTML
  python main.py -d "..." --no-interactive      # 非交互模式
        """
    )
    
    parser.add_argument(
        "--description", "-d",
        type=str,
        required=True,
        help="你的研究需求描述"
    )
    
    parser.add_argument(
        "--years", "-y",
        type=str,
        default="2024,2025",
        help="要爬取的年份 (默认: 2024,2025)"
    )
    
    parser.add_argument(
        "--conferences", "-c",
        type=str,
        default="ICLR,ICML,NEURIPS,ACL",
        help="要爬取的会议 (默认: ICLR,ICML,NEURIPS,ACL)"
    )
    
    parser.add_argument(
        "--no-arxiv",
        action="store_true",
        help="不爬取 Arxiv"
    )
    
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="关闭交互模式"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default="./output",
        help="输出目录 (默认: ./output)"
    )
    
    parser.add_argument(
        "--skip-crawl",
        action="store_true",
        help="跳过爬取步骤，使用已有的原始数据"
    )
    
    parser.add_argument(
        "--skip-filter",
        action="store_true",
        help="跳过 LLM 筛选步骤"
    )
    
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="只从 CSV 生成 HTML（跳过爬取和筛选）"
    )
    
    args = parser.parse_args()
    
    # 解析参数
    years = [int(y.strip()) for y in args.years.split(",")]
    conferences = [c.strip().upper() for c in args.conferences.split(",")]
    
    # 创建配置
    config = load_config(
        years=years,
        conferences=conferences,
        crawl_arxiv=not args.no_arxiv,
        output_dir=args.output_dir
    )
    
    # 运行 Pipeline
    run_pipeline(
        user_description=args.description,
        config=config,
        skip_crawl=args.skip_crawl,
        skip_filter=args.skip_filter,
        html_only=args.html_only,
        interactive=not args.no_interactive
    )


if __name__ == "__main__":
    main()
