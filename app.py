import streamlit as st
import db
import service
from datetime import datetime
from utils.config_tool import config_calc

ACTIVITY_LABELS = {"sedentary": "久坐", "light": "轻度活动", "moderate": "中度活动",
                   "high": "高度活动", "extreme": "极高活动"}
GOAL_LABELS = {"muscle_gain": "增肌", "fat_loss": "减脂", "maintain": "维持"}

st.set_page_config(page_title='Fitness_Diet_Assistant',page_icon='🥘',layout='wide')
st.title(body='健身饮食助手',text_alignment='center')
tab1, tab2 = st.tabs(["我的计划", "今日记录"])

#侧边栏，存放用户画像
with st.sidebar:
    # 性别选择器
    gender = st.selectbox("性别", options=["male", "female"], format_func=lambda g: "男" if g == "male" else "女")
    # 体重输入
    weight = st.number_input("体重(kg)", min_value=30.0, max_value=200.0, value=70.0, step=0.5)
    # 身高输入
    height = st.number_input("身高(cm)", min_value=100.0, max_value=250.0, value=175.0, step=0.5)
    # 年龄输入
    age = st.number_input('年龄',min_value=10,max_value=100,value=18,step=1)
    # 活动水平选择器
    act_opts = list(config_calc["ACTIVITY_FACTORS"])
    # 目标选择器
    activity = st.selectbox("活动水平",  options=act_opts, index=act_opts.index("moderate"),
                 format_func=lambda k: ACTIVITY_LABELS[k])
    goal = st.selectbox("目标", options=list(config_calc["GOAL_KCAL_FACTOR"]), format_func=lambda k: GOAL_LABELS[k])

    # 按钮生成计划
    if st.button("生成计划",width="stretch"):
        st.session_state["plan"] = service.build_plan(gender, weight, height, age, activity, goal)

with tab1:
    plan = st.session_state.get("plan")
    if plan is None:
        st.info('请在左侧填写个人信息，点击生成计划！')
    else:
        # 一行四列显示目标热量和宏量营养素
        col1,col2,col3,col4 = st.columns(4,border=True)
        col1.metric('热量',f'{plan["target"]["kcal"]:.0f} kcal')
        col2.metric('蛋白质',f'{plan["target"]["protein_g"]:.0f} g')
        col3.metric('脂肪',f'{plan["target"]["fat_g"]:.0f} g')
        col4.metric('碳水',f'{plan["target"]["carb_g"]:.0f} g')

        # 一行小号灰色说明文字显示BMR和TDEE
        st.caption(f"BMR（基础代谢）{plan['bmr']:.0f} kcal　|　TDEE（每日总消耗）{plan['tdee']:.0f} kcal")
        st.caption('以上基于上次点击『生成计划』时的画像')

with tab2:
    # 日期选择器
    d = st.date_input("日期", value=datetime.now().date())
    date_str = d.isoformat()

    # 食物选择器和克数输入
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
        st.stop()

    report = service.build_daily_report(date_str, plan['target'])

    # 记录列表+删除
    st.divider()
    st.subheader('今日记录')
    if not report['items']:
        st.info('今天还没记录')
    else:
        c = st.columns([2,1.2,1.2,1.2,1.2,1.2,0.9])
        c[0].markdown('食物名称')
        c[1].markdown('克数(g)')
        c[2].markdown('热量(kcal)')
        c[3].markdown('蛋白质(g)')
        c[4].markdown('脂肪(g)')
        c[5].markdown('碳水(g)')

        for item in report['items']:
            c = st.columns([2, 1.2, 1.2, 1.2, 1.2, 1.2, 0.9],vertical_alignment="center")
            c[0].write(f'{item["name"]}')
            c[1].write(f'{item["grams"]:.1f}g')
            c[2].write(f'{item["kcal"]:.0f}kcal')
            c[3].write(f'{item["protein_g"]:.0f}g')
            c[4].write(f'{item["fat_g"]:.0f}g')
            c[5].write(f'{item["carb_g"]:.0f}g')
            if c[6].button('删除',key=f'del_{item["id"]}' ):
                db.delete_intake(item['id'])
                st.rerun()

    # 汇总
    st.divider()
    st.subheader('汇总')
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

