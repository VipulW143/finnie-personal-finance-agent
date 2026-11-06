"""Route Finnie requests through an explicit, inspectable workflow."""

from typing import Literal, NotRequired, TypedDict, cast
import re

from langgraph.graph import END, START, StateGraph
from openai import OpenAIError

from finnie.portfolio import summarize_portfolio
from finnie.goals import calculate_monthly_contribution
from finnie.market_data import format_market_quote, get_market_quote
from finnie.market_history import get_market_history, format_market_history
from finnie.news import NewsSearchError, synthesize_financial_news
from finnie.rag import answer_with_sources, load_knowledge_base
from finnie.routing import resolve_request
from finnie.vector_store import VectorStore


FinanceIntent = Literal[
    "finance_qa", "portfolio_analysis", "goal_planning", "market_analysis",
    "news_synthesis", "tax_education", "clarification", "multi_agent",
]


class FinnieState(TypedDict):
    """Small pieces of data passed between workflow nodes."""

    question: str
    portfolio: NotRequired[list[dict[str, object]] | None]
    goal: NotRequired[dict[str, object] | None]
    market_symbol: NotRequired[str | None]
    market_history_days: NotRequired[int | None]
    market_history: NotRequired[dict | None]
    news_query: NotRequired[str | None]
    tax_question: NotRequired[str | None]
    intent: NotRequired[FinanceIntent]
    answer: NotRequired[str]
    auto_route: NotRequired[bool]
    history: NotRequired[list[dict[str, str]]]
    category: NotRequired[str | None]
    tasks: NotRequired[list[dict[str, object]]]
    task_index: NotRequired[int]
    task_results: NotRequired[list[dict[str, str]]]


def build_workflow():
    """Build the graph once and load embeddings only for RAG-based requests."""
    indexed_chunks: VectorStore | None = None

    def route_question(state: FinnieState) -> dict[str, object]:
        """Choose a capability from the explicit request type."""
        quote_request = re.fullmatch(
            r"(?:please\s+)?(?:get|show|fetch|what is|what's)\s+"
            r"(?:me\s+)?(?:the\s+)?(?:latest|current)\s+"
            r"(?:trade|quote|price)\s+(?:for|of)\s+"
            r"\$?([A-Za-z][A-Za-z0-9.-]{0,14})[?!.]*",
            state["question"].strip(),
            re.IGNORECASE,
        )
        if quote_request:
            return {
                "intent": "market_analysis",
                "market_symbol": quote_request.group(1).upper(),
            }
        if "portfolio" in state:
            return {"intent": "portfolio_analysis"}
        if "goal" in state:
            return {"intent": "goal_planning"}
        if "market_symbol" in state:
            return {"intent": "market_analysis"}
        if "news_query" in state:
            return {"intent": "news_synthesis"}
        if "tax_question" in state:
            return {"intent": "tax_education"}
        if state.get("auto_route"):
            return resolve_request(state["question"], state.get("history", []))
        return {"intent": "finance_qa"}

    def ensure_knowledge_base() -> VectorStore:
        nonlocal indexed_chunks
        if indexed_chunks is None:
            print("Loading Finnie's finance education source...")
            indexed_chunks = load_knowledge_base()
        return indexed_chunks

    def answer_finance_question(state: FinnieState) -> dict[str, str]:
        try:
            answer = answer_with_sources(
                state["question"], ensure_knowledge_base(), history=state.get("history"),
                category=state.get("category"),
            )
        except (OpenAIError, OSError):
            answer = "Finance education sources are temporarily unavailable. Please retry."
        return {"answer": answer}

    def educate_about_tax(state: FinnieState) -> dict[str, str]:
        question = state.get("tax_question", state["question"])
        try:
            answer = answer_with_sources(
                question, ensure_knowledge_base(), tax_education=True,
                history=state.get("history"),
            )
        except (OpenAIError, OSError):
            answer = "Tax education sources are temporarily unavailable. Please retry."
        return {"answer": answer}

    def synthesize_news(state: FinnieState) -> dict[str, str]:
        query = state.get("news_query", state["question"])
        try:
            return {"answer": synthesize_financial_news(query)}
        except (ValueError, NewsSearchError) as error:
            return {"answer": f"Could not synthesize current news: {error}"}

    def analyze_portfolio(state: FinnieState) -> dict[str, str]:
        holdings = state.get("portfolio")
        if holdings is None:
            return {"answer": "No portfolio holdings were provided."}
        try:
            return {"answer": summarize_portfolio(holdings)}
        except ValueError as error:
            return {"answer": f"Could not analyze the portfolio: {error}."}

    def plan_goal(state: FinnieState) -> dict[str, str]:
        goal = state.get("goal")
        if goal is None:
            return {"answer": "No goal details were provided."}
        try:
            return {"answer": calculate_monthly_contribution(goal)}
        except ValueError as error:
            return {"answer": f"Could not calculate the goal: {error}."}

    def analyze_market(state: FinnieState) -> dict:
        symbol = state.get("market_symbol")
        if symbol is None:
            return {"answer": "No ticker symbol was provided."}
        try:
            quote = get_market_quote(symbol)
        except ValueError as error:
            return {"answer": f"Could not retrieve a market quote: {error}."}
        answer = format_market_quote(quote)
        history = None
        if state.get("market_history_days") is not None:
            try:
                history = get_market_history(symbol, state["market_history_days"])
                answer += "\n\n" + format_market_history(history)
            except ValueError as error:
                answer += f"\n\nDaily price history unavailable: {error}."
        return {"answer": answer, "market_history": history}

    def choose_capability(state: FinnieState) -> FinanceIntent:
        # route_question always sets intent before this conditional edge runs.
        return cast(FinanceIntent, state["intent"])

    def dispatch_task(state: FinnieState) -> dict[str, object]:
        task = state["tasks"][state["task_index"]]
        # Clear request-specific fields before moving to another specialist.
        return {
            "portfolio": None, "goal": None, "market_symbol": None,
            "market_history_days": None, "market_history": None,
            "tax_question": None, "news_query": None, "answer": "",
            **task,
        }

    def collect_result(state: FinnieState) -> dict[str, object]:
        if not state.get("tasks"):
            return {}
        return {
            "task_results": state["task_results"] + [
                {"route": state["intent"], "answer": state["answer"]}
            ],
            "task_index": state["task_index"] + 1,
        }

    def next_step(state: FinnieState) -> str:
        if not state.get("tasks"):
            return END
        if state["task_index"] < len(state["tasks"]):
            return "dispatch_task"
        return "combine_results"

    def combine_results(state: FinnieState) -> dict[str, str]:
        titles = {
            "finance_qa": "Finance Q&A", "tax_education": "Tax Education",
            "goal_planning": "Goal Planning", "portfolio_analysis": "Portfolio Analysis",
            "market_analysis": "Market Analysis", "news_synthesis": "News Synthesis",
        }
        sections = [
            f"### {titles[result['route']]}\n\n{result['answer']}"
            for result in state["task_results"]
        ]
        return {"intent": "multi_agent", "answer": "\n\n".join(sections)}

    graph = StateGraph(FinnieState)
    graph.add_node("route_question", route_question)
    graph.add_node("finance_qa", answer_finance_question)
    graph.add_node("portfolio_analysis", analyze_portfolio)
    graph.add_node("goal_planning", plan_goal)
    graph.add_node("market_analysis", analyze_market)
    graph.add_node("news_synthesis", synthesize_news)
    graph.add_node("tax_education", educate_about_tax)
    graph.add_node("clarification", lambda state: {"answer": state["answer"]})
    graph.add_node("dispatch_task", dispatch_task)
    graph.add_node("collect_result", collect_result)
    graph.add_node("combine_results", combine_results)
    graph.add_edge(START, "route_question")
    graph.add_conditional_edges(
        "route_question",
        choose_capability,
        {
            "finance_qa": "finance_qa",
            "portfolio_analysis": "portfolio_analysis",
            "goal_planning": "goal_planning",
            "market_analysis": "market_analysis",
            "news_synthesis": "news_synthesis",
            "tax_education": "tax_education",
            "clarification": "clarification",
            "multi_agent": "dispatch_task",
        },
    )
    graph.add_conditional_edges("dispatch_task", choose_capability, {
        name: name for name in (
            "finance_qa", "portfolio_analysis", "goal_planning",
            "market_analysis", "news_synthesis", "tax_education",
        )
    })
    for name in (
        "finance_qa", "portfolio_analysis", "goal_planning",
        "market_analysis", "news_synthesis", "tax_education",
    ):
        graph.add_edge(name, "collect_result")
    graph.add_conditional_edges("collect_result", next_step, {
        END: END, "dispatch_task": "dispatch_task",
        "combine_results": "combine_results",
    })
    graph.add_edge("combine_results", END)
    graph.add_edge("clarification", END)
    return graph.compile()
