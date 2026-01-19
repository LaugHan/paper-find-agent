"""
论文数据基类
"""
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class PaperData:
    """论文数据结构"""
    title: str
    abstract: str
    authors: str
    institutions: str
    venue: str
    url: str
    year: str
    keywords: str = ""
    
    # 筛选结果字段（可选）
    is_relevant: Optional[bool] = None
    reason_zh: Optional[str] = None
    abstract_zh: Optional[str] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'Title': self.title,
            'Venue': self.venue,
            'Year': self.year,
            'Abstract': self.abstract,
            'Authors': self.authors,
            'Institutions': self.institutions,
            'Keywords': self.keywords,
            'Link': self.url,
        }
    
    def to_full_dict(self) -> dict:
        """转换为完整字典（包含筛选结果）"""
        d = self.to_dict()
        if self.reason_zh:
            d['ReasonZh'] = self.reason_zh
        if self.abstract_zh:
            d['AbstractZh'] = self.abstract_zh
        return d
    
    @classmethod
    def from_dict(cls, d: dict) -> 'PaperData':
        """从字典创建"""
        return cls(
            title=str(d.get('Title', '')).strip(),
            abstract=str(d.get('Abstract', '')).strip(),
            authors=str(d.get('Authors', '')),
            institutions=str(d.get('Institutions', '')),
            venue=str(d.get('Venue', '')),
            url=str(d.get('Link', '')),
            year=str(d.get('Year', '')),
            keywords=str(d.get('Keywords', '')),
            reason_zh=d.get('ReasonZh'),
            abstract_zh=d.get('AbstractZh'),
        )
