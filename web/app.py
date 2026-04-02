import streamlit as st
import os
import json
from tool_runner import run_tool
import ai_helper
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Tencent Channel Community Web", layout="wide")

st.sidebar.title("腾讯频道社区管理")

page = st.sidebar.radio(
    "导航",
    ["主页与Token配置", "频道与成员管理", "内容管理(帖子)", "消息通知与用户操作", "AI分析与生成", "定时任务"]
)

if page == "主页与Token配置":
    st.title("主页与环境配置")
    
    st.subheader("配置 Token")
    token = st.text_input("QQ_AI_CONNECT_TOKEN", type="password", help="请到 https://connect.qq.com/ai 获取")
    if st.button("保存 Token"):
        with open(".env", "a+") as f:
            f.write(f'\nQQ_AI_CONNECT_TOKEN="{token}"\n')
        st.success("Token 已保存至本地 .env 文件！")
        
    st.subheader("配置 OpenAI (可选)")
    openai_key = st.text_input("OPENAI_API_KEY", value=os.environ.get("OPENAI_API_KEY", ""), type="password")
    openai_url = st.text_input("OPENAI_BASE_URL", value=os.environ.get("OPENAI_BASE_URL", ""))
    openai_model = st.text_input("OPENAI_MODEL", value=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"))
    if st.button("保存 OpenAI 配置"):
        with open(".env", "a+") as f:
            f.write(f'\nOPENAI_API_KEY="{openai_key}"\nOPENAI_BASE_URL="{openai_url}"\nOPENAI_MODEL="{openai_model}"\n')
        st.success("OpenAI 配置已保存至本地 .env 文件！")
        # Update current environment
        os.environ["OPENAI_API_KEY"] = openai_key
        os.environ["OPENAI_BASE_URL"] = openai_url
        os.environ["OPENAI_MODEL"] = openai_model

    st.subheader("环境自检")
    if st.button("验证 Token 连通性"):
        res = run_tool("scripts/manage/read/verify_qq_ai_connect_token.py", {})
        if res.get("code") == 0:
            st.success(res.get("msg", "验证成功！"))
            st.json(res.get("data", {}))
        else:
            st.error(res.get("msg", "验证失败！"))
            st.json(res)

elif page == "频道与成员管理":
    st.title("频道与成员管理")
    
    tab1, tab2, tab3, tab4 = st.tabs(["我加入的频道", "频道详情", "频道成员", "操作"])
    
    with tab1:
        if st.button("获取我加入的频道"):
            res = run_tool("scripts/manage/read/get_my_join_guild_info.py", {})
            if res.get("code") == 0:
                st.success("成功")
                st.json(res.get("data", {}))
            else:
                st.error(res.get("msg", "获取失败"))
                
    with tab2:
        col1, col2 = st.columns([1, 1])
        with col1:
            guild_id = st.text_input("频道ID (guild_id)")
        with col2:
            if st.button("查询频道资料", key="get_guild_info"):
                if not guild_id:
                    st.warning("请输入频道ID")
                else:
                    res = run_tool("scripts/manage/read/get_guild_info.py", {"guild_id": guild_id})
                    st.json(res)
            if st.button("获取子频道列表", key="get_channel_list"):
                if not guild_id:
                    st.warning("请输入频道ID")
                else:
                    res = run_tool("scripts/manage/read/get_guild_channel_list.py", {"guild_id": guild_id})
                    st.json(res)
            
    with tab3:
        g_id_member = st.text_input("频道ID", key="g_id_member")
        page_token = st.text_input("分页Token (可选)")
        if st.button("获取成员列表"):
            res = run_tool("scripts/manage/read/get_guild_member_list.py", {"guild_id": g_id_member, "page_token": page_token})
            st.json(res)
            
        keyword = st.text_input("搜索成员昵称")
        if st.button("搜索成员"):
            res = run_tool("scripts/manage/read/guild_member_search.py", {"guild_id": g_id_member, "keyword": keyword})
            st.json(res)
            
    with tab4:
        st.subheader("创建/预览频道")
        create_name = st.text_input("新频道名称")
        create_profile = st.text_area("新频道简介")
        is_public = st.checkbox("公开频道", value=True)
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("预览创建"):
                res = run_tool("scripts/manage/read/preview_theme_private_guild.py", {"guild_name": create_name, "profile": create_profile, "is_public": is_public})
                st.json(res)
        with col_c2:
            if st.button("实际创建"):
                res = run_tool("scripts/manage/write/create_theme_private_guild.py", {"guild_name": create_name, "profile": create_profile, "is_public": is_public})
                st.json(res)

elif page == "内容管理(帖子)":
    st.title("内容管理(帖子)")
    tab1, tab2, tab3 = st.tabs(["浏览与搜索", "帖子详情与评论", "发帖与修改"])
    
    with tab1:
        g_id = st.text_input("频道ID", key="feed_gid")
        channel_id = st.text_input("子频道ID (可选，获取特定板块帖子时需要)", key="feed_cid")
        if st.button("获取频道主页帖子"):
            res = run_tool("scripts/feed/read/get_guild_feeds.py", {"guild_id": g_id})
            st.json(res)
        if st.button("获取指定板块帖子"):
            res = run_tool("scripts/feed/read/get_channel_timeline_feeds.py", {"guild_id": g_id, "channel_id": channel_id})
            st.json(res)
        
        search_kw = st.text_input("搜索关键词")
        if st.button("搜索内容(包含帖子、频道)"):
            res = run_tool("scripts/manage/read/search_guild_content.py", {"keyword": search_kw})
            st.json(res)

    with tab2:
        feed_id = st.text_input("帖子ID (feed_id)")
        if st.button("获取帖子详情"):
            res = run_tool("scripts/feed/read/get_feed_detail.py", {"guild_id": g_id, "feed_id": feed_id})
            st.json(res)
        if st.button("获取帖子评论"):
            res = run_tool("scripts/feed/read/get_feed_comments.py", {"guild_id": g_id, "feed_id": feed_id})
            st.json(res)
            
        comment_content = st.text_area("发表评论内容")
        if st.button("发表评论"):
            res = run_tool("scripts/feed/write/do_comment.py", {"guild_id": g_id, "feed_id": feed_id, "content": comment_content})
            st.json(res)
            
        if st.button("帖子点赞"):
            res = run_tool("scripts/feed/write/do_feed_prefer.py", {"guild_id": g_id, "feed_id": feed_id, "like": True})
            st.json(res)

    with tab3:
        st.subheader("发布新帖子")
        pub_title = st.text_input("标题")
        pub_content = st.text_area("正文内容")
        if st.button("发布文字贴"):
            res = run_tool("scripts/feed/write/publish_feed.py", {"guild_id": g_id, "channel_id": channel_id, "title": pub_title, "content": pub_content})
            st.json(res)

elif page == "消息通知与用户操作":
    st.title("消息通知与用户操作")
    tab1, tab2 = st.tabs(["消息通知", "用户操作"])
    with tab1:
        st.subheader("发送 QQ 消息给自己")
        push_content = st.text_area("消息内容")
        if st.button("发送消息"):
            res = run_tool("scripts/manage/write/push_qq_msg.py", {"content": push_content})
            st.json(res)
        
        st.subheader("获取消息通知")
        g_id_notice = st.text_input("频道ID", key="notice_gid")
        if st.button("获取通知列表"):
            res = run_tool("scripts/feed/read/get_notices.py", {"guild_id": g_id_notice})
            st.json(res)
            
    with tab2:
        st.subheader("加入频道")
        join_g_id = st.text_input("频道ID", key="join_gid")
        if st.button("获取加入设置"):
            res = run_tool("scripts/manage/read/get_join_guild_setting.py", {"guild_id": join_g_id})
            st.json(res)
        join_msg = st.text_input("加群验证信息 (若需要)")
        if st.button("加入频道"):
            res = run_tool("scripts/manage/write/join_guild.py", {"guild_id": join_g_id, "verify_msg": join_msg})
            st.json(res)
            
        st.subheader("成员管理操作")
        target_uid = st.text_input("目标成员 TinyID")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            shutup_time = st.number_input("禁言时间(秒，0为解除)", min_value=0, value=60)
            if st.button("禁言/解禁成员"):
                res = run_tool("scripts/manage/write/modify_member_shut_up.py", {"guild_id": join_g_id, "member_tinyid": target_uid, "shutup_time": shutup_time})
                st.json(res)
        with col_m2:
            if st.button("踢出频道成员"):
                res = run_tool("scripts/manage/write/kick_guild_member.py", {"guild_id": join_g_id, "member_tinyid": target_uid})
                st.json(res)

elif page == "AI分析与生成":
    st.title("AI 助手 (OpenAI)")
    st.info("基于配置的 OpenAI 协议的接口，实现分析、评论和发帖适配。")
    
    tab1, tab2, tab3 = st.tabs(["AI 数据分析", "AI 评论生成", "AI 辅助发帖"])
    
    with tab1:
        st.subheader("对频道数据进行分析")
        analysis_data = st.text_area("粘贴需要分析的 JSON 数据或文本 (例如帖子列表、成员列表)")
        analysis_prompt = st.text_area("你的分析需求", value="请总结出上述数据中的主要话题和用户情感倾向。")
        if st.button("开始分析"):
            with st.spinner("AI 正在分析..."):
                res = ai_helper.analyze_data(analysis_data, analysis_prompt)
                st.markdown(res)
                
    with tab2:
        st.subheader("生成评论回复")
        post_text = st.text_area("帖子或原评论内容")
        comment_style = st.selectbox("评论风格", ["友好", "幽默", "专业", "反驳"])
        if st.button("生成评论"):
            with st.spinner("AI 正在生成..."):
                res = ai_helper.generate_comment(post_text, comment_style)
                st.text_area("生成的评论", value=res, height=150)
                
    with tab3:
        st.subheader("生成新帖子")
        topic = st.text_input("帖子主题/标题", value="今天社区的新鲜事")
        reqs = st.text_area("具体要求", value="包含欢迎新成员的内容，呼吁大家活跃。字数在200字左右。")
        if st.button("生成帖子草稿"):
            with st.spinner("AI 正在创作..."):
                res = ai_helper.generate_post(topic, reqs)
                st.text_area("生成的帖子内容", value=res, height=300)

elif page == "定时任务":
    st.title("定时任务")
    st.write("配置与管理定时任务（基于 APScheduler）")
    
    st.info("定时任务引擎状态：可以在下方启动或配置任务。")
    
    from scheduler_app import get_jobs, add_job, remove_job, start_scheduler
    
    start_scheduler()
    
    jobs = get_jobs()
    st.subheader("当前任务列表")
    if jobs:
        for j in jobs:
            st.text(f"任务ID: {j.id}, 下次运行: {j.next_run_time}")
            if st.button(f"删除任务 {j.id}", key=f"del_{j.id}"):
                remove_job(j.id)
                st.rerun()
    else:
        st.write("暂无运行中的任务。")
        
    st.subheader("添加新任务")
    task_type = st.selectbox("任务类型", ["内容巡检扫描", "问答自动回复", "定时AI发帖"])
    interval_minutes = st.number_input("执行间隔 (分钟)", min_value=1, value=60)
    
    guild_id = st.text_input("频道ID (执行任务所在频道)")
    
    if st.button("添加定时任务"):
        if task_type == "内容巡检扫描":
            add_job("scripts/feed/operation/auto_clean_channel_feeds.py", {"guild_id": guild_id}, interval_minutes)
            st.success("已添加巡检任务！")
        elif task_type == "问答自动回复":
            add_job("scripts/feed/operation/channel_qa_responder.py", {"guild_id": guild_id}, interval_minutes)
            st.success("已添加问答回复任务！")
        elif task_type == "定时AI发帖":
            st.warning("暂未完全支持定时AI发帖，请在后台扩展功能。")
        st.rerun()

