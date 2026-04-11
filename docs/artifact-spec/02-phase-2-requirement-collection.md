**PHASE 2 — REQUIREMENT COLLECTION**

1. **Functional requirements**

The system shall operate on one daily portfolio-level decision cycle for each trading day in the backtest period.

The system shall produce a structured output for every trading day, including explicit no-action outcomes when no portfolio change is recommended.

The system shall manage the portfolio autonomously within the DJIA 30 universe. This includes:

* initial portfolio construction  
* ongoing review of holdings  
* addition of new positions  
* reduction or exit of positions  
* rebalancing  
* optional cash holding

The system shall use a two-level analysis process:

* first, a standardized daily information package for the full DJIA 30 universe  
* second, selective deeper analysis for a shared stock set

In the baseline configuration, analysts shall work independently and shall not see peer analyst reports before submitting their own initial outputs.

The system shall define screening outcomes using the statuses:

* no issue  
* monitor  
* flag for deeper analysis

The system shall create one shared deep-analysis set for each trading day.

The shared deep-analysis set shall consist of:

* current holdings  
* active candidate-list names  
* the union of newly flagged names from any analyst

The system shall treat current holdings as requiring regular deeper review.

The system shall maintain a dynamic candidate list rather than a fixed static shortlist.

Each analyst may nominate up to 3 candidate stocks per day for portfolio consideration.

The portfolio manager shall remain the final decision-maker and shall determine the final target portfolio and trade actions.

The system shall produce both:

* a full target portfolio state for the day  
* a corresponding action-ready trade instruction layer

2. **Resilience requirements**

The artifact shall support four comparable configurations:

* baseline  
* baseline plus challenger  
* baseline plus multi-agent debate  
* baseline plus challenger plus multi-agent debate

The challenger mechanism shall operate after analyst reporting and before the final portfolio-manager decision.

The challenger mechanism shall be implemented as a distinct portfolio-manager-led challenge stage rather than as an embedded prompt modification inside another agent.

The challenged analyst shall have one chance to respond or revise before the final decision is made.

Multi-agent debate shall be implemented as a controlled peer-based interaction process rather than unrestricted free-form conversation.

The debate process shall use the following structure:

* initial full report  
* peer review  
* revised final report with response fields

The revised final report shall include response fields showing which peer points were accepted, rejected, or partially incorporated.

The system shall support analysis of whether disinformation affected:

* the news analyst  
* later agent outputs  
* the portfolio manager decision  
* the final portfolio action

The combined configuration shall support the sequence:

* initial reports  
* peer review  
* revised final reports  
* portfolio-manager-led challenge stage  
* analyst challenge response or revision  
* final portfolio-manager decision

3. **Data requirements**

The system shall operate on stored and replayable data served from the controlled backtesting environment rather than directly from live APIs during evaluation runs.

The daily information package shall be based on an end-of-day snapshot for trading day t.

The daily information package shall include stock-level market data fields sufficient for daily review, such as:

* previous close  
* open  
* high  
* low  
* close  
* volume  
* selected price-change measures

The technical analyst input shall include selected technical indicator values as of day t close and their recent changes.

The fundamental analyst input shall include:

* the latest available point-in-time fundamental data  
* selected changes from prior available values  
* filing-related flags where available  
* relevant macroeconomic release context

The news analyst input shall include, for each stock:

* one selected headline  
* one summary of that selected news item  
* the daily news count

The news analyst may also receive relevant market-wide or macro-level news context, but macro news shall not be manipulated in the initial artifact version.

The system shall store and access current portfolio state each day, including:

* holdings  
* weights  
* cash  
* recent actions

The system shall store trigger reasons for why a stock entered deeper analysis on a given day.

The system shall store which analyst flagged each stock and whether multiple analysts flagged the same stock.

The system shall store persistent structured notes and summaries in the database to support continuity across days.

The system shall support a latest-snapshot-plus-history logic for persistent notes and summaries.

By default, analysts shall retrieve their own prior notes and summaries rather than unrestricted peer memory.

4. **Memory and retrieval requirements**

Persistent continuity across days shall be implemented through structured records stored in the database rather than through an unrestricted shared memory space.

Each analyst shall maintain its own role-specific persistent notes and summaries.

Persistent notes shall contain, at minimum:

* the analyst’s current stance  
* what changed since the previous note  
* what remains important from earlier analysis  
* what should be monitored next

The system shall keep:

* a current structured note for fast retrieval  
* a historical trail of prior notes for traceability

Memory retrieval shall begin as structured database retrieval rather than embedding-based vector search.

The first implementation shall not require full semantic RAG or vectorized memory retrieval.

5. **Disinformation requirements**

For the initial artifact version, disinformation shall be injected only into stock-specific news items presented to the news analyst.

Macro-level news may be included as contextual information, but it shall not be manipulated in the initial design.

The manipulated news items shall be stored in a controlled way that allows the researcher to trace:

* when the disinformation was applied  
* where it was applied  
* to which stock it was applied

The design shall support at least two disinformation severities per stock where feasible:

* a stronger high-impact false news case  
* a milder false news case

6. **Output and schema requirements**

All core agent outputs shall be structured and standardized.

The analyst outputs shall include recommendation fields, rationale fields, and confidence-related fields in a consistent format.

The system shall distinguish between:

* the full target portfolio state  
* the execution-oriented trade instruction layer

The portfolio output shall support paper trading by including the fields needed to translate the decision into simulated actions.

The system shall support explicit no-action outputs.

The system shall store the trigger reason for candidate selection or deeper analysis.

Weekly analyst summaries shall be generated every 5 trading days and stored as structured outputs.

The system shall use strict output schemas for major workflow steps so that outputs can be validated before the workflow continues.

The debate configuration shall use revised final reports with explicit response fields.

The challenger configuration shall use structured challenge messages and structured analyst responses or revisions.

7. **Transparency and auditability requirements**

The system shall log sufficient information to reconstruct how each daily decision was formed.

For each agent step, the system shall store:

* the date  
* the agent or workflow step identity  
* the input package reference  
* the task or question given to the agent  
* the structured output  
* the rationale fields  
* any peer review message, response field, challenge message, or revision where applicable

The logging design shall be sufficient to support coding of attack success at both:

* the individual agent level  
* the full system level

The system shall make it possible to identify whether manipulated news was:

* referenced  
* accepted  
* challenged  
* revised  
* propagated into the final decision

The system shall avoid relying only on uncontrolled raw text logs as the primary form of evidence.

8. **Comparability and experiment-control requirements**

Prompt templates shall remain fixed across configurations except where a change is explicitly required by the tested resilience mechanism.

Output schemas shall remain fixed across configurations except where a schema change is required by the presence of challenger or debate-related response fields.

Model versions and core generation settings shall remain fixed across configurations wherever possible.

The same stored data snapshot for each trading day shall be used across configurations.

The same screening logic and shared deep-analysis-set logic shall be used across configurations.

The Day 1 baseline portfolio shall be reused as the starting portfolio for all configurations to improve comparability.

When realism and comparability conflict, the design shall prefer the simpler and more controlled option unless additional realism is essential to preserve the portfolio-management logic.

9. **Execution and backtesting requirements**

The system shall make its decision after the market close of trading day t using information available up to that close.

Simulated trades shall be executed at the next trading day open, t+1.

The execution layer shall compare the current portfolio state with the target portfolio state and derive the required:

* buy  
* sell  
* reduce  
* increase  
* hold actions

The updated simulated portfolio state shall be stored and used as the current state input for the next daily decision cycle.

10. **Implementation constraints**

The artifact shall remain simple enough to defend in a business-school master thesis and shall avoid unnecessary engineering complexity.

The design shall prioritize structured outputs and strong workflow control over loosely governed prompt-only behavior.

The system shall remain within manageable token and compute limits by avoiding full deep analysis of all 30 DJIA stocks every day.

The design shall support a backtest horizon of either 180 or 365 trading days, depending on resource feasibility.

11. **Phase 2 summary**

The artifact requirements define a daily portfolio-level decision system with mandatory daily outputs, including no-action days. The system uses an end-of-day daily package for the full DJIA universe and then performs deeper analysis on a shared stock set consisting of holdings, active candidates, and newly flagged names. Each analyst may nominate up to 3 candidates per day, but the portfolio manager remains the final decision-maker. Disinformation is injected only through stock-specific news provided to the news analyst. Persistent continuity is handled through structured notes and summaries stored in the database, using current snapshots plus history rather than full vector RAG by default. All outputs and interactions must be structured, logged, and comparable across the four configurations. Decisions are made after day t close and executed at day t+1 open.
