import streamlit as st
import os
import json
from tool_runner import run_tool
import ai_helper
from dotenv import load_dotenv

load_dotenv()

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
    if st.button("💾 保存配置", use_container_width=True, type="primary"):
        with open(".env", "w") as f:
            f.write(f'QQ_AI_CONNECT_TOKEN="{token}"\n')
            f.write(f'OPENAI_API_KEY="{openai_key}"\n')
            f.write(f'OPENAI_BASE_URL="{openai_url}"\n')
            f.write(f'OPENAI_MODEL="{openai_model}"\n')
        os.environ["QQ_AI_CONNECT_TOKEN"] = token
        os.environ["OPENAI_API_KEY"] = openai_key
        os.environ["OPENAI_BASE_URL"] = openai_url
        os.environ["OPENAI_MODEL"] = openai_model
        st.success("✅ 配置已保存并生效！")
        st.rerun()

@st.dialog("📝 发布新帖子", width="large")
def publish_post_dialog(guild_id):
    st.write(f"当前操作频道 ID: `{guild_id}`")
    tab1, tab2, tab3 = st.tabs(["✍️ 直接发布", "🤖 AI 创作", "📑 AI 总结发帖"])
    
    with tab1:
        title = st.text_input("帖子标题", key="pub_title")
        content = st.text_area("帖子正文", key="pub_content", height=200)
        if st.button("🚀 立即发布", use_container_width=True, type="primary"):
            res = run_tool("scripts/feed/write/publish_feed.py", {"guild_id": guild_id, "title": title, "content": content})
            if res.get("code") == 0: 
                st.success("发布成功！")
            else: 
                st.error(f"发布失败: {res.get('msg')}")
                
    with tab2:
        topic = st.text_input("发帖主题")
        reqs = st.text_area("附加要求 (例如：语气幽默，不少于300字)", height=80)
        if st.button("✨ AI 生成并发布", use_container_width=True, type="primary"):
            with st.spinner("AI 正在头脑风暴..."):
                generated = ai_helper.generate_post(topic, reqs)
                st.text_area("生成的正文 (预览)", value=generated, height=200, disabled=True)
                res = run_tool("scripts/feed/write/publish_feed.py", {"guild_id": guild_id, "title": topic, "content": generated})
                if res.get("code") == 0: 
                    st.success("发布成功！")
                else: 
                    st.error(f"发布失败: {res.get('msg')}")
                    
    with tab3:
        source_data = st.text_area("输入需要总结的数据源 (例如长文章、群聊记录、新闻等)", height=150)
        if st.button("📝 总结并发布", use_container_width=True, type="primary"):
            with st.spinner("AI 正在提炼核心内容..."):
                generated = ai_helper.analyze_data(source_data, "请总结以上内容，提取核心信息，并写成一篇适合在社区分享的帖子，条理清晰。")
                st.text_area("生成的总结 (预览)", value=generated, height=200, disabled=True)
                res = run_tool("scripts/feed/write/publish_feed.py", {"guild_id": guild_id, "title": "今日资讯总结", "content": generated})
                if res.get("code") == 0: 
                    st.success("发布成功！")
                else: 
                    st.error(f"发布失败: {res.get('msg')}")

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
        
    if res.get("code") != 0:
        st.error("获取评论失败: " + str(res.get("msg")))
        return
        
    data = res.get("data", {})
    comments = data.get("comments", data.get("vecComment", []))
    
    if not comments:
        st.info("暂无评论，快来抢沙发吧！")
    else:
        for cmt in comments:
            cmt_id = cmt.get("comment_id", cmt.get("commentId", ""))
            cmt_content = cmt.get("content", "无内容")
            author = cmt.get("poster_info", {}).get("nick_name", "匿名")
            
            with st.container(border=True):
                st.markdown(f"**👤 {author}**:  \n{cmt_content}")
                if st.button("↩️ 回复此评论", key=f"btn_rep_{cmt_id}"):
                    reply_dialog(guild_id, feed_id, cmt_id, cmt_content)

# ---- Sidebar & Navigation ----
with st.sidebar:
    st.title("🚀 频道控制台")
    st.markdown("高效、智能的腾讯频道社区管理端")
    st.divider()
    
    page = st.radio("导航菜单", [
        "📊 数据仪表盘", 
        "📰 帖子与互动", 
        "👥 频道与成员", 
        "🔔 自动化与任务"
    ], label_visibility="collapsed")

    st.divider()
    if st.button("⚙️ 环境与系统配置", use_container_width=True):
        config_dialog()

# ---- Main Pages ----
if page == "📊 数据仪表盘":
    st.title("📊 数据仪表盘 Dashboard")
    st.markdown("欢迎使用腾讯频道社区控制台，为您提供直观的数据与快捷操作！")
    
    col1, col2 = st.columns([8, 2])
    with col2:
        if st.button("🔄 刷新数据", use_container_width=True):
            res = run_tool("scripts/manage/read/get_my_join_guild_info.py", {})
            if res.get("code") == 0:
                guilds = res.get("data", {}).get("guilds", res.get("data", {}).get("guildInfos", []))
                st.session_state.guild_count = len(guilds)
            else:
                st.error("获取数据失败，请检查 Token 配置。")
                
    st.divider()
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("已加入频道数", st.session_state.get("guild_count", "--"))
    with m2:
        token_status = "✅ 已配置" if os.environ.get("QQ_AI_CONNECT_TOKEN") else "❌ 未配置"
        st.metric("QQ Token", token_status)
    with m3:
        ai_status = "✅ 已连接" if os.environ.get("OPENAI_API_KEY") else "❌ 未配置"
        st.metric("AI 引擎", ai_status)
    with m4:
        st.metric("系统服务状态", "🟢 正常")
        
    st.divider()
    st.subheader("💡 快速上手指南")
    st.markdown("""
    1. **第一步**：点击左下角 **⚙️ 环境与系统配置** 填写并保存您的 Token。
    2. **第二步**：在当前页点击 **🔄 刷新数据** 验证是否连接成功。
    3. **第三步**：前往左侧 **📰 帖子与互动** 或其他菜单，开始管理您的社区！
    """)

elif page == "📰 帖子与互动":
    st.title("📰 帖子管理与社区互动")
    
    # Top Action Bar
    with st.container(border=True):
        st.markdown("**🔍 检索与操作**")
        g_id = st.text_input("📍 当前操作的频道 ID (guild_id)", value=st.session_state.get("guild_id", ""))
        st.session_state.guild_id = g_id
        
        col1, col2, col3 = st.columns([1.5, 2.5, 1.5])
        with col1:
            if st.button("🔄 加载最新帖子", use_container_width=True, type="primary"):
                if g_id: st.session_state.feed_action = "load"
                else: st.warning("请先填写频道 ID")
        with col2:
            kw = st.text_input("搜索", label_visibility="collapsed", placeholder="输入关键词...")
            if st.button("🔍 搜索包含此关键词的帖子", use_container_width=True):
                if g_id and kw:
                    st.session_state.feed_action = "search"
                    st.session_state.search_kw = kw
                else:
                    st.warning("请填写频道 ID 和搜索关键词")
        with col3:
            if st.button("✍️ 快速发布新帖", use_container_width=True):
                if not g_id: st.warning("请先填写频道 ID")
                else: publish_post_dialog(g_id)

    st.divider()
    
    # Load Feeds
    feeds = []
    if g_id:
        if st.session_state.get("feed_action") == "load":
            with st.spinner("正在获取帖子列表..."):
                res = run_tool("scripts/feed/read/get_guild_feeds.py", {"guild_id": g_id})
                if res.get("code") == 0:
                    feeds = res.get("data", {}).get("feeds", res.get("data", {}).get("vecFeed", []))
                else:
                    st.error("获取失败: " + str(res.get("msg")))
        elif st.session_state.get("feed_action") == "search":
            with st.spinner("正在搜索..."):
                res = run_tool("scripts/feed/read/search_guild_feeds.py", {"guild_id": g_id, "keyword": st.session_state.search_kw})
                if res.get("code") == 0:
                    feeds = res.get("data", {}).get("feeds", res.get("data", {}).get("vecFeed", []))
                else:
                    st.error("搜索失败: " + str(res.get("msg")))
    
    # Render Feeds Card Style
    if feeds:
        st.markdown(f"### 🗂️ 结果列表 (共 {len(feeds)} 条)")
        for f in feeds:
            feed_info = f.get("feed_info", f.get("feedInfo", f))
            feed_id = feed_info.get("feed_id", feed_info.get("feedId", ""))
            title = feed_info.get("title", "无标题")
            content = feed_info.get("content", "无内容")
            
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
    tab1, tab2 = st.tabs(["🏛️ 频道基础信息", "🧑‍🤝‍🧑 成员列表管理"])
    
    with tab1:
        with st.container(border=True):
            g_id = st.text_input("频道 ID", key="guild_info_id")
            if st.button("查询频道资料", type="primary"):
                res = run_tool("scripts/manage/read/get_guild_info.py", {"guild_id": g_id})
                st.json(res)
            
    with tab2:
        with st.container(border=True):
            g_id_mem = st.text_input("频道 ID", key="guild_mem_id")
            if st.button("获取成员列表", type="primary"):
                res = run_tool("scripts/manage/read/get_guild_member_list.py", {"guild_id": g_id_mem})
                st.json(res)

elif page == "🔔 自动化与任务":
    st.title("🔔 数据分析与自动化任务")
    tab1, tab2 = st.tabs(["🧠 AI 深度分析", "⏱️ 定时任务引擎"])
    
    with tab1:
        with st.container(border=True):
            st.subheader("输入需分析的数据或文本")
            analysis_data = st.text_area("例如：粘贴复制的帖子 JSON 列表、成员讨论记录等", height=200)
            analysis_prompt = st.text_input("分析指令", value="请总结出上述数据中的主要话题、用户活跃度及情感倾向，用条理清晰的方式输出。")
            if st.button("🚀 启动深度分析", type="primary"):
                with st.spinner("AI 正在深度思考..."):
                    res = ai_helper.analyze_data(analysis_data, analysis_prompt)
                    st.success("分析完成！")
                    st.markdown("### 📊 分析报告")
                    st.write(res)
                
    with tab2:
        with st.container(border=True):
            st.subheader("⚙️ 定时任务列表")
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
