"""Goal inputs, loss-comfort context, and comparable monthly projection paths."""

import streamlit as st

from finnie.goals import RISK_LABELS, RISK_SOURCE, project_goal


def render_goals_view(get_workflow):
    st.header("Savings goal planning")
    st.write("Estimate a monthly contribution and explore how the result depends on the return assumption.")
    st.caption(
        "Nominal annual return is divided by 12: 12% means 1% monthly. "
        "Contributions occur at month end. These are educational projections."
    )
    with st.form("goal_form"):
        target = st.number_input("Target amount ($)", min_value=0.0, value=20000.0, step=1000.0)
        current = st.number_input("Current savings ($)", min_value=0.0, value=5000.0, step=500.0)
        years = st.number_input("Time horizon (years)", min_value=1, max_value=100, value=5, step=1)
        rate = st.number_input("Assumed annual return (%)", min_value=-98.99, max_value=100.0, value=5.0, step=0.5)
        risk = st.selectbox("Comfort with investment losses", list(RISK_LABELS), format_func=RISK_LABELS.get)
        st.caption("Your loss-comfort answer adds context. It does not choose an investment or a return assumption.")
        submitted = st.form_submit_button("Project savings goal")
    if submitted:
        goal = dict(target_amount=target, current_savings=current, years=int(years),
                    annual_return=rate / 100, risk_tolerance=risk)
        try:
            report = project_goal(goal)
            result = get_workflow().invoke({"question": "Savings goal projection", "goal": goal})
            error = result["answer"].startswith("Could not calculate")
            st.session_state.goal_result = dict(route=result["intent"], answer=result["answer"],
                                                is_error=error, report=None if error else report)
        except ValueError as error:
            st.session_state.goal_result = dict(route="goal_planning", is_error=True,
                                                answer=f"Could not calculate the goal: {error}.")
    result = st.session_state.get("goal_result")
    if not result:
        return
    st.caption(f"Route: {result['route']}")
    if result.get("is_error"):
        st.error(result["answer"])
        return
    st.text(result["answer"])
    st.markdown(f"[SEC: understanding risk tolerance and time horizon]({RISK_SOURCE})")
    report = result.get("report")
    if not report:
        return
    st.subheader("Last projected savings goal")
    st.caption("The chart uses the last submitted inputs. Submit again after editing the form.")
    st.line_chart([
        {"Month": row["month"], "Entered-rate balance ($)": row["balance"],
         "Same contribution at 0% ($)": row["zero_return_balance"], "Target ($)": row["target"]}
        for row in report["rows"]
    ], x="Month", y=["Entered-rate balance ($)", "Same contribution at 0% ($)", "Target ($)"])
    st.caption(
        "Both paths use the same rounded monthly contribution and starting savings. "
        "The 0% path is not a guaranteed floor; neither path models market fluctuations. "
        "At a 0% entered rate, the two balance lines overlap."
    )
    with st.expander("Monthly projection details"):
        st.dataframe([
            {"Month": row["month"], "Entered-rate balance ($)": row["balance"],
             "Same contribution at 0% ($)": row["zero_return_balance"],
             "Modeled growth / loss ($)": row["modeled_growth"], "Target ($)": row["target"]}
            for row in report["rows"]
        ], hide_index=True)
