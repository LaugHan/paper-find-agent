"""
LLM 调用基类 - 支持同步和异步并发调用
"""
import re
import time
import asyncio
import aiohttp
import requests
from abc import ABC, abstractmethod
from typing import Tuple, Optional, List
from openai import OpenAI

from config import LLMConfig


class BaseLLMClient(ABC):
    """LLM 客户端基类"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    def call(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """调用 LLM"""
        pass


class OpenAICompatibleClient(BaseLLMClient):
    """OpenAI 兼容接口客户端（支持 InternLM 等）"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
    
    def call(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"  ❌ API 调用出错: {e}")
            if "429" in str(e):
                print("  ⚠️ 触发限流，暂停 5 秒...")
                time.sleep(5)
            return None


class SiliconFlowClient(BaseLLMClient):
    """SiliconFlow API 客户端（支持 DeepSeek 等）- 支持并发"""
    
    def call(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """同步调用"""
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "stream": False,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": 0.7,
        }
        
        try:
            response = requests.post(
                self.config.base_url,
                json=payload,
                headers=headers,
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  ❌ API 调用出错: {e}")
            return None

    async def call_async(
        self, 
        session: aiohttp.ClientSession,
        prompt: str, 
        system_prompt: str = "",
        index: int = 0
    ) -> Tuple[int, Optional[str]]:
        """异步调用"""
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "stream": False,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": 0.7,
        }
        
        try:
            async with session.post(
                self.config.base_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return index, data["choices"][0]["message"]["content"]
                elif response.status == 429:
                    # 限流，等待后重试
                    await asyncio.sleep(5)
                    return index, None
                else:
                    return index, None
        except Exception as e:
            return index, None

    async def call_batch_async(
        self,
        prompts: List[str],
        system_prompt: str = "",
        concurrency: int = 10
    ) -> List[Optional[str]]:
        """
        批量异步调用
        
        Args:
            prompts: prompt 列表
            system_prompt: 系统 prompt
            concurrency: 并发数
        
        Returns:
            响应列表（保持顺序）
        """
        results = [None] * len(prompts)
        semaphore = asyncio.Semaphore(concurrency)
        
        async def limited_call(session, prompt, idx):
            async with semaphore:
                return await self.call_async(session, prompt, system_prompt, idx)
        
        connector = aiohttp.TCPConnector(limit=concurrency)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [
                limited_call(session, prompt, i) 
                for i, prompt in enumerate(prompts)
            ]
            
            for coro in asyncio.as_completed(tasks):
                idx, result = await coro
                results[idx] = result
        
        return results


def parse_xml_response(text: str) -> Tuple[bool, str, str]:
    """
    解析 XML 格式的 LLM 响应
    
    Returns:
        (is_relevant, reason_zh, abstract_zh)
    """
    if not text:
        return False, "", ""
    
    def extract_tag(tag: str) -> str:
        # 尝试多种标签格式
        patterns = [
            rf'<{tag}>\s*(.*?)\s*</{tag}>',
            rf'<{tag}>(.*?)</{tag}>',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.S | re.I)
            if match:
                return match.group(1).strip()
        return ""
    
    # 提取相关性
    rel_text = extract_tag("is_relevant")
    is_relevant = any(v in rel_text.lower() for v in ['true', '是', 'yes'])
    
    reason_zh = ""
    abstract_zh = ""
    
    if is_relevant:
        # 尝试多种标签名
        reason_zh = extract_tag("reason_zh") or extract_tag("reason")
        abstract_zh = extract_tag("abstract_zh") or extract_tag("translation")
        
        # 截断过长的理由
        if len(reason_zh) > 200:
            reason_zh = reason_zh[:197] + "..."
    
    return is_relevant, reason_zh, abstract_zh
