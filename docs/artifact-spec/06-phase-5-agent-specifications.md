**PHASE 5 — AGENT SPECIFICATIONS**

1. **Purpose of this phase**

This phase defines the operational contract for each agent role in the artifact. The goal is to make each role explicit, bounded, and easy to implement inside the workflow.

Each agent specification should answer:

* what the agent is responsible for  
* when the agent acts  
* what information it receives  
* what tools it may use  
* what constraints limit its behavior  
* what structured output it must return  
* how its output is handed off to the next stage

In this architecture, the specialist analysts are not independent end-to-end decision-makers. They are role-bounded contributors to a controlled portfolio-management workflow. The Portfolio Manager remains the final decision-maker.

2. **Shared agent rules**

The following rules should apply to the specialist analysts unless a later phase explicitly overrides them:

* analysts screen the full DJIA 30 every trading day using only the daily screening package for day *t*  
* analysts do not decide portfolio actions directly  
* analysts do not execute trades  
* analysts do not change the workflow order  
* analysts only perform deep analysis on the shared deep-analysis set for day *t*  
* tool use during deep analysis must be point-in-time bounded to day *t*  
* in the baseline configuration, analysts do not see peer reports before submitting their own initial deep-analysis report  
* screening outputs must use only the statuses `no_issue` and `flag_for_deep_analysis`

The shared deep-analysis set for day *t* should consist of:

* all current holdings  
* the union of newly flagged names from the daily screening step

3. **News Analyst**

**Role**

The News Analyst is responsible for interpreting stock-specific and market-wide news from the perspective of possible portfolio relevance. Its role is not general sentiment scoring in the abstract, but evidence-based identification and explanation of news that may affect holdings or newly flagged names.

**When it acts**

The News Analyst acts in two stages:

1. daily screening of all 30 DJIA stocks  
2. deep analysis of the shared deep-analysis set

**Exact inputs during screening**

For day *t*, the News Analyst should receive:

* the News Analyst screening package rows for all DJIA stocks for day *t*  
* the day-*t* shared general-news context row

The stock-level screening package should include:

* package date  
* ticker  
* price close  
* selected daily percentage price-change fields  
* latest stock-news ID  
* latest stock-news title  
* daily stock-news count

The shared context should include:

* latest general-news item for the day  
* daily general-news count

In disinformation conditions, the News Analyst should still receive the same package schema. The only difference is that the stock-specific news item may come from the manipulated stock-news path rather than the clean stock-news path. The News Analyst should not be told that the source was manipulated.

**Allowed tools during deep analysis**

The News Analyst should be allowed to call:

* `get_price_snapshot`  
* `retrieve_stock_news`  
* `get_all_general_news`

These tools should be constructed with a fixed day-*t* boundary so that the News Analyst cannot retrieve future data.

**Constraints**

The News Analyst should:

* reason only from the information allowed for day *t*  
* not infer portfolio actions directly  
* not read peer analyst reports before allowed workflow stages  
* not see metadata revealing that a stock-news article was manipulated  
* treat general news as market context, not as stock-specific evidence unless clearly connected

**Screening output**

For each stock, the News Analyst should return:

* screening status  
* short trigger reason  
* short rationale

The only allowed statuses are:

* `no_issue`  
* `flag_for_deep_analysis`

**Deep-analysis output**

For each stock in the shared deep-analysis set, the News Analyst should return a full structured report containing, at minimum:

* ticker  
* role-level recommendation  
* confidence  
* rationale  
* key evidence used  
* any important uncertainty or contradiction

The role-level recommendation should use a standardized categorical field shared across the specialist analysts:

* `bullish`  
* `neutral`  
* `bearish`  
* `inconclusive`

**Handoff logic**

During screening, the News Analyst hands off structured stock-level screening results to the workflow.  
During deep analysis, the News Analyst hands off a full analyst report to the Portfolio Manager, and to debate or challenge stages where enabled.

**Contribution to evaluation**

The News Analyst is the primary entry point for disinformation exposure in the artifact. Its outputs are therefore central for evaluating:

* whether manipulated stock news changed screening behavior  
* whether manipulated stock news changed deep-analysis reasoning  
* whether those changes propagated into later portfolio decisions

4. **Fundamental Analyst**

**Role**

The Fundamental Analyst is responsible for interpreting firm-level financial condition, valuation context, filing visibility, and macroeconomic context from the perspective of portfolio management.

**When it acts**

The Fundamental Analyst acts in two stages:

1. daily screening of all 30 DJIA stocks  
2. deep analysis of the shared deep-analysis set

**Exact inputs during screening**

For day *t*, the Fundamental Analyst should receive:

* the Fundamental Analyst screening package rows for all DJIA stocks for day *t*  
* the day-*t* shared inflation or macro context row

The stock-level screening package should include:

* package date  
* ticker  
* price close  
* selected daily percentage price-change fields  
* latest visible fundamental period end date  
* corresponding fundamental filing date  
* filing flag  
* filing form  
* price-to-earnings  
* price-to-sales

The shared macro context should include:

* inflation rate

The fundamental period should only be visible if its filing date is on or before the package date. This keeps the screening layer point-in-time correct.

**Allowed tools during deep analysis**

The Fundamental Analyst should be allowed to call:

* `get_price_snapshot`  
* `get_financial_ratios`  
* `get_latest_economic_indicators`  
* `search_filings`

These tools should all be bounded to day *t*.

**Constraints**

The Fundamental Analyst should:

* use only filed or otherwise visible information available by day *t*  
* not use future knowledge of later filings or later revisions  
* not infer portfolio actions directly  
* not read peer analyst reports before allowed workflow stages  
* treat filing-linked retrieval as deep-analysis input, not as unrestricted memory search

**Screening output**

For each stock, the Fundamental Analyst should return:

* screening status  
* short trigger reason  
* short rationale

The only allowed statuses are:

* `no_issue`  
* `flag_for_deep_analysis`

**Deep-analysis output**

For each stock in the shared deep-analysis set, the Fundamental Analyst should return a full structured report containing, at minimum:

* ticker  
* role-level recommendation  
* confidence  
* rationale  
* key financial or filing evidence used  
* any important uncertainty or contradiction

The role-level recommendation should use the shared specialist-analyst categories:

* `bullish`  
* `neutral`  
* `bearish`  
* `inconclusive`

**Handoff logic**

During screening, the Fundamental Analyst hands off structured stock-level screening results to the workflow.  
During deep analysis, the Fundamental Analyst hands off a full analyst report to the Portfolio Manager, and to debate or challenge stages where enabled.

**Contribution to evaluation**

The Fundamental Analyst helps show whether:

* the system remains grounded in filed financial evidence  
* manipulated news can indirectly distort interpretation of otherwise stable fundamentals  
* resilience mechanisms reduce propagation of weak or poorly supported narratives

5. **Technical Analyst**

**Role**

The Technical Analyst is responsible for interpreting price behavior and technical-indicator movement from the perspective of short-term market structure, momentum, and abnormal movement.

**When it acts**

The Technical Analyst acts in two stages:

1. daily screening of all 30 DJIA stocks  
2. deep analysis of the shared deep-analysis set

**Exact inputs during screening**

For day *t*, the Technical Analyst should receive the Technical Analyst screening package rows for all DJIA stocks for day *t*.

The stock-level screening package should include:

* package date  
* ticker  
* price close  
* volume  
* selected daily percentage price-change fields  
* selected daily changes in technical indicators

The current baseline set of technical screening indicators should remain compact and should focus on changes rather than an overly large raw indicator surface.

**Allowed tools during deep analysis**

The Technical Analyst should be allowed to call:

* `get_price_snapshot`  
* `get_technical_indicators`

These tools should be bounded to day *t*.

**Constraints**

The Technical Analyst should:

* focus on price action and technical structure, not on filing interpretation or broad macro reasoning  
* not infer portfolio actions directly  
* not read peer analyst reports before allowed workflow stages  
* keep reasoning tied to observable market and indicator behavior

**Screening output**

For each stock, the Technical Analyst should return:

* screening status  
* short trigger reason  
* short rationale

The only allowed statuses are:

* `no_issue`  
* `flag_for_deep_analysis`

**Deep-analysis output**

For each stock in the shared deep-analysis set, the Technical Analyst should return a full structured report containing, at minimum:

* ticker  
* role-level recommendation  
* confidence  
* rationale  
* key price or indicator evidence used  
* any important uncertainty or contradiction

The role-level recommendation should use the shared specialist-analyst categories:

* `bullish`  
* `neutral`  
* `bearish`  
* `inconclusive`

**Handoff logic**

During screening, the Technical Analyst hands off structured stock-level screening results to the workflow.  
During deep analysis, the Technical Analyst hands off a full analyst report to the Portfolio Manager, and to debate or challenge stages where enabled.

**Contribution to evaluation**

The Technical Analyst helps show whether:

* the system reacts appropriately to market movement  
* the system can distinguish between ordinary noise and meaningful technical change  
* resilience mechanisms reduce overreaction to narratives not supported by price behavior

6. **Portfolio Manager**

**Role**

The Portfolio Manager is the central synthesis node and always the final decision-maker. It is responsible for converting analyst outputs and current portfolio context into one final portfolio decision for the day.

**When it acts**

The Portfolio Manager acts after the analysts have completed deep analysis and produced their initial reports.  
In extended configurations, it may also act in a challenge stage before the final decision.

**Exact inputs**

For day *t*, the Portfolio Manager should receive:

* current portfolio state  
* the shared deep-analysis set  
* the finalized deep-analysis reports from the News Analyst, Fundamental Analyst, and Technical Analyst  
* selected prior notes or summaries where allowed  
* debate-stage outputs where applicable  
* challenge-stage outputs where applicable

The current portfolio state should include, at minimum:

* current holdings  
* quantities or shares  
* current position values  
* portfolio weights  
* available cash  
* selected recent actions where relevant

**Allowed tools**

The Portfolio Manager should have bounded portfolio-management tools rather than unrestricted retrieval access.

At minimum, the Portfolio Manager should have access to:

* `get_price_snapshot`  
* a portfolio-history tool  
* an IPS or compliance-checking tool  
* a risk-management tool  
* a portfolio-preview tool that shows the projected portfolio state after a proposed decision

These tools should remain point-in-time bounded and should support portfolio-level decision-making rather than open-ended data exploration.

**Constraints**

The Portfolio Manager should:

* make the final daily decision after day *t* close  
* not use information outside the bounded workflow inputs for day *t*  
* remain responsible for total portfolio construction, adjustment, reduction, sale, purchase, rebalance, and cash holding  
* not delegate final authority to the analysts  
* produce a decision even on no-action days

**Output**

The Portfolio Manager should return a structured daily decision containing, at minimum:

* target portfolio state  
* action-ready trade instructions  
* rationale for key portfolio changes or no-change outcome  
* links to supporting analyst evidence

**Handoff logic**

The Portfolio Manager hands off:

* final daily portfolio decision  
* final trade instruction layer  
* persistent decision record for storage and later evaluation

**Contribution to evaluation**

The Portfolio Manager is the final integration point for evaluating whether:

* manipulated inputs changed the final decision  
* challenge or debate reduced propagation of weak reasoning  
* the system maintained portfolio-management discipline under disinformation conditions

7. **PM-Challenge stage**

**Role**

The PM-Challenge stage is a workflow mechanism led by the Portfolio Manager before the final PM decision in challenger configurations. It is not a separate independent investment agent.

Its purpose is to stress-test weak, suspicious, unsupported, or internally inconsistent analyst reasoning before the final decision is made.

**When it acts**

The PM-Challenge stage acts:

* after analyst initial reports  
* after debate revisions where debate is enabled  
* before the final Portfolio Manager decision

**Exact inputs**

The PM-Challenge stage should receive:

* current portfolio state  
* the relevant analyst reports for the day  
* any debate-stage revised reports where applicable

**Allowed tools**

In the baseline challenger design, the PM-Challenge stage should not need extra retrieval tools. It should challenge based on the already available analyst evidence and portfolio context.

**Constraints**

The PM-Challenge stage should:

* issue structured challenge points rather than free-form conversation  
* focus on weak evidence, contradiction, unsupported claims, overconfidence, or suspicious narrative influence  
* return challenge points to one analyst role at a time  
* allow one response or revision round before the final PM decision

If token or cost constraints later require a narrower challenger design, a defensible fallback is to restrict the PM-Challenge stage first to the News Analyst role, because that role is the primary disinformation exposure point.

**Output**

The PM-Challenge stage should produce a structured challenge output containing, at minimum:

* target analyst role  
* target stock  
* challenge point  
* reason for challenge  
* requested clarification or revision

**Handoff logic**

The PM-Challenge stage hands the structured challenge output back to the relevant analyst role. The revised analyst output then becomes an input to the final Portfolio Manager decision node.

**Contribution to evaluation**

The PM-Challenge stage supports evaluation of whether:

* weak reasoning can be identified before portfolio action  
* disinformation-driven narratives can be challenged and corrected  
* the challenger mechanism improves decision quality relative to the baseline

8. **Agent separation principle**

The specialist analysts should remain meaningfully distinct. Role overlap should be minimized so that the contribution of each role remains interpretable.

The intended separation is:

* News Analyst: event and narrative interpretation  
* Fundamental Analyst: filed financial and macro interpretation  
* Technical Analyst: price and technical-structure interpretation  
* Portfolio Manager: synthesis and portfolio-level decision

This separation improves:

* architectural clarity  
* implementation discipline  
* later evaluation of how influence propagates through the system

9. **Portfolio-state visibility for specialist analysts**

During deep analysis, specialist analysts should receive only a bounded subset of portfolio-state information rather than the full portfolio archive.

The allowed per-stock portfolio-state fields should be:

* `is_current_holding`  
* `current_position_weight`  
* `current_position_value`  
* `recent_action_for_stock`, if any

This gives the analysts enough portfolio context to interpret the importance of a stock without turning them into full portfolio-state controllers.
