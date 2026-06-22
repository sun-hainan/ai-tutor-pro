"""
多私教 AI 学习系统 - 主应用
"""
import streamlit as st
from datetime import datetime

from core.database import (
    init_db, get_session, User, Tutor, KnowledgePoint,
    Mistake, ChatSession, ChatMessage
)
from core.tutor_service import (
    TUTOR_TEMPLATES, create_tutor_from_template, create_custom_tutor,
    list_user_tutors, get_tutor, touch_tutor, update_tutor, delete_tutor
)
from core.tutor import (
    answer_question, generate_quiz, judge_answer,
    review_code, auto_categorize_mistake, generate_review_quiz
)
from core.spaced_repetition import (
    update_after_review, get_due_mistakes, get_weak_points, get_review_stats
)
from core.rag import (
    ingest_pdf, ingest_text, rag_answer, get_collection_stats
)
from core.llm import chat

# ========== 初始化 ==========
init_db()
db = get_session()

st.set_page_config(
    page_title="多私教 AI 学习系统",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ========== 侧边栏：用户管理 ==========
st.sidebar.title("👤 用户管理")
username = st.sidebar.text_input("用户名", value="default_user")

user = db.query(User).filter_by(username=username).first()
if not user:
    user = User(username=username)
    db.add(user)
    db.commit()
    st.sidebar.success(f"✅ 创建新用户：{username}")


# ========== 侧边栏：私教选择 ==========
st.sidebar.divider()
st.sidebar.title("🎓 选择私教")

tutors = list_user_tutors(db, user.id)
current_tutor = None

if not tutors:
    st.sidebar.warning("你还没有私教\n\n请在下方创建 👇")
else:
    tutor_options = {f"{t.icon} {t.name}": t for t in tutors}
    selected = st.sidebar.radio(
        "私教列表", 
        list(tutor_options.keys()),
        label_visibility="collapsed"
    )
    current_tutor = tutor_options[selected]
    touch_tutor(db, current_tutor.id)
    
    with st.sidebar.expander("📋 私教详情", expanded=False):
        st.caption(f"**学科**：{current_tutor.subject}")
        st.caption(f"**风格**：{current_tutor.style}")
        st.caption(f"**水平**：{current_tutor.level}")
        st.caption(f"**描述**：{current_tutor.description}")
        
        new_level = st.selectbox(
            "调整我的水平",
            ["beginner", "intermediate", "advanced"],
            index=["beginner", "intermediate", "advanced"].index(current_tutor.level),
            key=f"level_{current_tutor.id}"
        )
        if new_level != current_tutor.level:
            update_tutor(db, current_tutor.id, level=new_level)
            st.rerun()


# ========== 侧边栏：创建私教 ==========
st.sidebar.divider()
with st.sidebar.expander("➕ 创建新私教", expanded=False):
    tab1, tab2 = st.tabs(["从模板", "自定义"])
    
    with tab1:
        template_options = list(TUTOR_TEMPLATES.keys())
        template_choice = st.selectbox(
            "选择学习目标",
            template_options,
            format_func=lambda x: f"{TUTOR_TEMPLATES[x]['icon']} {TUTOR_TEMPLATES[x]['name']}",
            key="tmpl_select"
        )
        
        if template_choice:
            t = TUTOR_TEMPLATES[template_choice]
            st.info(f"📖 {t['description']}")
        
        custom_name = st.text_input("私教名（留空用默认）", key="tmpl_name")
        
        if st.button("🚀 立即创建", key="tmpl_create", use_container_width=True):
            try:
                tutor = create_tutor_from_template(db, user.id, template_choice, custom_name or None)
                st.success(f"✅ 已创建：{tutor.icon} {tutor.name}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 创建失败：{e}")
    
    with tab2:
        with st.form("custom_tutor_form"):
            st.markdown("**完全自定义你的私教**")
            name = st.text_input("私教名*", value="我的专属老师")
            subject = st.text_input("学科", value="通用")
            icon = st.text_input("图标", value="🎯")
            description = st.text_area("简介", height=60)
            system_prompt = st.text_area(
                "人设 Prompt*",
                height=200,
                placeholder="例：你是一个耐心的英语老师...\n- 风格：...\n- 范围：..."
            )
            level = st.select_slider("起点水平", options=["beginner", "intermediate", "advanced"])
            style = st.selectbox("风格", ["patient", "strict", "humorous", "professional"])
            
            if st.form_submit_button("创建私教", use_container_width=True):
                if name and system_prompt:
                    try:
                        tutor = create_custom_tutor(
                            db, user.id, name, subject, description,
                            system_prompt, icon, level, style
                        )
                        st.success(f"✅ 已创建：{tutor.icon} {tutor.name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 创建失败：{e}")
                else:
                    st.error("请填写私教名和人设 Prompt")


# ========== 侧边栏：危险操作 ==========
if current_tutor:
    with st.sidebar.expander("⚠️ 危险操作", expanded=False):
        st.warning(f"删除 **{current_tutor.name}** 将清除所有错题、对话、资料！")
        if st.button("🗑️ 删除这个私教", type="secondary"):
            if delete_tutor(db, current_tutor.id):
                st.success("已删除")
                st.rerun()


# ========== 主区域：未选私教时 ==========
if not current_tutor:
    st.title("🎓 多私教 AI 学习系统")
    st.info("👈 请先在左侧创建一个私教开始学习")
    
    st.markdown("""
    ### 💡 系统功能
    
    - **多私教管理**：每个学习目标独立私教，互不干扰
    - **智能答疑**：基于人设的个性化回答
    - **AI 出题**：按主题/难度自动出题
    - **代码评审**：贴代码获得专业反馈
    - **错题复习**：艾宾浩斯算法自动安排复习
    - **资料问答**：上传 PDF 让 AI 基于资料回答
    - **学习画像**：可视化学习进度
    
    ### 🚀 快速开始
    
    1. 左侧 "创建新私教" → "从模板" → 选个学习目标
    2. 主区域选功能模式（答疑/刷题/复习等）
    3. 开始学习！
    """)
    st.stop()


# ========== 主区域：已选私教 ==========
st.title(f"{current_tutor.icon} {current_tutor.name}")
st.caption(f"📖 {current_tutor.description}")

mode = st.radio(
    "选择功能",
    ["💬 答疑", "📝 刷题", "🔍 评审代码", "❌ 复习错题", "📖 资料问答", "📊 学习画像"],
    horizontal=True
)
st.divider()


# ========== 模式 1：答疑 ==========
if mode == "💬 答疑":
    st.header("💬 与私教对话")
    
    # 当前对话 session
    if "current_session_id" not in st.session_state or \
       st.session_state.get("current_tutor_id") != current_tutor.id:
        new_session = ChatSession(tutor_id=current_tutor.id, title="新对话")
        db.add(new_session)
        db.commit()
        st.session_state.current_session_id = new_session.id
        st.session_state.current_tutor_id = current_tutor.id
        st.session_state.messages = []
    
    session_id = st.session_state.current_session_id
    messages = db.query(ChatMessage).filter_by(session_id=session_id)\
        .order_by(ChatMessage.id).all()
    
    for msg in messages:
        with st.chat_message(msg.role):
            st.write(msg.content)
    
    if user_input := st.chat_input("问私教任何问题..."):
        db.add(ChatMessage(session_id=session_id, role="user", content=user_input))
        db.commit()
        with st.chat_message("user"):
            st.write(user_input)
        
        history = [{"role": m.role, "content": m.content} for m in messages]
        messages_for_llm = [{"role": "system", "content": current_tutor.system_prompt}]
        messages_for_llm.extend(history)
        messages_for_llm.append({"role": "user", "content": user_input})
        
        with st.chat_message("assistant"):
            with st.spinner("🤔 思考中..."):
                reply = chat(messages_for_llm)
                st.write(reply)
        
        db.add(ChatMessage(session_id=session_id, role="assistant", content=reply))
        db.commit()
    
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🗑️ 清空对话"):
            db.query(ChatMessage).filter_by(session_id=session_id).delete()
            db.commit()
            st.rerun()


# ========== 模式 2：刷题 ==========
elif mode == "📝 刷题":
    st.header("📝 让私教出题")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        topic = st.text_input("练什么知识点？", placeholder="装饰器 / 列表推导式 / JOIN ...")
    with col2:
        difficulty = st.select_slider("难度", options=["easy", "medium", "hard"])
    
    if st.button("🎲 出题", use_container_width=True) and topic:
        with st.spinner("AI 出题中..."):
            quiz = generate_quiz(topic, difficulty)
        st.session_state.current_quiz = quiz
        st.session_state.current_topic = topic
    
    if "current_quiz" in st.session_state:
        q = st.session_state.current_quiz
        st.subheader(q["question"])
        
        user_ans = st.radio(
            "选择答案",
            list(q["options"].keys()),
            format_func=lambda x: f"{x}. {q['options'][x]}",
            key="quiz_ans"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 提交答案", use_container_width=True):
                correct = (user_ans == q["correct_answer"])
                if correct:
                    st.success(f"🎉 正确！\n\n{q['explanation']}")
                else:
                    st.error(f"❌ 错了\n\n正确答案：{q['correct_answer']}\n\n{q['explanation']}")
                
                st.session_state.last_answer = user_ans
                st.session_state.was_correct = correct
        
        with col2:
            if st.button("🔄 换一题", use_container_width=True):
                if "current_quiz" in st.session_state:
                    del st.session_state.current_quiz
                st.rerun()
        
        if "was_correct" in st.session_state and not st.session_state.was_correct:
            if st.button("➕ 加入错题本"):
                cat = auto_categorize_mistake(
                    question=q["question"],
                    wrong_answer=st.session_state.last_answer,
                    correct_answer=q["correct_answer"]
                )
                kp = db.query(KnowledgePoint).filter_by(name=cat["knowledge_point"]).first()
                if not kp:
                    kp = KnowledgePoint(name=cat["knowledge_point"], category=cat.get("category", ""))
                    db.add(kp)
                    db.commit()
                
                mistake = Mistake(
                    tutor_id=current_tutor.id,
                    kp_id=kp.id,
                    question=q["question"],
                    user_answer=st.session_state.last_answer,
                    correct_answer=q["correct_answer"],
                    explanation=q["explanation"]
                )
                db.add(mistake)
                db.commit()
                st.success(f"✅ 已加入错题本 [{cat['knowledge_point']}]")
                del st.session_state.was_correct
                del st.session_state.last_answer


# ========== 模式 3：评审代码 ==========
elif mode == "🔍 评审代码":
    st.header("🔍 让私教评审你的代码")
    
    code = st.text_area("贴代码：", height=300, placeholder="把你的 Python 代码贴在这里...")
    
    col1, col2 = st.columns(2)
    with col1:
        language = st.selectbox("语言", ["python", "javascript", "sql", "java", "cpp", "go"])
    with col2:
        st.write("")
    
    if st.button("🤖 让私教评审", use_container_width=True) and code.strip():
        with st.spinner("私教评审中..."):
            prompt = f"请评审这段 {language} 代码：\n```{language}\n{code}\n```"
            result = chat([
                {"role": "system", "content": current_tutor.system_prompt},
                {"role": "user", "content": prompt}
            ])
        st.markdown(result)


# ========== 模式 4：复习错题 ==========
elif mode == "❌ 复习错题":
    st.header("❌ 错题复习")
    
    due = get_due_mistakes(db, current_tutor.id)
    stats = get_review_stats(db, current_tutor.id)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总错题", stats["total_mistakes"])
    col2.metric("今日待复习", stats["due_today"])
    col3.metric("已掌握", stats["mastered"])
    col4.metric("掌握率", f"{stats['mastery_rate']:.0f}%")
    
    st.divider()
    
    if stats["total_mistakes"] == 0:
        st.info("🎉 还没有错题，去「刷题」模式做几道题吧！")
    elif stats["due_today"] == 0:
        st.success("🎉 今天没有要复习的，明天再来！")
    else:
        st.write(f"📅 今日有 **{len(due)}** 道错题需要复习")
        
        if "review_quiz" not in st.session_state:
            if st.button("🚀 开始复习", use_container_width=True):
                with st.spinner("AI 生成复习题..."):
                    review_q = generate_review_quiz(due)
                st.session_state.review_quiz = review_q
                st.session_state.review_mistake = due[0]
                st.rerun()
        
        if "review_quiz" in st.session_state:
            q = st.session_state.review_quiz
            st.subheader("📝 复习题（基于你的错题）")
            st.write(q["question"])
            
            user_ans = st.radio(
                "选择",
                list(q["options"].keys()),
                format_func=lambda x: f"{x}. {q['options'][x]}",
                key="review_ans"
            )
            
            if st.button("提交", use_container_width=True):
                correct = (user_ans == q["correct_answer"])
                if correct:
                    st.success(f"✅ 答对了！\n\n{q['explanation']}")
                else:
                    st.error(f"❌ 答错了\n\n正确答案：{q['correct_answer']}\n\n{q['explanation']}")
                
                m = st.session_state.review_mistake
                update_after_review(m, is_correct=correct)
                db.commit()
                st.info(f"📅 下次复习：{m.next_review.strftime('%Y-%m-%d')}")
                
                del st.session_state.review_quiz
                del st.session_state.review_mistake
                st.balloons()
                st.rerun()


# ========== 模式 5：资料问答 ==========
elif mode == "📖 资料问答":
    st.header(f"📖 {current_tutor.name} 的资料库")
    
    stats = get_collection_stats(current_tutor.rag_collection)
    col1, col2 = st.columns([1, 4])
    col1.metric("📚 资料块数", stats["doc_count"])
    
    st.divider()
    
    st.subheader("📤 上传教程")
    col1, col2 = st.columns(2)
    with col1:
        uploaded_pdf = st.file_uploader("上传 PDF", type=["pdf"], key="pdf_upload")
    with col2:
        uploaded_text = st.file_uploader("上传 MD/TXT", type=["md", "txt"], key="text_upload")
    
    if uploaded_pdf:
        save_path = f"./uploads/{current_tutor.id}_{uploaded_pdf.name}"
        with open(save_path, "wb") as f:
            f.write(uploaded_pdf.getbuffer())
        with st.spinner("私教学习中..."):
            n = ingest_pdf(save_path, current_tutor.rag_collection)
        st.success(f"✅ 已学习 {n} 块内容")
        st.rerun()
    
    if uploaded_text:
        text_content = uploaded_text.getvalue().decode("utf-8")
        with st.spinner("私教学习中..."):
            n = ingest_text(text_content, uploaded_text.name, current_tutor.rag_collection)
        st.success(f"✅ 已学习 {n} 块内容")
        st.rerun()
    
    st.divider()
    
    st.subheader("❓ 问私教关于资料的问题")
    question = st.text_input("你的问题", placeholder="这份教程里讲了什么？")
    
    if st.button("🤔 询问私教", use_container_width=True) and question:
        with st.spinner("查资料中..."):
            answer = rag_answer(question, current_tutor.rag_collection, current_tutor.name)
        st.markdown("---")
        st.markdown(answer)


# ========== 模式 6：学习画像 ==========
elif mode == "📊 学习画像":
    st.header(f"📊 {current_tutor.name} 的学习画像")
    
    stats = get_review_stats(db, current_tutor.id)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📝 总错题", stats["total_mistakes"])
    col2.metric("⏰ 待复习", stats["due_today"])
    col3.metric("✅ 已掌握", stats["mastered"])
    col4.metric("📈 掌握率", f"{stats['mastery_rate']:.0f}%")
    
    st.divider()
    
    st.subheader("🎯 薄弱知识点 Top 5")
    weak = get_weak_points(db, current_tutor.id, top_n=5)
    
    if not weak:
        st.info("还没有错题数据，去刷题模式积累吧！")
    else:
        import pandas as pd
        df = pd.DataFrame(weak)
        df.columns = ["知识点", "错题数"]
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        import plotly.express as px
        fig = px.bar(
            df, x="知识点", y="错题数",
            title=f"{current_tutor.name} - 薄弱知识点分布",
            color="错题数", color_continuous_scale="Reds"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    st.subheader("📅 错题时间趋势")
    from sqlalchemy import func
    
    results = db.query(
        func.date(Mistake.created_at).label('date'),
        func.count(Mistake.id).label('count')
    ).filter(Mistake.tutor_id == current_tutor.id)\
     .group_by('date').order_by('date').all()
    
    if results:
        import plotly.graph_objects as go
        fig = go.Figure(data=go.Scatter(
            x=[r[0] for r in results],
            y=[r[1] for r in results],
            mode='lines+markers',
            name='每日错题数',
            line=dict(color='#FF6B6B', width=3),
            marker=dict(size=10)
        ))
        fig.update_layout(
            title="每日错题数趋势",
            xaxis_title="日期",
            yaxis_title="错题数"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无数据")