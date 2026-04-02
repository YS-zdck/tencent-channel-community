import streamlit as st
import os
import json
import time
from datetime import datetime, timedelta
from tool_runner import run_tool
import ai_helper
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.resolve()
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)
os.environ["QQ_AI_CONNECT_DOTENV"] = str(ENV_FILE)

st.set_page_config(page_title="频道控制台", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# ---- Custom CSS ----
st.markdown("""
<style>
.st-emotion-cache-1y4p8pa { padding-top: 2rem; }
div[data-testid="stMetricValue"] { font-size: 2.2rem; color: #1f77b4; font-weight: bold; }
.stButton>button { border-radius: 8px; width: 100%; font-weight: 500; }
.stContainer { border-radius: 12px; }
h1, h2, h3, h4 { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
</style>
""", unsafe_allow_html=True)

# ---- Helper Functions ----
def get_channel_list(guild_id):
    """获取指定频道下的所有子版块列表，返回格式 [{"id": "xxx", "name": "xxx"}]"""
    res = run_tool("scripts/manage/read/get_guild_channel_list.py", {"guild_id": guild_id})
    channels_options = []
    if res.get("code") == 0 or res.get("success") is True:
        channels = res.get("data", {}).get("channels", res.get("data", {}).get("vecChannel", []))
        for c in channels:
            c_info = c.get("channelInfo", c.get("channel_info", c))
            c_name = c_info.get("channelName", c_info.get("channel_name", "未命名版块"))
            c_id = c_info.get("channelId", c_info.get("channel_id", ""))
            if c_id:
                channels_options.append({"id": str(c_id), "name": f"{c_name} (ID:{c_id})"})
    return channels_options

def load_my_guilds():
    if "my_guilds" not in st.session_state:
        st.session_state.my_guilds = []
        
    try:
        res = run_tool("scripts/manage/read/get_my_join_guild_info.py", {})
        if isinstance(res, dict) and res.get("code") == 0:
            data = res.get("data", {})
            options = []
            
            # Helper to parse guild info from the new structure
            def add_guilds(guild_list, tag):
                for g in guild_list:
                    info = g.get("msgGuildInfo", {})
                    gid = g.get("uint64GuildId", "")
                    gname = info.get("bytesGuildName", "未知频道")
                    if gid:
                        options.append({"id": str(gid), "name": f"[{tag}] {gname}"})
            
            add_guilds(data.get("created_guilds", []), "创建")
            add_guilds(data.get("managed_guilds", []), "管理")
            add_guilds(data.get("joined_guilds", []), "加入")
            
            st.session_state.my_guilds = options
            return options
    except Exception as e:
        print(f"Failed to load guilds: {e}")
        pass
        
    return st.session_state.my_guilds

# ---- Dialogs ----
@st.dialog("⚙️ 环境与系统配置", width="large")
def config_dialog():
    st.info("配置信息将保存在本地 .env 文件中，不会影响远程仓库，随时可修改。")
    st.subheader("QQ 频道接口配置")
    token = st.text_input("QQ_AI_CONNECT_TOKEN", type="password", value=os.environ.get("QQ_AI_CONNECT_TOKEN", ""))
    
    st.subheader("AI (OpenAI 协议) 配置")
    col1, col2 = st.columns(2)
    with col1:
        openai_key = st.text_input("OPENAI_API_KEY", type="password", value=os.environ.get("OPENAI_API_KEY", ""))
    with col2:
        openai_url = st.text_input("OPENAI_BASE_URL (可选)", value=os.environ.get("OPENAI_BASE_URL", ""))
    openai_model = st.text_input("OPENAI_MODEL (可选)", value=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"))
    
    st.divider()
    col_save, col_verify = st.columns(2)
    with col_save:
        if st.button("💾 保存配置", use_container_width=True, type="primary"):
            import sys
            sys.path.append(str(BASE_DIR / "scripts" / "manage"))
            try:
                from common import write_dotenv_qq_token
                write_dotenv_qq_token(ENV_FILE, token)
            except Exception as e:
                st.error(f"写入 QQ Token 失败: {e}")
                
            # append other envs
            content = ENV_FILE.read_text() if ENV_FILE.exists() else ""
            lines = [l for l in content.splitlines() if not l.startswith("OPENAI_")]
            lines.append(f'OPENAI_API_KEY="{openai_key}"')
            lines.append(f'OPENAI_BASE_URL="{openai_url}"')
            lines.append(f'OPENAI_MODEL="{openai_model}"')
            ENV_FILE.write_text("\n".join(lines) + "\n")
            
            os.environ["QQ_AI_CONNECT_TOKEN"] = token
            os.environ["OPENAI_API_KEY"] = openai_key
            os.environ["OPENAI_BASE_URL"] = openai_url
            os.environ["OPENAI_MODEL"] = openai_model
            st.session_state.my_guilds = [] # Force reload guilds
            st.success("✅ 配置已保存并生效！")
            st.rerun()
            
    with col_verify:
        if st.button("🔌 验证 Token 连通性", use_container_width=True):
            with st.spinner("正在验证..."):
                res = run_tool("scripts/manage/read/verify_qq_ai_connect_token.py", {})
                if res.get("code") == 0 and res.get("data", {}).get("valid"):
                    st.success("✅ 验证成功：Token 可正常连接 QQ 频道！")
                    st.json(res.get("data"))
                else:
                    st.error("❌ 验证失败！请检查 Token 是否有效。")
                    st.json(res)

@st.dialog("📝 发布新帖子", width="large")
def publish_post_dialog(guild_id):
    st.write(f"当前操作频道 ID: `{guild_id}`")
    
    # 动态获取发帖版块列表
    channels = get_channel_list(guild_id)
    if not channels:
        st.error("未能获取到该频道的子版块列表，可能无权限或频道为空。")
        return
        
    # 用户显式选择版块
    selected_channel_name = st.selectbox(
        "📍 选择发帖目标版块", 
        options=[c["name"] for c in channels]
    )
    
    # 解析出选中的 channel_id
    selected_channel_id = ""
    for c in channels:
        if c["name"] == selected_channel_name:
            selected_channel_id = c["id"]
            break
            
    st.divider()

    tab1, tab2, tab3 = st.tabs(["✍️ 直接发布", "🤖 AI 创作", "📑 AI 总结发帖"])
    
    with tab1:
        title = st.text_input("帖子标题", key="pub_title")
        content = st.text_area("帖子正文", key="pub_content", height=200)
        if st.button("🚀 立即发布", use_container_width=True, type="primary"):
            with st.spinner("正在发布..."):
                res = run_tool("scripts/feed/write/publish_feed.py", {"guild_id": guild_id, "channel_id": selected_channel_id, "title": title, "content": content})
                if res.get("code") == 0 or res.get("success") is True: 
                    st.success("发布成功！")
                else: 
                    st.error(f"发布失败: {res.get('msg', res)}")
                
    with tab2:
        topic = st.text_input("发帖主题")
        reqs = st.text_area("附加要求 (例如：语气幽默，不少于300字)", height=80)
        if st.button("✨ AI 生成并发布", use_container_width=True, type="primary"):
            with st.spinner("AI 正在头脑风暴并发布..."):
                generated = ai_helper.generate_post(topic, reqs)
                st.text_area("生成的正文 (预览)", value=generated, height=200, disabled=True)
                res = run_tool("scripts/feed/write/publish_feed.py", {"guild_id": guild_id, "channel_id": selected_channel_id, "title": topic, "content": generated})
                if res.get("code") == 0 or res.get("success") is True: 
                    st.success("发布成功！")
                else: 
                    st.error(f"发布失败: {res.get('msg', res)}")
                    
    with tab3:
        source_data = st.text_area("输入需要总结的数据源 (例如长文章、群聊记录、新闻等)", height=150)
        if st.button("📝 总结并发布", use_container_width=True, type="primary"):
            with st.spinner("AI 正在提炼核心内容并发布..."):
                generated = ai_helper.analyze_data(source_data, "请总结以上内容，提取核心信息，并写成一篇适合在社区分享的帖子，条理清晰。")
                st.text_area("生成的总结 (预览)", value=generated, height=200, disabled=True)
                res = run_tool("scripts/feed/write/publish_feed.py", {"guild_id": guild_id, "channel_id": selected_channel_id, "title": "今日资讯总结", "content": generated})
                if res.get("code") == 0 or res.get("success") is True: 
                    st.success("发布成功！")
                else: 
                    st.error(f"发布失败: {res.get('msg', res)}")

@st.dialog("💬 发表评论", width="large")
def comment_dialog(guild_id, feed_id, post_content):
    st.markdown("### 原帖内容")
    st.info(post_content[:300] + ("..." if len(post_content)>300 else ""))
    
    tab1, tab2 = st.tabs(["✍️ 直接评论", "🤖 AI 辅助评论"])
    with tab1:
        cmt_content = st.text_area("输入你的评论...", key=f"cmt_input_{feed_id}", height=150)
        if st.button("发送评论", use_container_width=True, type="primary"):
            res = run_tool("scripts/feed/write/do_comment.py", {"guild_id": guild_id, "feed_id": feed_id, "content": cmt_content})
            if res.get("code") == 0: 
                st.success("评论成功！")
            else: 
                st.error(f"评论失败: {res.get('msg')}")
                
    with tab2:
        col1, col2 = st.columns([1, 2])
        with col1:
            style = st.selectbox("选择 AI 评论风格", ["友好赞同", "幽默风趣", "专业分析", "委婉反驳"])
        with col2:
            st.write("")
            st.write("")
            if st.button("✨ 生成并发送", use_container_width=True, type="primary"):
                with st.spinner("生成中..."):
                    generated = ai_helper.generate_comment(post_content, style)
                    st.success(f"**已发送:**\n{generated}")
                    res = run_tool("scripts/feed/write/do_comment.py", {"guild_id": guild_id, "feed_id": feed_id, "content": generated})
                    if res.get("code") != 0: 
                        st.error(f"发送失败: {res.get('msg')}")

@st.dialog("↩️ 回复评论", width="large")
def reply_dialog(guild_id, feed_id, comment_id, comment_content):
    st.markdown("### 回复目标")
    st.info(comment_content)
    
    tab1, tab2 = st.tabs(["✍️ 直接回复", "🤖 AI 辅助回复"])
    with tab1:
        reply_text = st.text_area("输入回复内容...", key=f"rep_input_{comment_id}", height=120)
        if st.button("发送回复", use_container_width=True, type="primary"):
            res = run_tool("scripts/feed/write/do_reply.py", {"guild_id": guild_id, "feed_id": feed_id, "comment_id": comment_id, "content": reply_text})
            if res.get("code") == 0: 
                st.success("回复成功！")
            else: 
                st.error(f"回复失败: {res.get('msg')}")
                
    with tab2:
        style = st.selectbox("选择 AI 回复风格", ["友好", "幽默", "专业补充", "委婉反驳"], key=f"rep_style_{comment_id}")
        if st.button("✨ 生成并发送", key=f"rep_ai_{comment_id}", use_container_width=True, type="primary"):
            with st.spinner("AI 生成中..."):
                generated = ai_helper.generate_comment(comment_content, style)
                st.success(f"**已发送:**\n{generated}")
                res = run_tool("scripts/feed/write/do_reply.py", {"guild_id": guild_id, "feed_id": feed_id, "comment_id": comment_id, "content": generated})
                if res.get("code") != 0: 
                    st.error(f"回复失败: {res.get('msg')}")

@st.dialog("👁️ 帖子详情与评论", width="large")
def post_details_dialog(guild_id, feed_id, title, content):
    st.markdown(f"## {title}")
    st.write(content)
    st.divider()
    
    st.subheader("💬 评论列表")
    with st.spinner("加载评论中..."):
        res = run_tool("scripts/feed/read/get_feed_comments.py", {"guild_id": guild_id, "feed_id": feed_id})
        
    if res.get("code") == 0 or res.get("success") is True:
        data = res.get("data", {})
        comments = data.get("comments", data.get("vecComment", []))
        
        if not comments:
            st.info("暂无评论，快来抢沙发吧！")
        else:
            for cmt in comments:
                cmt_id = cmt.get("comment_id", cmt.get("commentId", ""))
                # support both new flat structure and old nested structure
                if "content" in cmt and isinstance(cmt["content"], dict):
                    cmt_content = cmt["content"].get("text", "无内容")
                else:
                    cmt_content = cmt.get("content", "无内容")
                
                author = cmt.get("author", cmt.get("poster_info", {}).get("nick_name", "匿名"))
                
                with st.container(border=True):
                    st.markdown(f"**👤 {author}**:  \n{cmt_content}")
                    if st.button("↩️ 回复此评论", key=f"btn_rep_{cmt_id}"):
                        reply_dialog(guild_id, feed_id, cmt_id, cmt_content)
    else:
        st.error("获取评论失败: " + str(res.get("msg", res)))

# ---- Sidebar & Navigation ----
with st.sidebar:
    st.title("🚀 频道控制台")
    st.markdown("高效、智能的腾讯频道社区管理端")
    
    # Global Guild Selector
    st.subheader("📌 目标频道选择")
    
    # Check if we should load guilds
    if st.button("🔄 刷新获取频道列表", use_container_width=True):
        st.session_state.my_guilds = []
        load_my_guilds()
        st.rerun()

    guilds_options = st.session_state.get("my_guilds", [])
    
    if not guilds_options:
        st.warning("暂未获取到频道列表，可以点击上方刷新，或直接输入 ID。")
        selected_guild = st.text_input("手动输入频道 ID", value=st.session_state.get("global_guild_id", ""))
        if selected_guild:
            st.session_state.global_guild_id = selected_guild
    else:
        # Get index of currently selected guild
        current_gid = st.session_state.get("global_guild_id", "")
        default_index = 0
        for i, g in enumerate(guilds_options):
            if g["id"] == current_gid:
                default_index = i
                break
                
        selected_name = st.selectbox(
            "选择操作频道", 
            options=[g["name"] for g in guilds_options],
            index=default_index,
            label_visibility="collapsed"
        )
        
        # Update global guild ID based on selection
        for g in guilds_options:
            if g["name"] == selected_name:
                st.session_state.global_guild_id = g["id"]
                break

    st.divider()
    
    page = st.radio("导航菜单", [
        "📊 数据仪表盘", 
        "📰 帖子与互动", 
        "👥 频道与成员", 
        "🧠 AI 数据与发帖",
        "🔔 自动化任务"
    ], label_visibility="collapsed")

    st.divider()
    if st.button("⚙️ 环境与系统配置", use_container_width=True):
        config_dialog()

# Get global guild ID
g_id = st.session_state.get("global_guild_id", "")

# ---- Main Pages ----
if page == "📊 数据仪表盘":
    st.title("📊 数据仪表盘 Dashboard")
    st.markdown("欢迎使用腾讯频道社区控制台，为您提供直观的数据与快捷操作！")
    
    st.divider()
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("已加入频道数", len(st.session_state.get("my_guilds", [])) if st.session_state.get("my_guilds") else "--")
    with m2:
        token_status = "✅ 已配置" if os.environ.get("QQ_AI_CONNECT_TOKEN") else "❌ 未配置"
        st.metric("QQ Token", token_status)
    with m3:
        ai_status = "✅ 已连接" if os.environ.get("OPENAI_API_KEY") else "❌ 未配置"
        st.metric("AI 引擎", ai_status)
    with m4:
        st.metric("当前选中频道", g_id if g_id else "未选择")
        
    st.divider()
    
    if g_id:
        st.subheader("当前频道资料概览")
        with st.spinner("正在加载频道信息..."):
            res = run_tool("scripts/manage/read/get_guild_info.py", {"guild_id": g_id})
            if res.get("code") == 0 or res.get("success") is True:
                data = res.get("data", {})
                info_list = data.get("guildInfos", data.get("guild_infos", []))
                if not info_list and "guildInfo" in data:
                    # fallback to some other possible structure
                    info_list = [data]
                    
                if info_list:
                    info = info_list[0].get("guildInfo", info_list[0].get("guild_info", info_list[0]))
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        if info.get("avatarUrl"):
                            st.image(info.get("avatarUrl"), width=120)
                    with col2:
                        st.markdown(f"### {info.get('guildName', '未知名称')}")
                        st.markdown(f"**简介**: {info.get('profile', '无简介')}")
                        st.markdown(f"**成员数**: {info.get('memberNum', 0)}")
                        st.markdown(f"**创建时间**: {info.get('createTime_human', '未知')}")
                        if data.get("share_url"):
                            st.markdown(f"🔗 **分享链接**: [{data.get('share_url')}]({data.get('share_url')})")
            else:
                st.error("获取频道资料失败，请检查该频道 ID。")
    
    st.divider()
    st.subheader("💡 快速上手指南")
    st.markdown("""
    1. **第一步**：在左侧栏上方选择你需要管理的 **目标频道**。
    2. **第二步**：前往左侧 **📰 帖子与互动** 浏览或发布帖子。
    3. **第三步**：利用 **🧠 AI 数据与发帖** 模块对近期内容进行智能分析。
    """)

elif page == "📰 帖子与互动":
    st.title("📰 帖子管理与社区互动")
    
    if not g_id:
        st.warning("👈 请先在左侧选择一个频道！")
        st.stop()
        
    # Top Action Bar
    with st.container(border=True):
        st.markdown(f"**📍 当前频道 ID**: `{g_id}`")
        
        col1, col2, col3 = st.columns([1.5, 2.5, 1.5])
        with col1:
            if st.button("🔄 加载最新帖子", use_container_width=True, type="primary"):
                st.session_state.feed_action = "load"
        with col2:
            kw = st.text_input("搜索", label_visibility="collapsed", placeholder="输入关键词...")
            if st.button("🔍 搜索本频道帖子", use_container_width=True):
                if kw:
                    st.session_state.feed_action = "search"
                    st.session_state.search_kw = kw
                else:
                    st.warning("请填写搜索关键词")
        with col3:
            if st.button("✍️ 快速发布新帖", use_container_width=True):
                publish_post_dialog(g_id)

    st.divider()
    
    # Load Feeds
    feeds = []
    if st.session_state.get("feed_action") == "load":
        with st.spinner("正在获取帖子列表..."):
            res = run_tool("scripts/feed/read/get_guild_feeds.py", {"guild_id": g_id})
            # Some scripts return code:0, others return success:true
            if res.get("code") == 0 or res.get("success") is True:
                data = res.get("data", {})
                feeds = data.get("feeds", data.get("vecFeed", []))
                st.session_state.current_feeds = feeds
            else:
                st.error("获取失败: " + str(res.get("msg", res)))
    elif st.session_state.get("feed_action") == "search":
        with st.spinner("正在搜索..."):
            res = run_tool("scripts/feed/read/search_guild_feeds.py", {"guild_id": g_id, "keyword": st.session_state.search_kw})
            if res.get("code") == 0 or res.get("success") is True:
                data = res.get("data", {})
                feeds = data.get("feeds", data.get("vecFeed", []))
                st.session_state.current_feeds = feeds
            else:
                st.error("搜索失败: " + str(res.get("msg", res)))
    else:
        # Load from session state if available
        feeds = st.session_state.get("current_feeds", [])
    
    # Render Feeds Card Style
    if feeds:
        st.markdown(f"### 🗂️ 结果列表 (共 {len(feeds)} 条)")
        for f in feeds:
            # new struct has flat fields, old struct has feed_info
            feed_info = f.get("feed_info", f.get("feedInfo", f))
            feed_id = feed_info.get("feed_id", feed_info.get("feedId", ""))
            title = feed_info.get("title", f.get("title", "无标题"))
            
            # Use content_snippet or fallback to content
            content = f.get("content_snippet", feed_info.get("content", "无内容"))
            
            with st.container(border=True):
                st.markdown(f"#### {title}")
                st.write(content[:250] + ("..." if len(content)>250 else ""))
                st.write("---")
                
                c_act1, c_act2, c_act3, _ = st.columns([1, 1, 1, 3])
                with c_act1:
                    if st.button("👍 点赞", key=f"like_{feed_id}", use_container_width=True):
                        res = run_tool("scripts/feed/write/do_feed_prefer.py", {"guild_id": g_id, "feed_id": feed_id, "like": True})
                        if res.get("code") == 0: st.toast("✅ 点赞成功！")
                        else: st.toast("❌ 点赞失败！")
                with c_act2:
                    if st.button("💬 评论/AI评论", key=f"cmt_{feed_id}", use_container_width=True):
                        comment_dialog(g_id, feed_id, content)
                with c_act3:
                    if st.button("👁️ 详情与回复", key=f"det_{feed_id}", use_container_width=True):
                        post_details_dialog(g_id, feed_id, title, content)
    elif st.session_state.get("feed_action"):
        st.info("👻 暂无数据或没有找到相关帖子。")

elif page == "👥 频道与成员":
    st.title("👥 频道与成员管理")
    
    if not g_id:
        st.warning("👈 请先在左侧选择一个频道！")
        # stop rendering rest of the page, but allow creating guild below
    else:
        tab1, tab2 = st.tabs(["🏛️ 频道操作", "🧑‍🤝‍🧑 成员列表与管理"])
        
        with tab1:
            with st.container(border=True):
                col_m1, col_m2 = st.columns([3, 1])
                with col_m1:
                    keyword = st.text_input("搜索成员昵称", placeholder="留空则获取全部")
                with col_m2:
                    st.write("")
                    st.write("")
                    if st.button("获取/搜索成员", use_container_width=True, type="primary"):
                        if keyword:
                            res = run_tool("scripts/manage/read/guild_member_search.py", {"guild_id": g_id, "keyword": keyword})
                        else:
                            res = run_tool("scripts/manage/read/get_guild_member_list.py", {"guild_id": g_id})
                        
                        if res.get("code") == 0 or res.get("success") is True:
                            st.session_state.current_members = res.get("data", {})
                        else:
                            st.error("获取失败: " + str(res.get("msg", res)))
                
                members_data = st.session_state.get("current_members", {})
                if members_data:
                    # support new structure: owners, admins, members, robots
                    all_members = []
                    for group in ["owners", "admins", "members", "robots"]:
                        all_members.extend(members_data.get(group, []))
                    
                    # fallback for old structure
                    if not all_members:
                        all_members = members_data.get("members", members_data.get("vecMember", []))
                        
                    if not all_members:
                        st.info("未找到成员。")
                    else:
                        st.write(f"找到 {len(all_members)} 名成员：")
                        for m in all_members:
                            # try parse new structure first, then fallback to old
                            nick = m.get("昵称", m.get("member_info", {}).get("nick_name", "未知"))
                            tiny_id = m.get("tinyid", m.get("member_info", {}).get("member_tinyid", ""))
                            join_time = m.get("加入时间", m.get("member_info", {}).get("join_time_human", "未知"))
                            
                            with st.expander(f"👤 {nick} (TinyID: {tiny_id})"):
                                st.write(f"加入时间: {join_time}")
                                col_a1, col_a2 = st.columns(2)
                                with col_a1:
                                    shutup_time = st.number_input("禁言时间(秒，0为解除)", min_value=0, value=60, key=f"shutup_{tiny_id}")
                                    if st.button("禁言/解禁", key=f"btn_shutup_{tiny_id}"):
                                        res = run_tool("scripts/manage/write/modify_member_shut_up.py", {"guild_id": g_id, "member_tinyid": tiny_id, "shutup_time": shutup_time})
                                        st.json(res)
                                with col_a2:
                                    st.write("")
                                    st.write("")
                                    if st.button("踢出频道", key=f"btn_kick_{tiny_id}"):
                                        res = run_tool("scripts/manage/write/kick_guild_member.py", {"guild_id": g_id, "member_tinyid": tiny_id})
                                        st.json(res)

    st.divider()
    st.subheader("🌟 创建新频道 (无需依赖当前选择)")
    with st.container(border=True):
        create_name = st.text_input("新频道名称")
        create_profile = st.text_area("新频道简介")
        is_public = st.checkbox("公开频道", value=True)
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("预览创建效果"):
                res = run_tool("scripts/manage/read/preview_theme_private_guild.py", {"guild_name": create_name, "profile": create_profile, "is_public": is_public})
                st.json(res)
        with col_c2:
            if st.button("实际创建该频道", type="primary"):
                res = run_tool("scripts/manage/write/create_theme_private_guild.py", {"guild_name": create_name, "profile": create_profile, "is_public": is_public})
                st.json(res)

elif page == "🧠 AI 数据与发帖":
    st.title("🧠 AI 深度分析与自动化发帖")
    
    if not g_id:
        st.warning("👈 请先在左侧选择一个频道！")
        st.stop()
        
    st.markdown("通过选取近期帖子进行内容聚合分析，并将总结结果一键发帖到频道。")
    
    with st.container(border=True):
        st.subheader("1. 获取待分析数据")
        tab1, tab2 = st.tabs(["🕒 按时间段拉取", "🗂️ 手动选择帖子"])
        
        analysis_source_text = ""
        
        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                days = st.number_input("拉取过去几天的帖子?", min_value=1, max_value=30, value=7)
            with col2:
                st.write("")
                st.write("")
                if st.button("拉取帖子内容", use_container_width=True):
                    with st.spinner("正在获取并组装数据..."):
                        res = run_tool("scripts/feed/read/get_guild_feeds.py", {"guild_id": g_id})
                        if res.get("code") == 0:
                            feeds = res.get("data", {}).get("feeds", res.get("data", {}).get("vecFeed", []))
                            
                            # Filter by time (approximated by simple count for now since get_guild_feeds might not support strict time bounds easily)
                            # In a real scenario we'd check createTime
                            assembled_text = ""
                            for f in feeds[:20]: # limit to 20 for prompt size
                                info = f.get("feed_info", f.get("feedInfo", {}))
                                assembled_text += f"标题: {info.get('title', '')}\n内容: {info.get('content', '')}\n---\n"
                                
                            st.session_state.ai_source_data = assembled_text
                            st.success(f"成功提取了 {len(feeds[:20])} 条近期帖子作为分析素材！")
                        else:
                            st.error("获取失败: " + str(res.get("msg")))
                            
        with tab2:
            st.write("请先在 **📰 帖子与互动** 页面加载帖子列表，然后在这里勾选：")
            current_feeds = st.session_state.get("current_feeds", [])
            if not current_feeds:
                st.info("暂无加载的帖子，请先去帖子管理页拉取。")
            else:
                selected_contents = []
                for f in current_feeds:
                    info = f.get("feed_info", f.get("feedInfo", {}))
                    fid = info.get("feed_id", info.get("feedId", ""))
                    title = info.get("title", "无标题")
                    content = info.get("content", "无内容")
                    if st.checkbox(f"**{title}** - {content[:50]}...", key=f"sel_{fid}"):
                        selected_contents.append(f"标题: {title}\n内容: {content}")
                        
                if st.button("将选中的帖子作为分析素材"):
                    st.session_state.ai_source_data = "\n---\n".join(selected_contents)
                    st.success(f"已选中 {len(selected_contents)} 条帖子！")
                    
    # Display Source Data Text Area
    source_data = st.text_area("数据源预览 (可手动修改)", value=st.session_state.get("ai_source_data", ""), height=150)
    
    if source_data:
        with st.container(border=True):
            st.subheader("2. AI 总结与分析")
            analysis_prompt = st.text_input("分析指令", value="请总结出上述帖子中的主要话题、用户活跃度及情感倾向，用条理清晰的方式输出，适合作为社区周报发布。")
            
            if st.button("🚀 开始 AI 分析", type="primary"):
                with st.spinner("AI 正在深度思考..."):
                    res = ai_helper.analyze_data(source_data, analysis_prompt)
                    st.session_state.ai_analysis_result = res
                    
        # Display Result and Post Button
        if st.session_state.get("ai_analysis_result"):
            with st.container(border=True):
                st.subheader("3. 📊 分析报告与发帖")
                result_text = st.text_area("分析结果 (可编辑)", value=st.session_state.ai_analysis_result, height=300)
                
                post_title = st.text_input("帖子标题", value=f"社区内容总结报告 - {datetime.now().strftime('%Y-%m-%d')}")
                
                if st.button("📢 一键发布此报告到当前频道", use_container_width=True, type="primary"):
                    with st.spinner("获取板块并发布..."):
                        # Here we can also dynamically ask or just pick the first available for simplicity in auto-post
                        channels = get_channel_list(g_id)
                        channel_id = ""
                        if channels:
                            # Try to find a channel named "帖子" or "讨论"
                            for c in channels:
                                if "帖子" in c["name"] or "讨论" in c["name"] or "广场" in c["name"]:
                                    channel_id = c["id"]
                                    break
                            if not channel_id:
                                channel_id = channels[0]["id"]
                                
                        if not channel_id:
                            st.error("未能找到支持发帖的板块，请检查频道配置。")
                        else:
                            res = run_tool("scripts/feed/write/publish_feed.py", {"guild_id": g_id, "channel_id": channel_id, "title": post_title, "content": result_text})
                            if res.get("code") == 0 or res.get("success") is True:
                                st.success("✅ 报告发布成功！")
                            else:
                                st.error(f"❌ 发布失败: {res.get('msg', res)}")

elif page == "🔔 自动化任务":
    st.title("🔔 自动化任务引擎")
    
    if not g_id:
        st.warning("👈 请先在左侧选择一个频道！")
        st.stop()
        
    with st.container(border=True):
        st.subheader("➕ 添加新任务到当前频道")
        task_type = st.selectbox("任务类型", ["内容巡检扫描 (自动清理违规词)", "问答自动回复 (AI 自动回复提问)"])
        interval_minutes = st.number_input("执行间隔 (分钟)", min_value=1, value=60)
        
        if st.button("添加定时任务", type="primary"):
            from scheduler_app import add_job
            if task_type.startswith("内容巡检扫描"):
                add_job("scripts/feed/operation/auto_clean_channel_feeds.py", {"guild_id": g_id}, interval_minutes)
                st.success("已添加巡检任务！")
            elif task_type.startswith("问答自动回复"):
                add_job("scripts/feed/operation/channel_qa_responder.py", {"guild_id": g_id}, interval_minutes)
                st.success("已添加问答回复任务！")
            st.rerun()
            
    with st.container(border=True):
        st.subheader("⚙️ 运行中的定时任务列表")
        from scheduler_app import get_jobs, remove_job, start_scheduler
        start_scheduler()
        jobs = get_jobs()
        if jobs:
            for j in jobs:
                col1, col2 = st.columns([4, 1])
                col1.info(f"**任务ID**: {j.id}  \n**下次执行时间**: {j.next_run_time}")
                if col2.button("🗑️ 移除", key=f"del_{j.id}", use_container_width=True):
                    remove_job(j.id)
                    st.rerun()
        else:
            st.warning("暂无运行中的任务。")
