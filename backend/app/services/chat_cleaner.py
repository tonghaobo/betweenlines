import re
from typing import List


def clean_chat_content(raw_text: str) -> str:
    """
    清洗用户输入的聊天记录：
    1. 去除首尾空白
    2. 规范化换行
    3. 移除多余空行
    4. 截断过长内容（保留前后各 2500 字符）
    """
    text = raw_text.strip()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def validate_chat_format(text: str) -> List[str]:
    """
    验证聊天记录格式，返回警告列表。
    不阻止分析，仅返回提示。
    """
    warnings = []
    
    has_speaker_pattern = bool(re.search(r"^(他/她|她|他|我|she|he|me)[：:]", text, re.MULTILINE))
    
    if not has_speaker_pattern:
        # 也接受旧格式 A:/B: 以及其他常见格式
        has_legacy_pattern = bool(re.search(r"^[A-Za-z\u4e00-\u9fff]+[：:]", text, re.MULTILINE))
        if not has_legacy_pattern:
            warnings.append("未检测到明显的对话格式，分析结果可能不准确。建议使用 '他/她: xxx' 和 '我: xxx' 格式。")
    
    lines = [l for l in text.split("\n") if l.strip()]
    if len(lines) < 2:
        warnings.append("对话轮次过少，建议提供更多上下文。")
    
    return warnings


def is_potentially_harmful(text: str) -> bool:
    """
    检查内容是否可能包含违规内容。
    V1 阶段使用简单的关键词匹配。
    """
    harmful_keywords = [
        "PUA", "pua", "把妹", "泡妞", "搭讪话术",
        "操控", "跟踪", "骚扰", "情色",
    ]
    
    text_lower = text.lower()
    for keyword in harmful_keywords:
        if keyword.lower() in text_lower:
            return True
    return False
