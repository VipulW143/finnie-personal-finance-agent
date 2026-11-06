# Goal risk context and projection chart — November 5, 2026

## Result and scope

Goals now collects optional comfort-with-losses context and shows a monthly projection at the entered nominal annual rate alongside the same contribution at 0% and a target reference line. A monthly table includes modeled growth/loss. The existing $199.74 monthly example is preserved.

Loss comfort is context for an educational explanation, not an assessment of the user's capacity to bear losses, investment suitability, or a way to select expected returns. Neither path models volatility, uncertain returns, or probability of reaching the goal. The 0% comparison is not a guaranteed minimum or worst case. No asset allocation or investment recommendation is generated.

## Exact code changes

### src/finnie/goals.py

- Added RISK_LABELS for not_specified, low, moderate, and high, plus a link to the existing SEC risk-tolerance source captured in the library.
- Added project_goal(goal), returning a structured report rather than formatted text. Required inputs are unchanged: target_amount, current_savings, years, annual_return. Optional risk_tolerance defaults to not_specified. Validation retains positive target, nonnegative current savings, whole years 1–100, nominal annual return greater than -0.99 and at most 1. Booleans, numeric strings, invalid risk labels, nonfinite amounts, overflow, and invalid outer input types are rejected.
- Added _factors(rate, months) to calculate growth and annuity factors using log1p/expm1. This avoids cancellation in (growth - 1) when the rate is very close to zero; exact zero still uses a separate branch. These Python standard-library functions add no dependency.
- Kept the convention annual_return / 12, end-of-month payments, and upward cent rounding. Added numeric-limit guards so extremely large inputs yield a readable ValueError instead of an overflow/crash.
- Added monthly rows from month 0 through the final month, using the same rounded contribution as the text estimate. Each row has month, balance, zero_return_balance, target, and modeled_growth. Modeled growth subtracts the starting savings and subsequent contributions from the projected balance; it can be negative.
- Added the zero-return endpoint and gap to the report. Both paths use the same starting savings and contribution; the 0% path does not recalculate a new payment.
- Added a distinct explanation for each loss-comfort label. The calculation is independent of that label. Source-supported context notes that time horizon and ability to bear losses matter; money needed sooner has less recovery time after declines.
- Kept calculate_monthly_contribution() as the public workflow entry point. It now formats project_goal() output, adding comparison amounts, the risk-context explanation, limits, and source URL. Even when no new payment is needed, it displays the zero monthly payment and projected endpoint explicitly.

### src/finnie/goals_ui.py — new

- Extracted the Goals form into render_goals_view(get_workflow).
- Preserved existing amount/year/return input labels and percentage-to-fraction conversion. Added a selectbox for optional loss comfort.
- Both the saved chart report and workflow response are based on project_goal(). As in Portfolio, the small deterministic report is calculated by the view and revalidated by the existing workflow formatter; workflow result contracts do not need new report fields.
- Added a three-line chart for entered-rate balance, same contribution at 0%, and target; the target is a reference amount, not an assertion that it must be met in every intermediate month.
- Added an expandable monthly table, explanatory labels for overlapping zero-rate paths, and a clickable SEC source link.
- Saved report and text together in goal_result. Reruns retain the last submitted chart, with a label reminding users to submit after editing. Invalid submissions replace the previous report so no stale chart remains next to the error. Existing Clear conversation and results removes the saved projection.

### src/finnie/ui.py

Imported render_goals_view and replaced the previous inline Goals branch with one call. Increased workflow_version from 12 to 13 to recreate the session workflow after the updated calculations/routing prompt are loaded. Other views remain unchanged.

### src/finnie/routing.py

Extended the model's goal-payload instructions to permit optional risk_tolerance only when the user explicitly supplies comfort with losses. Instructed the model never to infer/change annual_return from this label. Required goal inputs and deterministic validation remain unchanged. Natural-language extraction still depends on the configured router model; the Goals form sends explicit values without a router model call.

### Tests and documentation

- tests/test_goals.py: nine tests cover the original sample, independent recurrence comparison, chart/text agreement, zero and negative rates, upward rounding, the 12% nominal convention, risk/math independence, already-funded goals, near-zero rates, invalid inputs, numeric limits, and real workflow output parity.
- tests/test_goals_ui.py: two AppTest checks cover risk context, sample amounts, 61-row chart/table, persistence, reset, zero-rate overlapping paths, and invalid-result replacement.
- README.md and .agent/PLAN.md: current milestone, test evidence, progress estimate, and remaining work updated.
- No dependencies, market data, source articles, or embeddings changed. Direct goal calculations and chart generation do not make model/API calls.

## Formula and technical learning

Let T be the target, P current savings, n months, and r = nominal annual return / 12.

Growth factor g = (1 + r)^n.

Annuity factor A = ((1 + r)^n - 1) / r for nonzero r; A = n for zero r.

Required monthly payment = max(0, (T - P*g) / A), rounded upward to cents.

At month m, projected balance = P*(1+r)^m + rounded_payment*A_m.

At 0% return, balance = P + rounded_payment*m.

The implementation computes growth minus one with expm1(n*log1p(r)), retaining accuracy near zero. Summary endpoint and chart endpoint use the same calculation. Tests compare this closed-form result against the independent monthly recurrence balance_next = balance*(1+r) + payment.

## Verification

All 51 project tests pass. This is a test count, not 80% coverage evidence. No additional API usage was needed.

For target $20,000, current savings $5,000, five years, and 5% nominal annual return:

- Monthly contribution $199.74.
- Projected entered-rate endpoint $20,000.33.
- Same contribution at 0% endpoint $16,984.40.
- Zero-return shortfall $3,015.60.
- 61 monthly rows, including month 0 and month 60.

For the same amounts and years with 0% entered return, payment is $250.00 and both balance lines overlap, ending at $20,000.00. Changing loss comfort must not change either payment or chart paths.

The earlier $25,000 target / $5,000 start / 10-year / 12%-nominal example remains $36.95 monthly and $25,001.86 projected, preserving the already-explained rate convention.

## Learner acceptance

Restart Streamlit from the project directory:

```bash
python -m streamlit run src/finnie/ui.py
```

1. Open Goals. Keep target 20000, savings 5000, years 5, annual return 5. Select Low comfort and submit.
2. Check the sample amounts above, a three-line chart, and monthly projection table.
3. Change only comfort to High and submit. Explanatory text should change, but the payment and chart should remain the same.
4. Enter a 0% annual return and submit. Expect $250.00 monthly with overlapping balance paths.
5. Set the target to zero and submit. Expect a validation error without the old chart. Clear results removes the saved projection.

Overall planning estimate: approximately 84%, pending full-rubric evaluation. Main market-history display was confirmed with TSLA; cache-repeat/history-toggle learner checks remain unconfirmed. Goal context/chart implementation passes automated checks, with learner browser acceptance pending. Next milestone is systematic requirement/evaluation review: coverage measurement, routing/retrieval/calculation/failure-path evidence, performance checks, and final documentation/packaging. Demo preparation follows submission readiness.
