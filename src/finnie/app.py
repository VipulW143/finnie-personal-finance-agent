import json

from finnie.config import get_settings
from finnie.workflow import build_workflow


def main():
    settings = get_settings()
    print(
        f"Finnie is ready ({settings['environment']} mode; "
        f"provider: {settings['provider']})."
    )

    workflow = None
    history: list[dict[str, str]] = []
    while True:
        user_input = input(
            "Ask Finnie a finance question, 'news <topic>', 'tax <question>', "
            "or type 'quit': "
        ).strip()

        if not user_input:
            print("Please enter a question.")
            continue

        if user_input.lower() == "quit":
            print("Goodbye!")
            break

        request: dict[str, object] = {
            "question": user_input, "auto_route": True, "history": history[-12:]
        }
        if user_input.lower().startswith("portfolio "):
            try:
                holdings = json.loads(user_input[len("portfolio "):])
            except json.JSONDecodeError:
                print(
                    "For portfolio analysis, enter 'portfolio ' followed by a "
                    "JSON list of holdings."
                )
                continue
            if not isinstance(holdings, list) or not all(
                isinstance(holding, dict) for holding in holdings
            ):
                print("Portfolio data must be a JSON list of holding objects.")
                continue
            request["portfolio"] = holdings
        elif user_input.lower().startswith("goal "):
            try:
                goal = json.loads(user_input[len("goal "):])
            except json.JSONDecodeError:
                print(
                    "For goal planning, enter 'goal ' followed by a JSON "
                    "object with target_amount, current_savings, years, "
                    "and annual_return."
                )
                continue
            if not isinstance(goal, dict):
                print("Goal details must be a JSON object.")
                continue
            request["goal"] = goal
        elif user_input.lower().startswith("market "):
            symbol = user_input[len("market "):].strip()
            if not symbol:
                print("Enter a ticker symbol after 'market'.")
                continue
            request["market_symbol"] = symbol
        elif user_input.lower() == "news" or user_input.lower().startswith("news "):
            query = user_input[len("news"):].strip()
            if not query:
                print("Enter a topic after 'news'.")
                continue
            request["news_query"] = query
        elif user_input.lower() == "tax" or user_input.lower().startswith("tax "):
            tax_question = user_input[len("tax"):].strip()
            if not tax_question:
                print("Enter a tax education question after 'tax'.")
                continue
            request["tax_question"] = tax_question
            request["question"] = tax_question

        if workflow is None:
            workflow = build_workflow()

        result = workflow.invoke(request)
        print(f"Route: {result['intent']}")
        print(result["answer"])
        history.extend([
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": result["answer"]},
        ])
        history = history[-12:]


if __name__ == "__main__":
    main()
