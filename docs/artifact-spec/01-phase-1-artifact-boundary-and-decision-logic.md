**PHASE 1 — ARTIFACT BOUNDARY AND DECISION LOGIC**

1. **Artifact definition**

The artifact is a controlled multi-agent autonomous paper-trading portfolio management system operating in a backtesting environment. Its purpose is to simulate end-to-end portfolio management under normal and disinformation conditions and to allow comparison of resilience mechanisms across four system configurations.

The artifact itself is the decision-making system. It should be kept conceptually separate from:

* the supporting data pipeline  
* the backtesting and execution engine  
* the evaluation framework

These are supporting components, but they are not the artifact itself.

2. **System purpose**

The system is designed to manage a portfolio autonomously within a controlled environment. It does not only analyze stocks. It performs the full portfolio management flow, including:

* initial portfolio construction  
* daily portfolio review  
* selling and reducing positions  
* buying and adding positions  
* rebalancing  
* holding cash when needed  
* identifying new investment opportunities within the allowed universe  
3. Investment universe

The investable universe is limited to the Dow Jones Industrial Average. This means the system can invest only in the 30 DJIA stocks.

The portfolio itself will hold only a subset of those stocks rather than all 30 at once.

4. **Operating logic**

The system operates on a daily portfolio-level decision cycle.

* Day 1 is treated as initial portfolio construction.  
   On that day, the system selects a subset of DJIA stocks and assigns portfolio weights.  
* Day 2 onward is treated as ongoing portfolio management.  
   This includes reviewing current holdings, reacting to new information, reducing or exiting positions, adding new positions, rebalancing existing allocations, and optionally keeping part of the portfolio in cash.

The system should behave like an autonomous end-to-end paper-trading system based on stored and controlled data inputs.

5. **Core agents and decision authority**

The baseline system contains four main agents:

* News Analyst  
* Fundamental Analyst  
* Technical Analyst  
* Portfolio Manager

The analysts provide structured recommendations, confidence indications, and reasoning from their own perspective.

The Portfolio Manager is always the final decision-maker.

In some configurations, the workflow also includes:

* a portfolio-manager-led challenger stage  
* a bounded multi-agent debate process  
6. **Configurations**

The artifact consists of one core system implemented in four configurations:

1. Baseline  
2. Baseline plus Challenger  
3. Baseline plus Multi-Agent Debate  
4. Baseline plus Challenger plus Multi-Agent Debate  
5. What is fixed across all configurations

The following elements remain the same in all four configurations:

* the investable universe remains the DJIA 30  
* the system operates daily  
* Day 1 is always the initial portfolio construction step  
* Day 2 onward is always ongoing portfolio management  
* the Portfolio Manager is always the final decision-maker  
* the current portfolio state is always part of the system input  
* cash is always allowed  
* outputs are always structured and standardized  
* the system always operates in a controlled backtesting environment using stored data  
* the Day 1 portfolio produced by the baseline configuration is reused as the starting portfolio for all configurations


8. **What changes across configurations**

Only two resilience mechanisms vary across configurations:

* the presence or absence of a challenger stage  
* the presence or absence of multi-agent debate

In this design:

* Challenger means a portfolio-manager-led challenge step before the final decision  
* Multi-Agent Debate means a controlled peer-based interaction process among analysts before the final decision  
9. **Baseline independence principle**

In the baseline configuration, the analysts work independently. They do not see each other’s reports before submitting their own initial outputs to the Portfolio Manager.

Peer visibility occurs only in the debate configurations. This is important because it preserves a clean baseline and makes the effect of debate easier to interpret.

10. **Decision cycle**

One daily system cycle is defined as follows:

1. The system loads stored daily data for the current trading day.  
2. The system loads the current portfolio state, including existing holdings, quantities, position values, weights, available cash, and recent actions.  
3. Each analyst performs a light screening of the full DJIA universe using the daily information package.  
4. Each analyst assigns screening outcomes to stocks using the statuses:  
   * no issue  
   * flag for deep analysis  
5. The system defines one shared deep-analysis set for the day.  
6. The analysts perform deeper analysis on that shared stock set and produce initial full reports.  
7. In Multi-Agent Debate configurations, analysts review peer reports and submit revised final reports with response fields.  
8. In Challenger configurations, the portfolio-manager-led challenge step reviews analyst reports and sends structured challenge points back for response or revision.  
9. The Portfolio Manager produces the final portfolio decision.  
10. The paper-trading layer applies the decision.  
11. The system stores outputs, logs, updated state, and relevant notes.

12. **Screening logic**

The daily information package is the broad screening layer across the DJIA 30\. It is not the full deep analysis. Its purpose is to help each analyst identify which stocks deserve further attention from that analyst’s perspective.

The screening statuses mean:

1. No issue  
    The stock does not require further action from that analyst on that day.  
2. Flag for deep analysis  
    The stock should be considered for inclusion in the shared deep-analysis set for that day.  
4. Shared deep-analysis set

The system should not deeply analyze all 30 DJIA stocks every day, because that would add unnecessary cost and noise.

Instead, after screening, the system creates one shared deep-analysis set for the day. This set ensures that all analysts perform deeper analysis on the same stocks on the same date.

The shared deep-analysis set is built from:

* current holdings  
* the union of newly flagged names from any analyst

This preserves full-universe awareness while keeping the system manageable and consistent across configurations.

13. **Initial reports**

An initial report does not mean a shallow report. It means the first full analyst report written:

* after deeper analysis  
* before any peer exposure in debate configurations

The initial report is already based on:

* the daily information package  
* deeper retrieved data for the shared deep-analysis set  
* the agent’s own relevant prior notes or summaries where allowed  
14. **Challenger logic**

The challenger should be implemented as a distinct workflow mechanism rather than as a hidden prompt change.

In practice, this means a portfolio-manager-led challenge stage is inserted after analyst reporting and before the final portfolio-manager decision.

Its purpose is to identify suspicious, weak, or potentially flawed reasoning before that reasoning is absorbed into the final portfolio decision.

The challenged analyst should have one chance to respond or revise before the final decision is made.

15. **Multi-Agent Debate logic**

Multi-Agent Debate should not be implemented as free-form open conversation. That would be harder to control, harder to log, and harder to defend in the thesis.

Instead, it should follow a controlled peer-based structure:

1. each analyst produces an initial full report  
2. peer analysts review that report from their own perspective  
3. the original analyst submits a revised final report with response fields

The response fields should show, at minimum:

* which peer points were accepted  
* which peer points were rejected  
* which peer points were partially incorporated  
* whether recommendation, confidence, or rationale changed

There should be no majority vote among analysts, because the final decision authority belongs to the Portfolio Manager.

16. **Combined configuration logic**

When Challenger and Multi-Agent Debate are both enabled, the order should be:

1. screening  
2. shared deep-analysis set creation  
3. deeper analysis  
4. initial analyst reports  
5. peer review  
6. revised final analyst reports  
7. portfolio-manager-led challenge stage  
8. analyst challenge response or revision  
9. final portfolio-manager decision

This keeps the combined configuration consistent with the other three configurations.

17. **Weekly summaries**

The system remains daily, but every five trading days each analyst should generate a short structured weekly summary.

These summaries are stored and can later be used as internal context in future daily decision cycles. This allows the system to build continuity and broader context without changing the operating frequency from daily to weekly.

18. **Portfolio output**

The final daily output should include both:

* target portfolio state  
* action-ready paper-trading instructions

The target portfolio state should include:

* target holdings  
* target weights  
* cash allocation

The action-ready trading output should include:

* ticker  
* action type  
* current weight  
* target weight  
* reference price  
* rationale

This allows the decision output to be used both for portfolio comparison and for simulated execution.

19. **Run definition**

One daily decision cycle is the core operational unit of the artifact.

One full run is one complete configuration executed across the full backtesting horizon, such as 180 or 365 trading days.

This means the thesis can compare four full runs, one for each configuration, while also analyzing what happens at the level of individual daily cycles.

20. **Simplified investment policy statement**

At this stage, the system should use a simple and defendable investment policy framework.

The simplified IPS is:

* the portfolio is long-only  
* short selling is not allowed  
* the investable universe is restricted to the DJIA 30  
* the target number of holdings is between 5 and 10  
* the maximum allocation per stock is 15 percent  
* cash is allowed between 0 and 30 percent  
* sector caps are omitted for now to keep the design simpler  
* leverage is not allowed

These are initial design defaults and can still be refined later if needed.

22. **Phase 1 summary**

The artifact is a multi-agent autonomous paper-trading portfolio management system for the DJIA 30\. It operates on a daily basis in a controlled backtesting environment. It constructs an initial portfolio on Day 1 and manages that portfolio from Day 2 onward. The Portfolio Manager is always the final decision-maker. The four configurations differ only by whether a portfolio-manager-led challenger stage and multi-agent debate are enabled. The system uses structured outputs, allows cash holdings, uses a screening layer followed by a shared deep-analysis set built from current holdings and newly flagged names, and produces both target allocations and action-ready trade instructions. One daily cycle is the operational unit, while one full backtest episode for one configuration is the experimental run.
