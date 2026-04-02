import os
from openai import OpenAI
import json

def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url=base_url)

def analyze_data(data: str, prompt: str) -> str:
    client = get_openai_client()
    if not client:
        return "请先配置 OPENAI_API_KEY"
    try:
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": "你是一个数据分析助手。请根据给定的数据和问题，进行深度分析并输出结论。"},
                {"role": "user", "content": f"数据：\n{data}\n\n问题/需求：\n{prompt}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 分析失败: {e}"

def generate_comment(post_content: str, style: str = "友好") -> str:
    client = get_openai_client()
    if not client:
        return "请先配置 OPENAI_API_KEY"
    try:
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": "你是一个社区活跃用户。请根据帖子内容，生成一条相关的评论。"},
                {"role": "user", "content": f"请用【{style}】的风格，对以下帖子发表评论：\n{post_content}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 评论生成失败: {e}"

def generate_post(topic: str, requirements: str = "") -> str:
    client = get_openai_client()
    if not client:
        return "请先配置 OPENAI_API_KEY"
    try:
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": "你是一个社区管理员/运营者，擅长撰写吸引人的帖子。"},
                {"role": "user", "content": f"请以“{topic}”为主题，写一篇频道帖子。附加要求：{requirements}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 发帖生成失败: {e}"
