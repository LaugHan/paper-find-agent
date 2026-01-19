"""
Paper Pipeline 配置管理
"""
import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class LLMConfig:
    """LLM 模型配置"""
    api_key: str
    base_url: str
    model_name: str
    temperature: float = 0.1
    max_tokens: int = 4096


@dataclass
class Config:
    """Pipeline 全局配置"""
    
    # 爬虫配置
    years: List[int] = field(default_factory=lambda: [2024, 2025])
    conferences: List[str] = field(default_factory=lambda: ['ICLR', 'ICML', 'NEURIPS', 'ACL'])
    crawl_arxiv: bool = True
    arxiv_max_results: int = 500
    
    # LLM 配置
    large_llm: Optional[LLMConfig] = None
    
    # 并发配置
    concurrency: int = 10  # LLM 并发请求数
    
    # 输出配置
    output_dir: str = "./output"
    output_csv: str = "papers_filtered.csv"
    output_html: str = "papers_report.html"
    
    # 中间文件
    raw_papers_file: str = "papers_raw.csv"
    
    # 速率控制（已废弃，使用并发）
    sleep_seconds: float = 0.0
    
    def __post_init__(self):
        """初始化 LLM 配置"""
        if self.large_llm is None:
            self.large_llm = LLMConfig(
                api_key=os.getenv("SILICON_API_KEY", ""),
                base_url="https://api.siliconflow.cn/v1/chat/completions",
                model_name="deepseek-ai/DeepSeek-V3",
                temperature=0.1,
                max_tokens=4096
            )
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
    
    @property
    def raw_papers_path(self) -> str:
        return os.path.join(self.output_dir, self.raw_papers_file)
    
    @property
    def coarse_filtered_path(self) -> str:
        return os.path.join(self.output_dir, self.coarse_filtered_file)
    
    @property
    def output_csv_path(self) -> str:
        return os.path.join(self.output_dir, self.output_csv)
    
    @property
    def output_html_path(self) -> str:
        return os.path.join(self.output_dir, self.output_html)


def load_config(**overrides) -> Config:
    """加载配置，支持覆盖默认值"""
    return Config(**overrides)
