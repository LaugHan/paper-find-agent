"""
Prompt 自动生成器 - 根据用户需求描述生成关键词和筛选 prompt
"""
import re
from typing import Dict, List
from config import LLMConfig
from filters.base import SiliconFlowClient


GENERATOR_TEMPLATE = """
你是一个 AI 研究助手。用户会给出一段关于他们感兴趣的研究方向的描述，你需要：

1. 生成 4-6 个精准的论文搜索关键词
2. 生成一个用于论文筛选的 prompt

用户需求描述：
{user_description}

## 任务 1: 生成搜索关键词

生成 4-6 个用于论文搜索和预筛选的关键词。要求：
- 关键词要足够具体，能够精准定位到用户感兴趣的研究方向
- 不要直接使用过于宽泛的词（如 大语言模型、AI、机器学习这类词或含义，会匹配太多无关论文）
- 关键词应该覆盖用户需求的不同侧面
- 使用英文关键词（学术论文多为英文）
- 一个关键词由2-3个单词组成
- 当用户指定关键词时，直接使用用户指定的关键词

## 任务 2: 生成筛选 Prompt

生成一个用于 LLM 筛选论文的 prompt，要求：
- 包含 {{title}} 和 {{abstract}} 占位符（注意：使用双花括号）
- 详细说明判定标准，包含具体的研究问题列表
- 要求模型输出 XML 格式的结果，包含 <is_relevant>, <reason_zh>, <abstract_zh> 三个标签
- 如果相关，需要给出中文理由和中文翻译的摘要

## 输出格式

请严格按照以下 XML 格式输出：

<keywords>
关键词1, 关键词2, 关键词3, 关键词4, 关键词5
</keywords>

<prompt>
（这里填写筛选 prompt）
</prompt>
"""


def generate_all(user_description: str, llm_config: LLMConfig) -> Dict:
    """
    根据用户需求描述，调用大模型生成关键词和筛选 prompt
    
    Args:
        user_description: 用户的研究需求描述
        llm_config: 大模型配置
    
    Returns:
        {
            "keywords": List[str],
            "fine_prompt": str  # 保持兼容性
        }
    """
    print("\n🧠 正在根据您的需求生成关键词和筛选 Prompt...")
    
    client = SiliconFlowClient(llm_config)
    prompt = GENERATOR_TEMPLATE.format(user_description=user_description)
    
    response = client.call(
        prompt, 
        system_prompt="你是一个专业的 AI 研究助手，擅长理解用户需求并生成高质量的搜索关键词和筛选 prompt。"
    )
    
    if not response:
        print("   ❌ 生成失败，将使用默认配置")
        return get_defaults()
    
    # 解析响应
    keywords = extract_keywords(response)
    filter_prompt = extract_tag(response, "prompt")
    
    # 验证和补充
    if not keywords:
        print("   ⚠️ 关键词生成失败，请手动指定")
        keywords = []
    
    if not filter_prompt:
        print("   ⚠️ Prompt 解析失败，将使用默认模板")
        filter_prompt = get_defaults()["fine_prompt"]
    
    # 打印结果
    print("   ✅ 生成完成")
    print("\n" + "="*60)
    print("🔑 生成的搜索关键词:")
    print("-"*60)
    for i, kw in enumerate(keywords, 1):
        print(f"   {i}. {kw}")
    print("\n" + "="*60)
    print("📝 生成的筛选 Prompt:")
    print("-"*60)
    print(filter_prompt[:500] + "..." if len(filter_prompt) > 500 else filter_prompt)
    print("="*60 + "\n")
    
    return {
        "keywords": keywords,
        "fine_prompt": filter_prompt,
        "coarse_prompt": filter_prompt  # 保持兼容性，不再使用
    }


def extract_tag(text: str, tag: str) -> str:
    """提取 XML 标签内容"""
    pattern = rf'<{tag}>\s*(.*?)\s*</{tag}>'
    match = re.search(pattern, text, re.S | re.I)
    if match:
        return match.group(1).strip()
    return ""


def extract_keywords(text: str) -> List[str]:
    """提取关键词列表"""
    keywords_text = extract_tag(text, "keywords")
    if not keywords_text:
        return []
    
    # 分割关键词（支持逗号、顿号等分隔）
    keywords = re.split(r'[,，、\n]+', keywords_text)
    # 清理并过滤
    keywords = [kw.strip() for kw in keywords if kw.strip()]
    # 限制数量
    return keywords[:8]


def get_defaults() -> Dict:
    """获取默认配置"""
    from filters.fine_filter import DEFAULT_FINE_PROMPT
    return {
        "keywords": [],
        "fine_prompt": DEFAULT_FINE_PROMPT,
        "coarse_prompt": DEFAULT_FINE_PROMPT
    }
