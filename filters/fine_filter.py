"""
LLM 筛选器 - 支持并发推理
"""
import asyncio
from typing import List
from tqdm import tqdm

from config import LLMConfig
from crawlers.base import PaperData
from .base import SiliconFlowClient, parse_xml_response


class FineFilter:
    """LLM 筛选器（支持并发）"""
    
    def __init__(self, config: LLMConfig, prompt_template: str, concurrency: int = 10):
        """
        Args:
            config: LLM 配置
            prompt_template: 筛选 prompt 模板，包含 {title} 和 {abstract} 占位符
            concurrency: 并发数
        """
        self.client = SiliconFlowClient(config)
        self.prompt_template = prompt_template
        self.system_prompt = "你是一个严谨的学术论文筛选助手。"
        self.concurrency = concurrency
    
    def build_prompt(self, title: str, abstract: str) -> str:
        """构建筛选 prompt"""
        return self.prompt_template.format(title=title, abstract=abstract)
    
    def filter_papers(
        self,
        papers: List[PaperData],
        sleep_seconds: float = 0.0  # 并发模式下不需要 sleep
    ) -> List[PaperData]:
        """
        批量筛选论文（并发）
        
        Args:
            papers: 待筛选论文列表
            sleep_seconds: 已废弃，保留参数兼容性
        
        Returns:
            通过筛选的论文列表
        """
        print(f"\n🔍 [LLM筛选] 开始筛选 {len(papers)} 篇论文（并发数: {self.concurrency}）...")
        
        # 构建所有 prompts
        prompts = [self.build_prompt(p.title, p.abstract) for p in papers]
        
        # 并发调用
        results = asyncio.run(self._filter_batch_async(prompts, papers))
        
        print(f"   ✅ 筛选完成，保留 {len(results)} 篇论文")
        return results
    
    async def _filter_batch_async(
        self, 
        prompts: List[str], 
        papers: List[PaperData]
    ) -> List[PaperData]:
        """异步批量筛选"""
        
        # 使用 tqdm 显示进度
        pbar = tqdm(total=len(prompts), desc="筛选进度")
        
        results = []
        batch_size = self.concurrency * 2  # 每批处理的数量
        
        for i in range(0, len(prompts), batch_size):
            batch_prompts = prompts[i:i + batch_size]
            batch_papers = papers[i:i + batch_size]
            
            # 并发调用这一批
            responses = await self.client.call_batch_async(
                batch_prompts,
                self.system_prompt,
                concurrency=self.concurrency
            )
            
            # 处理响应
            for paper, response in zip(batch_papers, responses):
                if response:
                    is_relevant, reason, abstract_zh = parse_xml_response(response)
                    if is_relevant:
                        paper.reason_zh = reason
                        paper.abstract_zh = abstract_zh
                        results.append(paper)
                pbar.update(1)
            
            # 短暂休息避免限流
            await asyncio.sleep(0.5)
        
        pbar.close()
        return results


# 默认的筛选 prompt 模板
DEFAULT_FINE_PROMPT = """
你是一个严谨的科研助手。我会提供一篇论文的标题和摘要，请你判断这篇论文是否与研究主题密切相关。

相关性的判定标准是：论文需要实质性地讨论研究主题，而不仅仅是顺带提到这些词。

请严格按照下面的格式用中文输出，不要添加多余说明：

<is_relevant>
true 或 false
</is_relevant>

<reason_zh>
如果是 true，用一两句话中文解释为什么相关；如果是 false，这一段可以留空。
</reason_zh>

<abstract_zh>
如果是 true，请将论文摘要翻译成中文；如果是 false，这一段可以留空。
</abstract_zh>

论文标题: {title}

论文摘要: {abstract}
"""
