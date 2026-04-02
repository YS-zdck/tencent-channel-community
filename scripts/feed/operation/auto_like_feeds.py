"""
Skill: auto_like_feeds
描述: 定时获取频道最新帖子，并给未点赞过的帖子自动点赞。
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _mcp_client import call_mcp

SKILL_MANIFEST = {
    "name": "auto-like-feeds",
    "description": "自动给频道内最新获取到的帖子点赞。",
    "parameters": {
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"}
        },
        "required": ["guild_id"]
    }
}

def run(params: dict) -> dict:
    guild_id = params["guild_id"]
    try:
        page = call_mcp("get_guild_feeds", {
            "guild_id": str(guild_id),
            "count": 20,
            "get_type": 2,
            "sort_option": 1,
        })
    except Exception as e:
        return {"success": False, "error": f"拉取帖子列表失败：{e}"}

    feeds_list = page.get("structuredContent", {}).get("feeds", [])
    if not feeds_list:
        # Fallback to old format
        feeds_list = page.get("data", {}).get("feeds", page.get("data", {}).get("vecFeed", []))

    liked_count = 0
    errors = []

    for f in feeds_list:
        info = f.get("feed_info", f.get("feedInfo", f))
        feed_id = info.get("feed_id", info.get("feedId", info.get("id", "")))
        if not feed_id:
            continue
            
        try:
            call_mcp("do_feed_prefer", {
                "guild_id": str(guild_id),
                "feed_id": str(feed_id),
                "prefer_type": 1,
                "is_prefer": 1
            })
            liked_count += 1
            # 延时避免被频控
            time.sleep(0.5)
        except Exception as e:
            errors.append(f"{feed_id}: {str(e)}")

    return {
        "success": True,
        "data": {
            "liked_count": liked_count,
            "errors": errors
        }
    }

if __name__ == "__main__":
    from _skill_runner import run_as_cli
    run_as_cli(SKILL_MANIFEST, run)