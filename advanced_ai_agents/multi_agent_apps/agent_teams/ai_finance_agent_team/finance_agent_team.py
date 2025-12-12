from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
from agno.os import AgentOS

# Setup database for storage
db = SqliteDb(db_file="agents.db")

web_agent = Agent(
    name="Web Agent",
    role="Search the web for information",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    db=db,
    add_history_to_context=True,
    markdown=True,
)

finance_agent = Agent(
    name="Finance Agent",
    role="Get financial data",
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(

    )],
    instructions=["Always use tables to display data"],
    db=db,
    add_history_to_context=True,
    markdown=True,
)

# Team 只是一个逻辑结构，不是 Agent
agent_team = Team(
    name="Agent Team (Web+Finance)",
    model=OpenAIChat(id="gpt-4o"),
    members=[web_agent, finance_agent],
    debug_mode=True,
    markdown=True,
)

# Agno 2.x 必须把 agents 展开传入
agent_os = AgentOS(
    agents=[web_agent, finance_agent]
)

app = agent_os.get_app()

if __name__ == "__main__":
    # ⚠️ 这里必须写你的 Python 文件名 : app
    # 假设你的文件名叫 finance_agent_team.py
    agent_os.serve(app="finance_agent_team:app", reload=True)
