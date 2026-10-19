from datetime import datetime

import streamlit as st

import db
import service
from ai.agent import chat_stream
from ai.pipeline import parse_and_validate, AIServiceError
from utils.config_tool import config_calc
from utils.logger_tool import logger

ACTIVITY_LABELS = {"sedentary": "久坐", "light": "轻度活动", "moderate": "中度活动",
                   "high": "高度活动", "extreme": "极高活动"}
GOAL_LABELS = {"muscle_gain": "增肌", "fat_loss": "减脂", "maintain": "维持"}

st.set_page_config(page_title='Fitness_Diet_Assistant', page_icon='🥘', layout='wide')
st.title(body='健身饮食助手', text_alignment='center')
tab1, tab2, tab3 = st.tabs(["我的计划", "今日记录", "问问AI"])

# 侧边栏，存放用户画像
with st.sidebar:
    # 性别选择器
    gender = st.selectbox("性别", options=["male", "female"], format_func=lambda g: "男" if g == "male" else "女")
    # 体重输入
    weight = st.number_input("体重(kg)", min_value=30.0, max_value=200.0, value=70.0, step=0.5)
    # 身高输入
    height = st.number_input("身高(cm)", min_value=100.0, max_value=250.0, value=175.0, step=0.5)
    # 年龄输入
    age = st.number_input('年龄', min_value=10, max_value=80, value=18, step=1)
    # 活动水平选择器
    act_opts = list(config_calc["ACTIVITY_FACTORS"])
    activity = st.selectbox("活动水平", options=act_opts, index=act_opts.index("moderate"),
                            format_func=lambda k: ACTIVITY_LABELS[k])
    # 目标选择器
    goal = st.selectbox("目标", options=list(config_calc["GOAL_KCAL_FACTOR"]), format_func=lambda k: GOAL_LABELS[k])

    # 按钮生成计划
    if st.button("生成计划", width="stretch"):
        st.session_state["plan"] = service.build_plan(gender, weight, height, age, activity, goal)
        st.session_state["goal_label"] = GOAL_LABELS[goal]

    # 选项卡1：我的计划
with tab1:
    plan = st.session_state.get("plan")
    if plan is None:
        st.info('请在左侧填写个人信息，点击生成计划！')
    else:
        # 一行四列显示目标热量和宏量营养素
        col1, col2, col3, col4 = st.columns(4, border=True)
        col1.metric('热量', f'{plan["target"]["kcal"]:.0f} kcal')
        col2.metric('蛋白质', f'{plan["target"]["protein_g"]:.0f} g')
        col3.metric('脂肪', f'{plan["target"]["fat_g"]:.0f} g')
        col4.metric('碳水', f'{plan["target"]["carb_g"]:.0f} g')

        # 一行小号灰色说明文字显示BMR和TDEE
        st.caption(f"BMR（基础代谢）{plan['bmr']:.0f} kcal　|　TDEE（每日总消耗）{plan['tdee']:.0f} kcal")
        st.caption('以上基于上次点击『生成计划』时的画像')

# 选项卡2：今日记录
with tab2:
    # 日期选择器
    d = st.date_input("日期", value=datetime.now().date())
    date_str = d.isoformat()

    # ——————————ai记录———————————
    st.divider()
    st.subheader('一句话记录（AI）')
    text = st.text_input("请输入一句话描述今天吃的食物(如：我今天吃了150克鸡蛋)")
    if st.button('提交', key='parse_btn'):
        if not text.strip():
            st.warning('请输入内容')
        else:
            try:
                with st.spinner('解析中...'):
                    st.session_state['parsed'] = parse_and_validate(text)
            except AIServiceError:
                st.error("解析服务暂时不可用，请稍后重试。手动记录仍可正常使用。")

    parsed = st.session_state.get('parsed')
    if parsed:
        if sum(len(s) for s in parsed.values()) == 0:
            st.info("没有识别到任何食物，换个说法试试？")
        else:
            if parsed["ok"]:
                st.success(f"可直接添加（{len(parsed['ok'])} 项）")
                for i, item in enumerate(parsed["ok"]):
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"{item['raw']} → {item['food']} {item['grams']}g")
                    if c2.button("添加", key=f"add_ok_{i}"):
                        db.add_intake(date_str, item["food"], item["grams"])
                        parsed["ok"].pop(i)  # 已处理，移出待确认
                        st.session_state["parsed"] = parsed
                        st.rerun()

            if parsed["ambiguous"]:
                st.warning(f'需确认（{len(parsed["ambiguous"])} 项）')
                for i, item in enumerate(parsed["ambiguous"]):
                    c1, c2 = st.columns([4, 1])
                    for j, candidate in enumerate(item["candidates"]):
                        c1.write(f"{item['raw']} → {candidate}{item['grams']}")
                        if c2.button("添加", key=f"add_amb_{i}_{j}"):
                            db.add_intake(date_str, candidate, item["grams"])
                            parsed["ambiguous"].pop(i)  # 已处理，移出待确认
                            st.session_state["parsed"] = parsed
                            st.rerun()

            if st.button("清空待确认", key="clear_parsed"):
                st.session_state.pop("parsed", None)
                st.rerun()

            if parsed["not_found"]:
                st.error(f'未找到（{len(parsed["not_found"])} 项）')
                for i, item in enumerate(parsed["not_found"]):
                    c1, c2, c3 = st.columns([3, 3, 1])
                    c1.write(f"{item['raw']} ({item['grams'] or '克数待补'} )")

                    revise = c2.text_input('请输入修改的食物',
                                           key=f"revise_input_{i}",
                                           label_visibility="collapsed",
                                           placeholder="输入库中已有的食物名")
                    if c3.button('修改', key=f"revise_{i}"):
                        if not revise.strip():
                            st.warning('请输入修改内容')
                        elif item['grams'] is None:
                            st.warning('该项缺少克数，无法添加')
                        else:
                            result = db.query_food(revise)
                            if result:
                                db.add_intake(date_str, result["name"], item["grams"])
                                parsed["not_found"].pop(i)  # 已处理，移出待确认
                                st.session_state["parsed"] = parsed
                                st.rerun()
                            else:
                                st.warning(f'数据库中未找到 {revise},试试更完整的名称')

            if parsed["invalid"]:
                st.error(f'数据错误（{len(parsed["invalid"])} 项）')
                for i, item in enumerate(parsed["invalid"]):
                    c1, c2 = st.columns([5, 1])
                    c1.write(f"{item['raw']}  {item['grams']}g — {item['reason']}")
                    if c2.button("忽略", key=f"ignore_inv_{i}"):
                        parsed["invalid"].pop(i)
                        st.session_state["parsed"] = parsed
                        st.rerun()

    # ——————————手动记录——————————
    # 食物选择器和克数输入
    st.divider()
    st.subheader('手动记录')
    foods = [f["name"] for f in db.search_foods("")]  # 全部食物名
    food = st.selectbox("食物", options=foods)
    grams = st.number_input("克数(g)", min_value=1.0, value=100.0, step=10.0)

    # 添加按钮
    if st.button("添加"):
        db.add_intake(date_str, food, grams)
        st.rerun()

    # 显示今日记录
    plan = st.session_state.get("plan")
    if plan is None:
        st.warning('请先生成计划，否则无法计算缺口')
    else:
        report = service.build_daily_report(date_str, plan['target'])

        # 记录列表+删除
        st.divider()
        st.header('今日记录')
        if not report['items']:
            st.info('今天还没记录')
        else:
            c = st.columns([2, 1.2, 1.2, 1.2, 1.2, 1.2, 0.9])
            c[0].markdown('食物名称')
            c[1].markdown('克数(g)')
            c[2].markdown('热量(kcal)')
            c[3].markdown('蛋白质(g)')
            c[4].markdown('脂肪(g)')
            c[5].markdown('碳水(g)')

            for item in report['items']:
                c = st.columns([2, 1.2, 1.2, 1.2, 1.2, 1.2, 0.9], vertical_alignment="center")
                c[0].write(f'{item["name"]}')
                c[1].write(f'{item["grams"]:.1f}g')
                c[2].write(f'{item["kcal"]:.0f}kcal')
                c[3].write(f'{item["protein_g"]:.0f}g')
                c[4].write(f'{item["fat_g"]:.0f}g')
                c[5].write(f'{item["carb_g"]:.0f}g')
                if c[6].button('删除', key=f'del_{item["id"]}'):
                    db.delete_intake(item['id'])
                    st.rerun()

        # 汇总
        st.divider()
        st.header('汇总')
        c = st.columns([1.4, 1, 1, 1, 1])
        c[1].write("热量(kcal)")
        c[2].write("蛋白质(g)")
        c[3].write("脂肪(g)")
        c[4].write("碳水(g)")
        for label, d in [("目标", plan["target"]), ("已摄入", report["total"]), ("剩余", report["gap"])]:
            c = st.columns([1.4, 1, 1, 1, 1])
            c[0].write(f"**{label}**")
            c[1].write(f"{d['kcal']:.0f}")
            c[2].write(f"{d['protein_g']:.0f}")
            c[3].write(f"{d['fat_g']:.0f}")
            c[4].write(f"{d['carb_g']:.0f}")

# 选项卡3：问问AI
MAX_HISTORY = 20
with tab3:
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    hist = st.session_state["chat_history"]
    if len(hist) > MAX_HISTORY:
        hist = hist[-MAX_HISTORY:]
    while hist and hist[0]["role"] != "user":
        hist.pop(0)
    st.session_state["chat_history"] = hist

    plan = st.session_state.get("plan")
    if plan is None:
        st.info('请先在左侧生成计划，否则AI无法获取建议')
    else:
        # 渲染聊天历史
        if not st.session_state["chat_history"]:
            st.chat_message("assistant").write("问我任何关于食物营养、今日摄入的问题")

        for m in st.session_state["chat_history"]:
            st.chat_message(m["role"]).write(m["content"])

        # ② 处理上一轮提交的问题
        pending = st.session_state.pop("pending_question", None)
        today = datetime.now().strftime("%Y-%m-%d")

        if pending:
            st.session_state["chat_history"].append({"role": "user", "content": pending})
            st.chat_message("user").write(pending)

            with st.chat_message("assistant"):
                box = st.empty()
                buf = ""

                try:
                    for msg in chat_stream(st.session_state["chat_history"],
                                           plan["target"],
                                           today,
                                           st.session_state.get("goal_label", "")):
                        if msg["type"] == "text":
                            buf += msg['content']
                            box.markdown(buf)
                except AIServiceError:
                    box.error("AI服务暂时不可用，请稍后重试。")
                    st.session_state["chat_history"].pop()
                except Exception as e:
                    logger.exception("chat_stream failed")  # 日志留完整堆栈
                    box.error("AI 服务出错了，请稍后重试。")  # 界面只给结论
                    st.session_state["chat_history"].pop()
                else:
                    st.session_state['chat_history'].append({"role": "assistant", "content": buf})

        # ③ 处理本轮用户输入
        with st.form("ask_form", clear_on_submit=True):
            c1, c2 = st.columns([6, 1])
            q = c1.text_input("提问", label_visibility="collapsed", placeholder="问点什么....")
            if c2.form_submit_button("提交"):
                if q.strip():
                    st.session_state["pending_question"] = q.strip()
                    st.rerun()
