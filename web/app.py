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
CACHE_FILE = BASE_DIR / "guilds_cache.json"

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
def parse_to_timestamp(time_str_or_int):
    """尝试将可能的时间字符串（2026-04-02 14:15:48）或数字转换为纯数字时间戳字符串"""
    if not time_str_or_int:
        return "0"
    if isinstance(time_str_or_int, int) or (isinstance(time_str_or_int, str) and time_str_or_int.isdigit()):
        return str(time_str_or_int)
    try:
        dt = datetime.strptime(str(time_str_or_int), "%Y-%m-%d %H:%M:%S")
        return str(int(dt.timestamp()))
    except:
        return "0"

def get_channel_list(guild_id):
    """获取指定频道下的所有子版块列表，返回格式 [{"id": "xxx", "name": "xxx"}]"""
    res = run_tool("scripts/manage/read/get_guild_channel_list.py", {"guild_id": guild_id})
    channels_options = []
    if res.get("code") == 0 or res.get("success") is True:
        data = res.get("data", {})
        
        # New structure: data.guildInfoList[0].channelList
        guild_info_list = data.get("guildInfoList", [])
        if guild_info_list and isinstance(guild_info_list, list):
            channels = guild_info_list[0].get("channelList", [])
            for c in channels:
                c_name = c.get("channelName", c.get("channel_name", "未命名版块"))
                c_id = c.get("channelId", c.get("channel_id", ""))
                if c_id:
                    channels_options.append({"id": str(c_id), "name": f"{c_name} (ID:{c_id})"})
            return channels_options
            
        # Old/fallback structure: data.channels or data.vecChannel
        channels = data.get("channels", data.get("vecChannel", []))
        for c in channels:
            c_info = c.get("channelInfo", c.get("channel_info", c))
            c_name = c_info.get("channelName", c_info.get("channel_name", "未命名版块"))
            c_id = c_info.get("channelId", c_info.get("channel_id", ""))
            if c_id:
                channels_options.append({"id": str(c_id), "name": f"{c_name} (ID:{c_id})"})
    return channels_options

def load_my_guilds(force_refresh=False):
    if not force_refresh and "my_guilds" in st.session_state and st.session_state.my_guilds:
        return st.session_state.my_guilds
        
    # Try load from cache file first
    if not force_refresh and CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                if cache_data.get("token") == os.environ.get("QQ_AI_CONNECT_TOKEN"):
                    st.session_state.my_guilds = cache_data.get("guilds", [])
                    return st.session_state.my_guilds
        except Exception:
            pass

    try:
        res = run_tool("scripts/manage/read/get_my_join_guild_info.py", {})
        if isinstance(res, dict) and (res.get("code") == 0 or res.get("success") is True):
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
            
            # Save to cache file
            try:
                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump({
                        "token": os.environ.get("QQ_AI_CONNECT_TOKEN"),
                        "guilds": options
                    }, f, ensure_ascii=False)
            except Exception as e:
                print(f"Failed to write cache: {e}")
                
            return options
    except Exception as e:
        print(f"Failed to load guilds: {e}")
        pass
        
    return st.session_state.get("my_guilds", [])

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
            if not os.environ.get("OPENAI_API_KEY"):
                st.error("⚠️ 尚未配置 OpenAI 密钥，请先在左侧菜单底部点击 [⚙️ 环境与系统配置] 填写！")
            else:
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
            if not os.environ.get("OPENAI_API_KEY"):
                st.error("⚠️ 尚未配置 OpenAI 密钥，请先在左侧菜单底部点击 [⚙️ 环境与系统配置] 填写！")
            else:
                with st.spinner("AI 正在提炼核心内容并发布..."):
                    generated = ai_helper.analyze_data(source_data, "请总结以上内容，提取核心信息，并写成一篇适合在社区分享的帖子，条理清晰。")
                    st.text_area("生成的总结 (预览)", value=generated, height=200, disabled=True)
                    res = run_tool("scripts/feed/write/publish_feed.py", {"guild_id": guild_id, "channel_id": selected_channel_id, "title": "今日资讯总结", "content": generated})
                    if res.get("code") == 0 or res.get("success") is True: 
                        st.success("发布成功！")
                    else: 
                        st.error(f"发布失败: {res.get('msg', res)}")

@st.dialog("💬 发表评论", width="large")
def comment_dialog(guild_id, feed_id, create_time, post_content):
    st.markdown("### 原帖内容")
    st.info(post_content[:300] + ("..." if len(post_content)>300 else ""))
    
    tab1, tab2 = st.tabs(["✍️ 直接评论", "🤖 AI 辅助评论"])
    with tab1:
        cmt_content = st.text_area("输入你的评论...", key=f"cmt_input_{feed_id}", height=150)
        if st.button("发送评论", use_container_width=True, type="primary"):
            ts = parse_to_timestamp(create_time)
            res = run_tool("scripts/feed/write/do_comment.py", {
                "guild_id": guild_id, 
                "feed_id": feed_id, 
                "feed_create_time": ts, 
                "comment_type": 1,
                "content": cmt_content
            })
            if res.get("code") == 0 or res.get("success") is True: 
                st.success("评论成功！")
            else: 
                st.error(f"评论失败: {res.get('msg', res)}")
                
    with tab2:
        col1, col2 = st.columns([1, 2])
        with col1:
            style = st.selectbox("选择 AI 评论风格", ["友好赞同", "幽默风趣", "专业分析", "委婉反驳"])
        with col2:
            st.write("")
            st.write("")
            if st.button("✨ 生成并发送", use_container_width=True, type="primary"):
                if not os.environ.get("OPENAI_API_KEY"):
                    st.error("⚠️ 尚未配置 OpenAI 密钥，请先在左侧菜单底部点击 [⚙️ 环境与系统配置] 填写！")
                else:
                    with st.spinner("生成中..."):
                        generated = ai_helper.generate_comment(post_content, style)
                        st.success(f"**已发送:**\n{generated}")
                        ts = parse_to_timestamp(create_time)
                        res = run_tool("scripts/feed/write/do_comment.py", {
                            "guild_id": guild_id, 
                            "feed_id": feed_id, 
                            "feed_create_time": ts, 
                            "comment_type": 1,
                            "content": generated
                        })
                        if res.get("code") == 0 or res.get("success") is True: 
                            st.success("评论成功！")
                        else:
                            st.error(f"发送失败: {res.get('msg', res)}")

@st.dialog("↩️ 回复评论", width="large")
def reply_dialog(guild_id, feed_id, create_time, comment_id, comment_content):
    st.markdown("### 回复目标")
    st.info(comment_content)
    
    tab1, tab2 = st.tabs(["✍️ 直接回复", "🤖 AI 辅助回复"])
    with tab1:
        reply_text = st.text_area("输入回复内容...", key=f"rep_input_{comment_id}", height=120)
        if st.button("发送回复", use_container_width=True, type="primary"):
            ts = parse_to_timestamp(create_time)
            res = run_tool("scripts/feed/write/do_reply.py", {
                "guild_id": guild_id, 
                "feed_id": feed_id, 
                "feed_create_time": ts, 
                "comment_id": comment_id, 
                "reply_type": 1,
                "content": reply_text
            })
            if res.get("code") == 0 or res.get("success") is True: 
                st.success("回复成功！")
            else: 
                st.error(f"回复失败: {res.get('msg', res)}")
                
    with tab2:
        style = st.selectbox("选择 AI 回复风格", ["友好", "幽默", "专业补充", "委婉反驳"], key=f"rep_style_{comment_id}")
        if st.button("✨ 生成并发送", key=f"rep_ai_{comment_id}", use_container_width=True, type="primary"):
            if not os.environ.get("OPENAI_API_KEY"):
                st.error("⚠️ 尚未配置 OpenAI 密钥，请先在左侧菜单底部点击 [⚙️ 环境与系统配置] 填写！")
            else:
                with st.spinner("AI 生成中..."):
                    generated = ai_helper.generate_comment(comment_content, style)
                    st.success(f"**已发送:**\n{generated}")
                    ts = parse_to_timestamp(create_time)
                    res = run_tool("scripts/feed/write/do_reply.py", {
                        "guild_id": guild_id, 
                        "feed_id": feed_id, 
                        "feed_create_time": ts, 
                        "comment_id": comment_id, 
                        "reply_type": 1,
                        "content": generated
                    })
                    if res.get("code") == 0 or res.get("success") is True: 
                        st.success("回复成功！")
                    else: 
                        st.error(f"回复失败: {res.get('msg', res)}")

@st.dialog("👁️ 帖子详情与评论", width="large")
def post_details_dialog(guild_id, feed_id, create_time, title, content):
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
                        reply_dialog(guild_id, feed_id, create_time, cmt_id, cmt_content)
    else:
        st.error("获取评论失败: " + str(res.get("msg", res)))

# ---- Sidebar & Navigation ----
with st.sidebar:
    st.title("🚀 频道控制台")
    st.markdown("高效、智能的腾讯频道社区管理端")
    
    # Global Guild Selector
    st.subheader("📌 目标频道选择")
    
    # Check if we should load guilds
    if st.button("🔄 强制从云端刷新频道列表", use_container_width=True):
        st.session_state.my_guilds = []
        load_my_guilds(force_refresh=True)
        st.rerun()

    # Automatically try loading from cache
    load_my_guilds()
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
        "🌟 创建新频道",
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
    1. **第一步**：在左侧栏上方选择你需要管理的 **目标频道**，或者通过 **🌟 创建新频道** 新建一个。
    2. **第二步**：前往左侧 **📰 帖子与互动** 浏览或发布帖子。
    3. **第三步**：利用 **🧠 AI 数据与发帖** 模块对近期内容进行智能分析。
    """)

elif page == "🌟 创建新频道":
    st.title("🌟 创建新频道")
    st.markdown("无需依赖左侧选中的目标频道，您可以直接在此处创建一个全新的频道。")
    
    with st.container(border=True):
        create_name = st.text_input("新频道名称 (必填)")
        create_profile = st.text_area("新频道简介 (必填)")
        theme = st.text_input("频道主题 (theme) (若提供，名称和简介可由 AI 自动润色补充)")
        is_public = st.selectbox("频道公开度", ["public", "private"], index=0)
        
        st.markdown("**🖼️ 频道头像 (必传)**")
        uploaded_file = st.file_uploader("选择一张图片作为频道头像 (JPG/PNG)", type=["jpg", "jpeg", "png"])
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("预览创建参数", use_container_width=True):
                if not uploaded_file:
                    st.warning("请先上传频道头像图片。")
                else:
                    # Save to temp
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    res = run_tool("scripts/manage/read/preview_theme_private_guild.py", {
                        "guild_name": create_name, 
                        "guild_profile": create_profile, 
                        "theme": theme,
                        "community_type": is_public,
                        "image_path": tmp_path
                    })
                    st.json(res)
                    os.remove(tmp_path)
                    
        with col_c2:
            if st.button("🚀 立即创建该频道", type="primary", use_container_width=True):
                if not uploaded_file:
                    st.warning("请先上传频道头像图片。")
                else:
                    # Save to temp
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    with st.spinner("正在向 QQ 频道提交创建请求..."):
                        res = run_tool("scripts/manage/write/create_theme_private_guild.py", {
                            "guild_name": create_name, 
                            "guild_profile": create_profile, 
                            "theme": theme,
                            "community_type": is_public,
                            "image_path": tmp_path
                        })
                        if res.get("code") == 0 or res.get("success") is True:
                            st.success("频道创建成功！")
                        else:
                            st.error(f"创建失败: {res.get('msg', res)}")
                        st.json(res)
                    
                    os.remove(tmp_path)
                
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
            create_time = feed_info.get("create_time", feed_info.get("createTime", f.get("create_time", f.get("createTime", 0))))
            
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
                        comment_dialog(g_id, feed_id, create_time, content)
                with c_act3:
                    if st.button("👁️ 详情与回复", key=f"det_{feed_id}", use_container_width=True):
                        post_details_dialog(g_id, feed_id, create_time, title, content)
    elif st.session_state.get("feed_action"):
        st.info("👻 暂无数据或没有找到相关帖子。")

elif page == "👥 频道与成员":
    st.title("👥 频道与成员管理")
    
    if not g_id:
        st.warning("👈 请先在左侧选择一个频道！")
        # stop rendering rest of the page
        st.stop()
    
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

elif page == "🧠 AI 数据与发帖":
    st.title("🧠 AI 深度分析与自动化发帖")
    
    if not g_id:
        st.warning("👈 请先在左侧选择一个频道！")
        st.stop()
        
    st.markdown("在这里，你可以拉取近期的帖子，自由勾选你想分析的内容，交给 AI 进行总结，并一键发帖回社区。")
    
    with st.container(border=True):
        st.subheader("1. 独立拉取并勾选帖子")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            fetch_limit = st.number_input("一次性拉取最新多少条帖子？", min_value=5, max_value=50, value=20)
        with col2:
            st.write("")
            st.write("")
            if st.button("📥 拉取最新帖子", use_container_width=True, type="primary"):
                with st.spinner("正在直接从接口拉取数据..."):
                    res = run_tool("scripts/feed/read/get_guild_feeds.py", {"guild_id": g_id})
                    if res.get("code") == 0 or res.get("success") is True:
                        data = res.get("data", {})
                        feeds = data.get("feeds", data.get("vecFeed", []))
                        st.session_state.ai_analysis_feeds = feeds[:fetch_limit]
                        st.success(f"✅ 成功拉取 {len(st.session_state.ai_analysis_feeds)} 条帖子！")
                    else:
                        st.error("获取失败: " + str(res.get("msg", res)))
                        
        # Display list of feeds for selection
        available_feeds = st.session_state.get("ai_analysis_feeds", [])
        if available_feeds:
            st.markdown("---")
            st.markdown("**请勾选你想放入 AI 分析素材库的帖子：**")
            
            selected_contents = []
            for idx, f in enumerate(available_feeds):
                info = f.get("feed_info", f.get("feedInfo", f))
                fid = info.get("feed_id", info.get("feedId", f"unknown_{idx}"))
                title = info.get("title", f.get("title", "无标题"))
                content = f.get("content_snippet", info.get("content", "无内容"))
                
                # Checkbox for each feed
                if st.checkbox(f"📄 **{title}** - {content[:80]}...", key=f"ai_sel_{fid}_{idx}", value=True):
                    selected_contents.append(f"标题: {title}\n内容: {content}")
                    
            if st.button("➕ 确认选中并生成分析素材", use_container_width=True):
                st.session_state.ai_source_data = "\n---\n".join(selected_contents)
                st.success(f"已成功将 {len(selected_contents)} 条帖子合并为分析素材！请在下方查看或修改。")
        else:
            st.info("👆 请先点击上方按钮拉取帖子列表。")
                    
    # Display Source Data Text Area
    source_data = st.text_area("数据源预览 (你可以手动修改、补充或粘贴其他内容)", value=st.session_state.get("ai_source_data", ""), height=200)
    
    if source_data:
        with st.container(border=True):
            st.subheader("2. AI 总结与分析")
            analysis_prompt = st.text_input("分析指令", value="请总结出上述帖子中的主要话题、用户活跃度及情感倾向，用条理清晰的方式输出，适合作为社区周报发布。")
            
            if st.button("🚀 开始 AI 分析", type="primary"):
                if not os.environ.get("OPENAI_API_KEY"):
                    st.error("⚠️ 尚未配置 OpenAI 密钥，请先在左侧菜单底部点击 [⚙️ 环境与系统配置] 填写！")
                else:
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
        task_type = st.selectbox("任务类型", [
            "内容巡检扫描 (拉取内容供外部AI审查违规词)", 
            "问答自动回复 (自动提取关键词检索频道并回复)",
            "自动点赞 (给频道内最新拉取到的帖子点赞)"
        ])
        interval_minutes = st.number_input("执行间隔 (分钟)", min_value=1, value=60)
        
        # 额外参数
        extra_params = {}
        if "问答自动回复" in task_type:
            st.info("ℹ️ 问答自动回复逻辑：每隔设定时间拉取最新帖子，如果帖子中包含如“怎么”、“如何”、“求助”、“不知道”等疑问词汇，则会提取关键词并在频道内搜索相关旧帖，如果搜到，会把旧帖子的摘要整理成答案自动在帖子下回复。")
        elif "内容巡检扫描" in task_type:
            st.info("ℹ️ 内容巡检逻辑：每隔设定时间拉取最新帖子，若发现包含设定违禁词的帖子，则会自动调用底层接口将其删除。")
            scan_interval = st.number_input("扫描过去多少分钟的帖子？", value=60)
            banned_words_input = st.text_input("设置违禁词（多个词用逗号分隔，留空则仅拉取不删帖）", placeholder="例如: 加微,兼职,代刷")
            extra_params["scan_interval"] = scan_interval
            if banned_words_input.strip():
                extra_params["banned_words"] = [w.strip() for w in banned_words_input.split(",") if w.strip()]
        elif "自动点赞" in task_type:
            st.info("ℹ️ 自动点赞逻辑：每隔设定时间拉取频道最新帖子（单次约 20 条），并为它们逐一点赞，适合保持社区活跃度。")
        
        if st.button("添加定时任务", type="primary"):
            from scheduler_app import add_job
            if "内容巡检扫描" in task_type:
                add_job("scripts/feed/operation/auto_clean_channel_feeds.py", {"guild_id": g_id, **extra_params}, interval_minutes)
                st.success("已添加巡检任务！")
            elif "问答自动回复" in task_type:
                add_job("scripts/feed/operation/channel_qa_responder.py", {"guild_id": g_id, **extra_params}, interval_minutes)
                st.success("已添加问答回复任务！")
            elif "自动点赞" in task_type:
                add_job("scripts/feed/operation/auto_like_feeds.py", {"guild_id": g_id}, interval_minutes)
                st.success("已添加自动点赞任务！")
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
