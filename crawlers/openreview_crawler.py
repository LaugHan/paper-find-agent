"""
OpenReview 爬虫 - 支持 ICLR, NeurIPS, ICML, ACL
支持关键词预过滤
"""
import openreview
from tqdm import tqdm
from typing import List, Optional
from .base import PaperData


def get_content_val(content, key, default=''):
    """
    兼容 OpenReview V1 和 V2 API 的内容提取
    V2: {'value': 'xxx'}
    V1: 'xxx'
    """
    if not content:
        return default
    val = content.get(key)
    if val is None:
        return default
    if isinstance(val, dict) and 'value' in val:
        return val['value']
    return val


def matches_keywords(title: str, abstract: str, paper_keywords: List[str], search_keywords: List[str]) -> bool:
    """
    检查论文是否匹配搜索关键词
    
    Args:
        title: 论文标题
        abstract: 摘要
        paper_keywords: 论文自带的关键词
        search_keywords: 搜索关键词列表
    
    Returns:
        True 如果匹配任意一个关键词
    """
    if not search_keywords:
        return True  # 没有关键词限制时，通过所有论文
    
    # 合并所有可搜索文本
    full_text = f"{title} {abstract} {' '.join(paper_keywords)}".lower()
    
    # 检查是否匹配任意关键词
    for kw in search_keywords:
        if kw.lower() in full_text:
            return True
    
    return False


class OpenReviewCrawler:
    """OpenReview 论文爬虫"""
    
    def __init__(self, year: int):
        self.client = openreview.api.OpenReviewClient(
            baseurl='https://api2.openreview.net'
        )
        self.year = str(year)
    
    def _get_venue_id(self, conf_name: str) -> Optional[str]:
        """获取会议的 venue ID"""
        conf = conf_name.upper()
        y = self.year
        
        if conf == 'ICLR':
            return f'ICLR.cc/{y}/Conference'
        elif conf in ['NEURIPS', 'NIPS']:
            return f'NeurIPS.cc/{y}/Conference'
        elif conf == 'ICML':
            return f'ICML.cc/{y}/Conference'
        elif conf == 'ACL':
            return f'aclweb.org/ACL/{y}'
        
        return None
    
    def _get_acl_invitations(self) -> List[str]:
        """获取 ACL ARR 的 invitation IDs"""
        y = self.year
        if y == '2024':
            months = ['February', 'April', 'June', 'October']
        elif y == '2025':
            months = ['May', 'July', 'October']
        else:
            months = ['February', 'April', 'June', 'October', 'May', 'July']
        
        return [f'aclweb.org/ACL/ARR/{y}/{m}/-/Submission' for m in months]
    
    def crawl(self, conf_name: str, keywords: Optional[List[str]] = None) -> List[PaperData]:
        """
        爬取指定会议的论文
        
        Args:
            conf_name: 会议名称 (ICLR, ICML, NEURIPS, ACL)
            keywords: 关键词列表，用于预过滤论文（可选）
        
        Returns:
            论文列表
        """
        conf_upper = conf_name.upper()
        
        # 获取 submissions
        submissions = []
        
        if conf_upper == 'ACL':
            # ACL 使用 ARR 系统，按月份爬取
            invitations = self._get_acl_invitations()
            for inv in invitations:
                print(f"🔍 [OpenReview] 获取 {inv} ...")
                try:
                    batch = self.client.get_all_notes(invitation=inv)
                    print(f"   ✅ 获取到 {len(batch)} 篇")
                    submissions.extend(batch)
                except Exception as e:
                    if "Forbidden" in str(e) or "NotFoundError" in str(e):
                        print(f"   ⚠️ 无法访问 {inv}")
                    else:
                        print(f"   ❌ 错误: {e}")
        else:
            # 其他会议使用 venue ID
            venue_id = self._get_venue_id(conf_name)
            if not venue_id:
                print(f"⚠️ 未配置会议: {conf_name}")
                return []
            
            print(f"🔍 [OpenReview] 获取 {venue_id} ...")
            try:
                submissions = self.client.get_all_notes(
                    content={'venueid': venue_id}
                )
                print(f"   ✅ 获取到 {len(submissions)} 篇")
            except Exception as e:
                if "Forbidden" in str(e) or "NotFoundError" in str(e):
                    print(f"   ⚠️ 无法访问 {venue_id}")
                else:
                    print(f"   ❌ 错误: {e}")
                return []
        
        if not submissions:
            print(f"⚠️ {conf_name} {self.year} 未获取到论文")
            return []
        
        # 解析论文数据（带关键词过滤）
        results = []
        seen = set()
        filtered_count = 0
        
        for note in tqdm(submissions, desc=f"解析 {conf_name} {self.year}"):
            if note.id in seen:
                continue
            seen.add(note.id)
            
            content = note.content
            title = get_content_val(content, 'title')
            abstract = get_content_val(content, 'abstract')
            
            if not title or not abstract:
                continue
            
            # 提取论文关键词
            kw_list = get_content_val(content, 'keywords', [])
            if not isinstance(kw_list, list):
                kw_list = []
            
            # 关键词预过滤
            if keywords and not matches_keywords(title, abstract, kw_list, keywords):
                filtered_count += 1
                continue
            
            keywords_str = ", ".join(kw_list)
            
            # 提取作者
            authors_list = get_content_val(content, 'authors', [])
            authors_str = ", ".join(authors_list) if isinstance(authors_list, list) else str(authors_list)
            
            # 提取机构（从邮箱后缀）
            author_ids = get_content_val(content, 'authorids', [])
            institutions = set()
            if isinstance(author_ids, list):
                for uid in author_ids:
                    if '@' in str(uid):
                        institutions.add(str(uid).split('@')[-1])
            institutions_str = ", ".join(institutions)
            
            paper = PaperData(
                title=str(title).strip(),
                abstract=str(abstract).strip().replace('\n', ' '),
                authors=authors_str,
                institutions=institutions_str,
                venue=f"{conf_name} {self.year}",
                url=f"https://openreview.net/forum?id={note.id}",
                year=self.year,
                keywords=keywords_str
            )
            results.append(paper)
        
        # 打印统计
        if keywords:
            print(f"   🔑 关键词过滤: {filtered_count} 篇被过滤")
        print(f"   📊 {conf_name} {self.year}: 共 {len(results)} 篇论文")
        
        return results
