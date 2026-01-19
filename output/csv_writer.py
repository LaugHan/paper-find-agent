"""
CSV 输出模块
"""
import csv
import os
from typing import List
from crawlers.base import PaperData


def write_csv(papers: List[PaperData], output_path: str, include_filter_results: bool = True):
    """
    将论文列表写入 CSV 文件
    
    Args:
        papers: 论文列表
        output_path: 输出文件路径
        include_filter_results: 是否包含筛选结果（理由和翻译）
    """
    if not papers:
        print("⚠️ 没有论文可写入")
        return
    
    # 确保目录存在
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    # 定义列
    if include_filter_results:
        headers = ['Title', 'Venue', 'Year', 'Link', 'ReasonZh', 'AbstractZh', 'Abstract', 'Authors', 'Institutions', 'Keywords']
    else:
        headers = ['Title', 'Venue', 'Year', 'Abstract', 'Authors', 'Institutions', 'Keywords', 'Link']
    
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for paper in papers:
            if include_filter_results:
                row = [
                    paper.title,
                    paper.venue,
                    paper.year,
                    paper.url,
                    paper.reason_zh or "",
                    paper.abstract_zh or "",
                    paper.abstract,
                    paper.authors,
                    paper.institutions,
                    paper.keywords
                ]
            else:
                row = [
                    paper.title,
                    paper.venue,
                    paper.year,
                    paper.abstract,
                    paper.authors,
                    paper.institutions,
                    paper.keywords,
                    paper.url
                ]
            writer.writerow(row)
    
    print(f"💾 已保存 {len(papers)} 篇论文到: {os.path.abspath(output_path)}")


def append_csv(papers: List[PaperData], output_path: str):
    """追加论文到现有 CSV 文件"""
    if not papers:
        return
    
    file_exists = os.path.exists(output_path)
    
    with open(output_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        
        if not file_exists:
            headers = ['Title', 'Venue', 'Year', 'Abstract', 'Authors', 'Institutions', 'Keywords', 'Link']
            writer.writerow(headers)
        
        for paper in papers:
            writer.writerow([
                paper.title,
                paper.venue,
                paper.year,
                paper.abstract,
                paper.authors,
                paper.institutions,
                paper.keywords,
                paper.url
            ])
    
    print(f"💾 已追加 {len(papers)} 篇论文到: {output_path}")
