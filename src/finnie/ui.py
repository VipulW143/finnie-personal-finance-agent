"""Minimal Streamlit chat interface for Finnie's finance Q&A workflow."""

from math import isfinite

import streamlit as st

from finnie.workflow import build_workflow
from finnie.portfolio_ui import render_portfolio_view
from finnie.market_ui import render_market_view
from finnie.goals_ui import render_goals_view
from finnie.knowledge import (
    ARTICLES_DIR, category_of, load_sources, load_glossary, search_glossary,
)


st.set_page_config(page_title="Finnie Finance Tutor", page_icon="💰")
st.title("Finnie Finance Tutor")
st.caption(
    "Ask general personal-finance questions. Answers are educational, not "
    "individualized financial advice."
)


def get_workflow():
    """Keep one compiled workflow per browser session across Streamlit reruns."""
    workflow_version = 13
    if (
        "workflow" not in st.session_state
        or st.session_state.get("workflow_version") != workflow_version
    ):
        st.session_state.workflow = build_workflow()
        st.session_state.workflow_version = workflow_version
    return st.session_state.workflow


def clear_session_results():
    """Clear visible conversation and tool outputs for this browser session."""
    st.session_state.messages = []
    for key in (
        "portfolio_result", "goal_result", "market_result", "news_result",
        "tax_messages",
        "chat_messages",
    ):
        if key in st.session_state:
            del st.session_state[key]


def render_chat_answer(answer: str, route: str = ""):
    """Preserve currency in calculation results displayed inside Markdown chat."""
    answer = answer.replace("$", "\\$")
    st.markdown(answer)


if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.subheader("About Finnie")
    view = st.radio(
        "Choose a tool",
        [
            "Chat", "Finance Q&A", "Portfolio", "Goals", "Market", "News",
            "Tax Education", "Knowledge",
        ],
    )
    st.write(
        "Finnie provides general educational information, not individualized "
        "financial advice."
    )
    st.button(
        "Clear conversation and results",
        on_click=clear_session_results,
    )

if view in ("Chat", "Finance Q&A"):
    category = None
    if view == "Chat":
        st.header("Chat")
        st.caption("Ask across finance topics. Finnie selects a specialist for each question.")
    else:
        categories = sorted({category_of(source["topic"]) for source in load_sources()})
        selected_category = st.selectbox(
            "Search sources in", ["All topics"] + categories, key="qa_category"
        )
        category = None if selected_category == "All topics" else selected_category
    message_key = "chat_messages" if view == "Chat" else "messages"
    if message_key not in st.session_state:
        st.session_state[message_key] = []
    messages = st.session_state[message_key]
    for message in messages:
        with st.chat_message(message["role"]):
            if message.get("route"):
                st.caption(f"Route: {message['route']}")
            render_chat_answer(message["content"], message.get("route", ""))

    prompt = st.chat_input("Ask Finnie a finance question")
    if prompt:
        history = [dict(message) for message in messages[-12:]]
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Finnie is preparing an answer..."):
                result = get_workflow().invoke(
                    {"question": prompt, "auto_route": view == "Chat",
                     "history": history, "category": category}
                )
            answer = result["answer"]
            route = result["intent"]
            st.caption(f"Route: {route}")
            render_chat_answer(answer, route)

        messages.append({"role": "user", "content": prompt})
        messages.append(
            {"role": "assistant", "route": route, "content": answer}
        )
elif view == "Portfolio":
    render_portfolio_view(get_workflow)
elif view == "Goals":
    render_goals_view(get_workflow)
elif view == "Market":
    render_market_view(get_workflow)
elif view == "News":
    st.header("Financial news synthesis")
    st.write(
        "Search current reporting and get a short, cited summary. News may be "
        "incomplete or change; this view does not recommend investments."
    )
    with st.form("news_form"):
        news_query = st.text_input(
            "What financial topic should Finnie search?",
            placeholder="Example: latest Federal Reserve interest-rate news",
        )
        submitted = st.form_submit_button("Search and summarize")

    if submitted:
        if not news_query.strip():
            st.error("Enter a topic or question for the news search.")
        else:
            with st.spinner("Searching current financial news..."):
                result = get_workflow().invoke(
                    {
                        "question": news_query.strip(),
                        "news_query": news_query.strip(),
                    }
                )
            st.session_state.news_result = {
                "route": result["intent"],
                "answer": result["answer"],
            }

    news_result = st.session_state.get("news_result")
    if news_result:
        st.caption(f"Route: {news_result['route']}")
        if news_result["answer"].startswith("Could not synthesize"):
            st.error(news_result["answer"])
        else:
            st.markdown(news_result["answer"], unsafe_allow_html=False)
elif view == "Tax Education":
    st.header("Tax education")
    st.caption("Ask about taxes or change topics. Finnie selects the specialist for each message.")
    st.caption(
        "General U.S. federal tax education from IRS materials. Finnie cannot "
        "determine your personal filing obligation, eligibility, or tax bill."
    )
    if "tax_messages" not in st.session_state:
        st.session_state.tax_messages = []
    for message in st.session_state.tax_messages:
        with st.chat_message(message["role"]):
            if message.get("route"):
                st.caption(f"Route: {message['route']}")
            render_chat_answer(message["content"], message.get("route", ""))

    tax_prompt = st.chat_input("Ask a general U.S. federal tax question")
    if tax_prompt:
        tax_history = [
            dict(message) for message in st.session_state.tax_messages[-12:]
        ]
        st.session_state.tax_messages.append(
            {"role": "user", "content": tax_prompt}
        )
        with st.chat_message("user"):
            st.markdown(tax_prompt)
        with st.chat_message("assistant"):
            with st.spinner("Checking Finnie's IRS education sources..."):
                result = get_workflow().invoke(
                    {"question": tax_prompt, "auto_route": True,
                     "history": tax_history}
                )
            answer = result["answer"]
            route = result["intent"]
            st.caption(f"Route: {route}")
            render_chat_answer(answer, route)
        st.session_state.tax_messages.append(
            {"role": "assistant", "route": route, "content": answer}
        )
elif view == "Knowledge":
    st.header("Knowledge library")
    sources = load_sources()
    st.caption(
        f"{len(sources)} captured education sources. "
        "Browse the summaries and open their original sources."
    )
    glossary = load_glossary()
    st.caption(f"{len(glossary)} glossary terms. Definitions are separate from the article count.")
    browse = st.radio("Browse", ["Articles", "Glossary"], horizontal=True)
    if browse == "Articles":
        categories = sorted({category_of(source["topic"]) for source in sources})
        selected_category = st.selectbox(
            "Topic", ["All topics"] + categories, key="knowledge_category"
        )
        search = st.text_input("Search titles, publishers, or topics").strip().casefold()
        matches = [
            source for source in sources
            if (selected_category == "All topics"
                or category_of(source["topic"]) == selected_category)
            and (not search or search in " ".join(
                source[field] for field in ("title", "publisher", "topic")
            ).casefold())
        ]
        if not matches:
            st.info("No captured articles match your search.")
        for source in matches:
            with st.expander(source["title"]):
                st.caption(
                    f"{source['publisher']} | {source['topic']} | "
                    f"Reviewed {source.get('checked_on', 'date not recorded')}"
                )
                st.markdown(f"[Open original source]({source['url']})")
                st.markdown(
                    (ARTICLES_DIR / source["file"]).read_text(encoding="utf-8")
                    .replace("$", "\\$")
                )
    else:
        glossary_categories = sorted({category_of(entry["topic"]) for entry in glossary})
        glossary_category = st.selectbox(
            "Topic", ["All topics"] + glossary_categories, key="glossary_category"
        )
        glossary_query = st.text_input("Search terms or definitions", key="glossary_search")
        entries = search_glossary(glossary_query, glossary_category)
        st.caption(f"{len(entries)} matching terms")
        if not entries:
            st.info("No glossary terms match your search.")
        for entry in entries:
            with st.expander(entry["term"]):
                st.caption(entry["topic"])
                st.markdown(entry["definition"].replace("$", "\\$"))
                st.markdown(f"[Source: {entry['source_title']}]({entry['source_url']})")
