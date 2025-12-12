from textwrap import dedent
from agno.agent import Agent
from agno.run.agent import RunOutput
import streamlit as st
import re
import requests
from agno.tools import tool
from agno.models.openai import OpenAIChat
from icalendar import Calendar, Event
from datetime import datetime, timedelta

# -------------------------------------------------------
# 正确的：Agno 2.x 使用 “函数 + @tool” 的方式创建工具
# -------------------------------------------------------

@tool
def gaode_search(query: str, city: str, api_key: str) -> str:
    """高德地图搜索工具（完全适配 Agno 2.3.7）"""

    url = "https://restapi.amap.com/v5/place/text"
    params = {
        "key": api_key,
        "keywords": query,
        "city": city,
        "page_size": 10,
        "page_num": 1,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        if data.get("status") != "1":
            return f"高德 API 错误: {data.get('info')}"

        pois = data.get("pois", [])
        if not pois:
            return "未找到相关地点信息"

        results = []
        for p in pois:
            name = p.get("name")
            addr = p.get("address")
            type_ = p.get("type")
            results.append(f"{name} | {type_} | {addr}")

        return "\n".join(results)

    except Exception as e:
        return f"高德 API 调用异常: {e}"


# ------------------------------------------------
# 日程 ICS 文件生成（保持不变）
# ------------------------------------------------
def generate_ics_content(plan_text: str, start_date: datetime = None) -> bytes:
    cal = Calendar()
    cal.add('prodid','-//AI Travel Planner//' )
    cal.add('version', '2.0')

    if start_date is None:
        start_date = datetime.today()

    day_pattern = re.compile(r'Day (\d+)[:\s]+(.*?)(?=Day \d+|$)', re.DOTALL)
    days = day_pattern.findall(plan_text)

    if not days:
        event = Event()
        event.add('summary', "Travel Itinerary")
        event.add('description', plan_text)
        event.add('dtstart', start_date.date())
        event.add('dtend', start_date.date())
        event.add("dtstamp", datetime.now())
        cal.add_component(event)
    else:
        for day_num, day_content in days:
            day_num = int(day_num)
            current_date = start_date + timedelta(days=day_num - 1)

            event = Event()
            event.add('summary', f"Day {day_num} Itinerary")
            event.add('description', day_content.strip())
            event.add('dtstart', current_date.date())
            event.add('dtend', current_date.date())
            event.add("dtstamp", datetime.now())
            cal.add_component(event)

    return cal.to_ical()


# ------------------------------------------------
# Streamlit UI
# ------------------------------------------------
st.title("AI旅行规划师")
st.caption("使用高德地图 API 自动规划旅行行程，并生成 ICS 日历文件。")

if 'itinerary' not in st.session_state:
    st.session_state.itinerary = None

openai_api_key = st.text_input("Enter OpenAI API Key", type="password")
gaode_api_key = st.text_input("Enter 高德地图 API Key", type="password")

# ------------------------------------------------
# 只有提供两个 key 才能启动
# ------------------------------------------------
if openai_api_key and gaode_api_key:

    # -----------------------------
    # Researcher Agent
    # -----------------------------
    researcher = Agent(
        name="Researcher",
        role="使用高德地图搜索旅行目的地、活动、美食和住宿信息",
        model=OpenAIChat(id="gpt-4o", api_key=openai_api_key),
        description=dedent(
            """\
            你是世界级的旅行研究员。
            根据用户输入的目的地和天数，生成 3 个搜索关键词，并调用 gaode_search 工具。
            """
        ),
        instructions=[
            "生成 3 个与旅行相关的高德搜索关键词。",
            "每个关键词必须调用 gaode_search(query, city, api_key)。",
            "整理信息，输出最相关的 10 条真实地点推荐。",
        ],
        tools=[gaode_search],
    )

    # -----------------------------
    # Planner Agent
    # -----------------------------
    planner = Agent(
        name="Planner",
        role="根据研究结果生成旅行行程",
        model=OpenAIChat(id="gpt-4o", api_key=openai_api_key),
        description="你是资深旅行规划师。",
        instructions=[
            "根据研究结果生成每日活动、美食、住宿和路线建议。",
            "不要编造不存在的地点。",
        ],
    )

    destination = st.text_input("请输入目的地")
    num_days = st.number_input("请输入旅游天数?", min_value=1, max_value=30, value=5)

    col1, col2 = st.columns(2)

    # ------------------------------------------------
    # 按钮：生成行程
    # ------------------------------------------------
    with col1:
        if st.button("生成旅行规划"):
            st.write("正在使用高德地图搜索信息…")

            research_results: RunOutput = researcher.run(
                f"研究 {destination}，行程 {num_days} 天，使用 api_key={gaode_api_key}",
                stream=False
            )

            st.write("搜索完成，正在生成行程…")

            prompt = f"""
            Destination: {destination}
            Days: {num_days}

            Research Results:
            {research_results.content}

            请生成详细旅行行程。
            """

            response: RunOutput = planner.run(prompt, stream=False)
            st.session_state.itinerary = response.content
            st.write(response.content)

    # ------------------------------------------------
    # 右侧：下载 ICS
    # ------------------------------------------------
    with col2:
        if st.session_state.itinerary:
            ics_file = generate_ics_content(st.session_state.itinerary)
            st.download_button(
                "下载行程 (.ics)",
                data=ics_file,
                file_name="travel.ics",
                mime="text/calendar"
            )