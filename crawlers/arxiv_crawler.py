"""
Arxiv 爬虫 - 支持关键词过滤、年份过滤和引用量过滤
"""
import arxiv
import requests
import time
from typing import List, Optional, Dict
from .base import PaperData


def matches_keywords(title: str, abstract: str, keywords: List[str]) -> bool:
    """检查论文是否匹配关键词"""
    if not keywords:
        return True
    full_text = f"{title} {abstract}".lower()
    for kw in keywords:
        if kw.lower() in full_text:
            return True
    return False


def get_arxiv_id_from_url(url: str) -> Optional[str]:
    """从 arxiv URL 提取 arxiv ID"""
    # URL 格式: http://arxiv.org/abs/2301.12345v1
    if 'arxiv.org' in url:
        parts = url.split('/')
        for i, part in enumerate(parts):
            if part == 'abs' and i + 1 < len(parts):
                arxiv_id = parts[i + 1]
                # 移除版本号
                if 'v' in arxiv_id:
                    arxiv_id = arxiv_id.split('v')[0]
                return arxiv_id
    return None


def get_citation_count_batch(arxiv_ids: List[str]) -> Dict[str, int]:
    """
    批量获取 arxiv 论文的引用量（使用 Semantic Scholar API）
    
    Args:
        arxiv_ids: arxiv ID 列表
    
    Returns:
        {arxiv_id: citation_count} 字典
    """
    if not arxiv_ids:
        return {}
    
    results = {}
    
    # Semantic Scholar API 支持批量查询（每次最多 500 个）
    # 使用 paper/batch 端点
    batch_size = 100
    
    for i in range(0, len(arxiv_ids), batch_size):
        batch = arxiv_ids[i:i + batch_size]
        
        # 构建请求
        ids = [f"ARXIV:{aid}" for aid in batch]
        
        try:
            response = requests.post(
                "https://api.semanticscholar.org/graph/v1/paper/batch",
                json={"ids": ids},
                params={"fields": "citationCount,externalIds"},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                for paper in data:
                    if paper and paper.get('externalIds', {}).get('ArXiv'):
                        arxiv_id = paper['externalIds']['ArXiv']
                        results[arxiv_id] = paper.get('citationCount', 0) or 0
            elif response.status_code == 429:
                print("   ⚠️ Semantic Scholar API 限流，等待 5 秒...")
                time.sleep(5)
            else:
                print(f"   ⚠️ Semantic Scholar API 错误: {response.status_code}")
                
        except Exception as e:
            print(f"   ⚠️ 获取引用量失败: {e}")
        
        # 限流保护
        time.sleep(1)
    
    return results


class ArxivCrawler:
    """Arxiv 论文爬虫"""
    
    def __init__(self, min_citations: int = 5):
        """
        Args:
            min_citations: 最小引用量（低于此值的论文将被过滤）
        """
        self.client = arxiv.Client(
            page_size=100,
            delay_seconds=3.0,
            num_retries=3
        )
        self.min_citations = min_citations
    
    def crawl(
        self,
        keywords: List[str],
        years: Optional[List[int]] = None,
        max_results: int = 500,
        categories: Optional[List[str]] = None,
        filter_by_keywords: bool = True,
        filter_by_citations: bool = True
    ) -> List[PaperData]:
        """
        爬取 Arxiv 论文
        
        Args:
            keywords: 搜索关键词
            years: 年份列表，只保留这些年份的论文
            max_results: 最大结果数
            categories: Arxiv 分类 (默认: cs.CL, cs.LG, cs.AI)
            filter_by_keywords: 是否对结果进行关键词过滤
            filter_by_citations: 是否按引用量过滤
        
        Returns:
            论文列表
        """
        if not keywords:
            return []
        
        if categories is None:
            categories = ['cs.CL', 'cs.LG', 'cs.AI']
        
        # 构建查询
        keywords_query = " OR ".join([f'abs:"{k}"' for k in keywords])
        category_query = " OR ".join([f'cat:{c}' for c in categories])
        final_query = f'({keywords_query}) AND ({category_query})'
        
        print(f"🔍 [Arxiv] 搜索: {final_query[:100]}...")
        if years:
            print(f"   📅 年份限制: {min(years)}-{max(years)}")
        
        search = arxiv.Search(
            query=final_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        
        # 第一遍：收集所有符合条件的论文
        candidates = []
        filtered_by_year = 0
        filtered_by_keywords = 0
        
        try:
            for r in self.client.results(search):
                # 年份过滤
                paper_year = r.published.year
                if years and paper_year not in years:
                    filtered_by_year += 1
                    continue
                
                title = r.title.strip()
                abstract = r.summary.replace("\n", " ").strip()
                
                # 关键词二次过滤
                if filter_by_keywords and not matches_keywords(title, abstract, keywords):
                    filtered_by_keywords += 1
                    continue
                
                arxiv_id = get_arxiv_id_from_url(r.entry_id)
                
                candidates.append({
                    'title': title,
                    'abstract': abstract,
                    'authors': ", ".join([a.name for a in r.authors]),
                    'categories': ", ".join(r.categories),
                    'url': r.entry_id,
                    'year': str(paper_year),
                    'arxiv_id': arxiv_id
                })
                
        except Exception as e:
            print(f"❌ Arxiv 爬取错误: {e}")
        
        # 打印初步统计
        if years:
            print(f"   📅 年份过滤: {filtered_by_year} 篇被过滤")
        if filter_by_keywords:
            print(f"   🔑 关键词过滤: {filtered_by_keywords} 篇被过滤")
        
        # 第二遍：获取引用量并过滤
        results = []
        filtered_by_citations = 0
        
        if filter_by_citations and candidates:
            print(f"   📊 获取引用量中（共 {len(candidates)} 篇）...")
            arxiv_ids = [c['arxiv_id'] for c in candidates if c['arxiv_id']]
            citation_counts = get_citation_count_batch(arxiv_ids)
            
            for c in candidates:
                citations = citation_counts.get(c['arxiv_id'], 0)
                
                if citations < self.min_citations:
                    filtered_by_citations += 1
                    continue
                
                paper = PaperData(
                    title=c['title'],
                    abstract=c['abstract'],
                    authors=c['authors'],
                    institutions="N/A",
                    venue=f"Arxiv ({citations} citations)",
                    url=c['url'],
                    year=c['year'],
                    keywords=c['categories']
                )
                results.append(paper)
            
            print(f"   📈 引用量过滤 (>={self.min_citations}): {filtered_by_citations} 篇被过滤")
        else:
            # 不做引用量过滤
            for c in candidates:
                paper = PaperData(
                    title=c['title'],
                    abstract=c['abstract'],
                    authors=c['authors'],
                    institutions="N/A",
                    venue="Arxiv Preprint",
                    url=c['url'],
                    year=c['year'],
                    keywords=c['categories']
                )
                results.append(paper)
        
        print(f"   📊 Arxiv: 共 {len(results)} 篇论文")
        
        return results
