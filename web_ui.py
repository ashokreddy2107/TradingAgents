import streamlit as st
import datetime
import time
from pathlib import Path
from dotenv import load_dotenv

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from cli.models import AnalystType
from cli.stats_handler import StatsCallbackHandler
from cli.utils import classify_message_type

# Load environment variables
load_dotenv()
load_dotenv(".env.enterprise", override=False)

st.set_page_config(page_title="TradingAgents UI", page_icon="📈", layout="wide")

# Sidebar for inputs
with st.sidebar:
    st.title("TradingAgents settings")
    ticker = st.text_input("Ticker Symbol", value="SPY")
    analysis_date = st.date_input("Analysis Date", value=datetime.date.today())

    st.subheader("Analyst Selection")
    analysts_options = {
        "Market Analyst": AnalystType.MARKET,
        "Social Analyst": AnalystType.SOCIAL,
        "News Analyst": AnalystType.NEWS,
        "Fundamentals Analyst": AnalystType.FUNDAMENTALS
    }
    selected_analyst_names = st.multiselect(
        "Select Analyst Teams",
        options=list(analysts_options.keys()),
        default=["Market Analyst", "News Analyst", "Fundamentals Analyst"]
    )
    selected_analysts = [analysts_options[name] for name in selected_analyst_names]

    st.subheader("LLM Configuration")
    llm_provider = st.selectbox("LLM Provider", ["OpenAI", "Google", "Anthropic", "xAI", "OpenRouter", "Ollama"])
    shallow_thinker = st.text_input("Quick Thinker Model", value="gpt-4o-mini")
    deep_thinker = st.text_input("Deep Thinker Model", value="gpt-4o")
    research_depth = st.slider("Debate / Research Depth", min_value=1, max_value=5, value=2)
    output_language = st.selectbox("Output Language", ["English", "Spanish", "French", "German", "Chinese", "Japanese", "Korean"])
    backend_url = st.text_input("Backend URL (Optional)", value="")

    run_button = st.button("Run Analysis", type="primary")

# Main display area
st.title("TradingAgents Analysis Dashboard")

if run_button:
    if not selected_analysts:
        st.error("Please select at least one analyst.")
    else:
        st.write(f"**Analyzing {ticker} on {analysis_date}**")

        # Configure the settings
        config = DEFAULT_CONFIG.copy()
        config["max_debate_rounds"] = research_depth
        config["max_risk_discuss_rounds"] = research_depth
        config["quick_think_llm"] = shallow_thinker
        config["deep_think_llm"] = deep_thinker
        config["llm_provider"] = llm_provider.lower()
        if backend_url:
            config["backend_url"] = backend_url
        config["output_language"] = output_language

        stats_handler = StatsCallbackHandler()

        # Normalize analyst keys
        ANALYST_ORDER = ["market", "social", "news", "fundamentals"]
        selected_set = {analyst.value for analyst in selected_analysts}
        selected_analyst_keys = [a for a in ANALYST_ORDER if a in selected_set]

        graph = TradingAgentsGraph(
            selected_analyst_keys,
            config=config,
            debug=True,
            callbacks=[stats_handler],
        )

        init_agent_state = graph.propagator.create_initial_state(
            ticker, analysis_date.strftime("%Y-%m-%d")
        )
        args = graph.propagator.get_graph_args(callbacks=[stats_handler])

        # Display placeholders
        status_placeholder = st.empty()
        log_placeholder = st.empty()
        report_placeholder = st.empty()

        logs = []
        reports = {}
        processed_message_ids = set()

        def update_ui(chunk_num=None):
            with status_placeholder.container():
                st.info("Analysis in progress...")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("LLM Calls", stats_handler.llm_calls)
                    st.metric("Total Tokens", stats_handler.total_tokens)
                with col2:
                    st.metric("Tool Calls", stats_handler.tool_calls)
                    st.metric("Cost", f"${stats_handler.total_cost:.4f}")

            with log_placeholder.expander("Agent Logs", expanded=False):
                for log in logs[-20:]:  # Show last 20 logs
                    st.text(log)

            with report_placeholder.container():
                st.subheader("Generated Reports")
                for report_name, content in reports.items():
                    with st.expander(report_name.replace("_", " ").title(), expanded=True):
                        st.markdown(content)

        trace = []
        for chunk in graph.graph.stream(init_agent_state, **args):
            for message in chunk.get("messages", []):
                msg_id = getattr(message, "id", None)
                if msg_id is not None:
                    if msg_id in processed_message_ids:
                        continue
                    processed_message_ids.add(msg_id)

                msg_type, content = classify_message_type(message)
                if content and content.strip():
                    logs.append(f"[{msg_type}] {content[:100]}...")

                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tool_call in message.tool_calls:
                        name = tool_call["name"] if isinstance(tool_call, dict) else tool_call.name
                        logs.append(f"[Tool Call] {name}")

            # Extract reports
            for section in ["market_report", "sentiment_report", "news_report", "fundamentals_report", "investment_plan", "trader_investment_plan", "final_trade_decision"]:
                if chunk.get(section):
                    reports[section] = chunk[section]

            if chunk.get("investment_debate_state"):
                debate_state = chunk["investment_debate_state"]
                bull_hist = debate_state.get("bull_history", "").strip()
                bear_hist = debate_state.get("bear_history", "").strip()
                judge = debate_state.get("judge_decision", "").strip()
                if bull_hist: reports["investment_plan_bull"] = bull_hist
                if bear_hist: reports["investment_plan_bear"] = bear_hist
                if judge: reports["investment_plan_judge"] = judge

            if chunk.get("risk_debate_state"):
                risk_state = chunk["risk_debate_state"]
                agg_hist = risk_state.get("aggressive_history", "").strip()
                con_hist = risk_state.get("conservative_history", "").strip()
                neu_hist = risk_state.get("neutral_history", "").strip()
                judge = risk_state.get("judge_decision", "").strip()
                if agg_hist: reports["final_trade_decision_agg"] = agg_hist
                if con_hist: reports["final_trade_decision_con"] = con_hist
                if neu_hist: reports["final_trade_decision_neu"] = neu_hist
                if judge: reports["final_trade_decision_judge"] = judge

            update_ui()
            trace.append(chunk)

        final_state = trace[-1]
        decision = graph.process_signal(final_state.get("final_trade_decision", ""))

        st.success("Analysis Complete!")
        st.subheader("Final Decision")
        st.markdown(decision)
