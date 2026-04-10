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
2. The system loads the current portfolio state, including existing holdings, weights, available cash, and recent actions.  
3. Each analyst performs a light screening of the full DJIA universe using the daily information package.  
4. Each analyst assigns screening outcomes to stocks using the statuses:  
   * no issue  
   * monitor  
   * flag for deeper analysis  
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
2. Monitor  
    The stock is noteworthy and may remain relevant for watchlist or candidate purposes, but it does not automatically enter deeper analysis on that day.  
3. Flag for deeper analysis  
    The stock should be considered for inclusion in the shared deep-analysis set for that day.  
4. Shared deep-analysis set

The system should not deeply analyze all 30 DJIA stocks every day, because that would add unnecessary cost and noise.

Instead, after screening, the system creates one shared deep-analysis set for the day. This set ensures that all analysts perform deeper analysis on the same stocks on the same date.

The shared deep-analysis set is built from:

* current holdings  
* active candidate-list names  
* the union of newly flagged names from any analyst

This preserves full-universe awareness while keeping the system manageable and consistent across configurations.

13. **Candidate logic**

The candidate list is a persistent and dynamic object. It is not the same thing as same-day analyst nominations.

The system may keep a stock on the candidate list across days, remove it later, or add new names over time.

Separately, each analyst may nominate up to 3 candidate stocks per day for portfolio consideration. These nominations are part of the daily analyst output, but they do not determine portfolio changes by themselves. The Portfolio Manager remains responsible for deciding whether those nominations affect the target portfolio.

14. **Initial reports**

An initial report does not mean a shallow report. It means the first full analyst report written:

* after deeper analysis  
* before any peer exposure in debate configurations

The initial report is already based on:

* the daily information package  
* deeper retrieved data for the shared deep-analysis set  
* the agent’s own relevant prior notes or summaries where allowed  
15. **Challenger logic**

The challenger should be implemented as a distinct workflow mechanism rather than as a hidden prompt change.

In practice, this means a portfolio-manager-led challenge stage is inserted after analyst reporting and before the final portfolio-manager decision.

Its purpose is to identify suspicious, weak, or potentially flawed reasoning before that reasoning is absorbed into the final portfolio decision.

The challenged analyst should have one chance to respond or revise before the final decision is made.

16. **Multi-Agent Debate logic**

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

17. **Combined configuration logic**

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

18. **Weekly summaries**

The system remains daily, but every five trading days each analyst should generate a short structured weekly summary.

These summaries are stored and can later be used as internal context in future daily decision cycles. This allows the system to build continuity and broader context without changing the operating frequency from daily to weekly.

19. **Portfolio output**

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

20. **Run definition**

One daily decision cycle is the core operational unit of the artifact.

One full run is one complete configuration executed across the full backtesting horizon, such as 180 or 365 trading days.

This means the thesis can compare four full runs, one for each configuration, while also analyzing what happens at the level of individual daily cycles.

21. **Simplified investment policy statement**

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

The artifact is a multi-agent autonomous paper-trading portfolio management system for the DJIA 30\. It operates on a daily basis in a controlled backtesting environment. It constructs an initial portfolio on Day 1 and manages that portfolio from Day 2 onward. The Portfolio Manager is always the final decision-maker. The four configurations differ only by whether a portfolio-manager-led challenger stage and multi-agent debate are enabled. The system uses structured outputs, allows cash holdings, uses a screening layer followed by a shared deep-analysis set, and produces both target allocations and action-ready trade instructions. One daily cycle is the operational unit, while one full backtest episode for one configuration is the experimental run.

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

**PHASE 3 — ARCHITECTURE DESIGN**

1. **Architecture overview**

The artifact should be implemented as a workflow-driven multi-agent system with stateful orchestration. The architecture should use LangGraph-style orchestration as the main control layer, while LangChain-style components may still be used inside individual steps where useful.

This choice fits the artifact because the system does not behave like a free-form agent conversation. Instead, it follows a controlled daily workflow with defined stages, conditional branches, and limited iterative loops.

The architecture should therefore prioritize explicit workflow control over open-ended agent autonomy. Agents should reason locally within their assigned roles, but the overall order of execution, interaction logic, branching conditions, and stopping rules should be controlled by the workflow.

2. **Baseline architecture logic**

The baseline architecture should be implemented first and treated as the core system. It must support both:

* Day 1 initial portfolio construction  
* Day 2 onward ongoing portfolio management

The baseline daily cycle should work as follows:

1. The system loads the end-of-day daily information package for the full DJIA 30 universe and the current portfolio state.  
2. Each analyst performs a light first-pass screening of the full daily package from its own perspective.  
3. The system aggregates screening outputs and defines the shared deep-analysis set for the day.  
4. Each analyst retrieves deeper data only for the shared deep-analysis set and produces an initial full report.  
5. The portfolio manager synthesizes the analyst reports and produces the final portfolio decision.  
6. The execution layer translates the target portfolio decision into action-ready simulated trades.  
7. The system stores outputs, updated state, and relevant notes in the database.

This baseline should remain the architectural reference point for the extended configurations.

3. **Workflow control principle**

The overall system should be workflow-driven with local agency.

This means:

* the workflow decides which step happens next  
* the workflow decides which node runs  
* the workflow controls what data is available to each node  
* the workflow controls when the process stops

Agents retain local reasoning autonomy inside their own role-specific step, but they do not control the overall routing of the system.

This is important for comparability, reproducibility, and auditability. It keeps the experiment focused on the resilience mechanisms rather than on uncontrolled differences in agent behavior.

4. **Portfolio manager role**

The portfolio manager should be the central synthesis node and the final decision-maker in the architecture.

The analyst agents provide:

* specialized assessments  
* candidate nominations  
* structured reasoning from their own perspective

The portfolio manager is responsible for:

* combining those inputs with the current portfolio state  
* producing the final target portfolio  
* producing final trade actions

This makes the decision authority explicit and keeps the architecture close to a credible portfolio-management process.

5. **Node concept**

In this architecture, a node is one defined workflow step.

A node is not necessarily the same as a whole agent identity. The same conceptual agent may appear in more than one node if it performs different tasks at different stages.

For example:

* news analyst initial-report node  
* news analyst revision node

This is still the same agent role, but in two different workflow steps.

6. **State design**

The system should use one shared workflow state for each trading day. This daily graph state is the temporary working object that moves through the workflow during that one daily cycle.

It should contain the information needed to coordinate the daily run, but it should not be treated as the full persistent database.

The daily graph state should include, at minimum:

* trading date  
* active configuration  
* references to the daily information package  
* current portfolio state  
* screening outputs  
* shared deep-analysis set  
* analyst reports  
* debate-stage outputs where applicable  
* challenger outputs where applicable  
* portfolio manager decision  
* trade instruction outputs

Although the workflow uses a shared state object, visibility into that state should be controlled by node. In the baseline configuration, analysts should not see each other’s reports before submitting their own initial outputs.

Shared workflow state does not mean unrestricted access by all agents.

7. **Database and persistent storage**

Persistent data should remain in Supabase rather than inside the workflow state.

Supabase should store:

* raw and transformed market data  
* news data  
* manipulated news records  
* daily packages  
* stock notes  
* weekly summaries  
* candidate status history  
* portfolio history  
* run logs  
* evaluation records

The graph state should only carry the working state for the current daily run. This separation keeps the orchestration clean and the storage layer stable and replayable.

8. **Controlled data access**

Agents should not have unrestricted access to all available system data. Instead, each agent should access only the database views, retrieval functions, and data structures relevant to its role.

The news analyst should access:

* news-related daily package fields  
* selected market-wide news context  
* allowed prior news notes

The fundamental analyst should access:

* relevant fundamental snapshots  
* filing or macro context  
* allowed prior fundamental notes

The technical analyst should access:

* price and technical indicator history  
* technical signal fields  
* allowed prior technical notes

The portfolio manager should access:

* finalized analyst outputs  
* current portfolio state  
* selected recent summaries or notes  
* challenger output where applicable

This controlled access structure is important for both methodological clarity and implementation discipline.

9. **Screening layer and screening statuses**

The daily information package should serve as the broad screening layer across the DJIA 30\. It is not the full deep analysis. Its purpose is to help each analyst identify which stocks deserve further attention from that analyst’s perspective.

The architecture should define three screening statuses:

* no issue  
* monitor  
* flag for deeper analysis

These should mean:

1. No issue  
    The stock does not require further action from that analyst on that day.  
2. Monitor  
    The stock is noteworthy and may remain relevant for watchlist or candidate purposes, but it does not automatically enter deeper analysis on that day.  
3. Flag for deeper analysis  
    The stock should be considered for inclusion in the shared deep-analysis set for that day.

These statuses should be stored as structured screening outputs so that the screening logic is visible and comparable across configurations.

10. **Shared deep-analysis set**

After screening, the system should create one shared deep-analysis set for the day. This set ensures that all analysts perform deeper analysis on the same stocks on the same date, which is necessary for consistency across configurations.

The shared deep-analysis set should consist of:

* all current holdings  
* all active candidate-list names  
* the union of newly flagged names from any analyst during the daily screening step

For every flagged stock, the system should also store:

* which analyst flagged it  
* the trigger reason for that flag  
* whether multiple analysts flagged it

This architecture preserves analyst specialization during screening while ensuring unified deeper analysis afterward.

11. **Deep analysis and initial reports**

Once the shared deep-analysis set has been created, each analyst retrieves deeper role-specific data for that same stock set and produces its first full report for the day.

In this design, an initial report does not mean a shallow report. It means the first full analyst report written:

* after deeper analysis  
* before any peer exposure in debate configurations

The initial report is already based on:

* today’s daily package  
* deeper retrieved data  
* the agent’s own relevant prior notes where allowed  
12. **Candidate logic**

Each analyst may nominate up to three candidate stocks per day for portfolio consideration. These nominations are part of the analyst output, but they do not determine portfolio changes by themselves. The portfolio manager remains responsible for deciding whether those nominations affect the target portfolio.

The candidate list should remain dynamic over time. Stocks may:

* enter the candidate list  
* remain on the candidate list  
* leave the candidate list

The architecture should therefore support candidate-status persistence in the database rather than relying only on same-day nominations.

13. **Memory design**

Persistent memory should be implemented through structured records stored in Supabase, not through an unrestricted shared memory space.

Each analyst should maintain its own role-specific persistent notes and summaries. These should include:

* stock-level notes where deeper analysis took place  
* periodic weekly summaries

The portfolio manager should also produce persistent decision records.

The memory design should follow a latest-snapshot-plus-history approach. This means the system keeps:

* a current structured note for fast retrieval  
* a historical trail of prior notes for traceability

Each updated note should contain:

* the analyst’s current stance  
* what changed since the previous note  
* what remains important from earlier analysis  
* what should be monitored next

This allows continuity without turning memory into an uncontrolled text archive.

14. **Memory retrieval logic**

Memory retrieval should begin as structured database retrieval rather than embedding-based vector search.

Because the relevant records are already structured by:

* stock  
* agent  
* date  
* note type

they can be retrieved directly through normal database queries.

At the initial implementation stage, the system does not require full semantic RAG or vectorized memory retrieval. If a later version requires more flexible retrieval over larger amounts of unstructured text, that can be added later, but it is not necessary for the first architecture.

By default:

* analysts should retrieve their own prior notes and summaries  
* analysts should not retrieve broad peer memory  
* peer visibility should occur only through explicitly defined interaction stages, such as debate  
* the portfolio manager may retrieve a broader set of current analyst outputs and selected recent summaries where useful  
15. **Weekly summaries**

Every five trading days, each analyst should generate a structured weekly summary.

These summaries should be stored in Supabase and may later be retrieved as part of the context for future daily decisions. Their purpose is to create continuity and broader context without replacing the daily evidence-driven analysis.

16. **Debate architecture**

Recurrent discussion should be implemented as a bounded peer-based debate process rather than as unrestricted conversation. Debate should happen only:

* after the shared deep-analysis set has been created  
* after the analysts have produced their initial full reports

The debate structure should be:

1. Initial report  
2. Peer review  
3. Revised final report with response fields  
4. Portfolio manager review

In the peer review stage, the other analysts respond from their own perspective by providing structured cross-perspective feedback. This may include:

* agreements  
* disagreements  
* missing-risk flags  
* alternative interpretations  
* constructive questions

The original analyst then produces a revised final report that includes explicit response fields showing:

* which peer points were accepted  
* which peer points were rejected  
* which peer points were partially incorporated  
* how the recommendation changed, if at all  
* how the confidence changed, if at all  
* how the rationale changed, if at all

This design keeps debate iterative and meaningful, while still bounded and auditable. It also keeps debate clearly distinct from challenger logic.

17. **Challenger architecture**

The challenger mechanism should be implemented as a separate portfolio-manager challenge stage rather than as a hidden behavior inside the final decision node.

In challenger configurations, the portfolio manager first performs a PM-Challenge stage. In this stage, the portfolio manager reviews the analyst reports and produces structured challenge points, objections, or requests for clarification directed back to the original analyst.

The challenged analyst then has one chance to:

* respond  
* clarify  
* revise its reasoning

Only after that does the workflow proceed to the final PM-Decision node, where the portfolio manager makes the final portfolio decision.

This design preserves the logic of the challenger as a distinct resilience mechanism and makes the interaction visible in the logs.

18. **Combined debate and challenger configuration**

The architecture should also support the combined configuration where recurrent discussion and challenger are both enabled.

In that case, the order should be:

1. Screening  
2. Shared deep-analysis set creation  
3. Deep analysis  
4. Initial analyst reports  
5. Peer review  
6. Revised final analyst reports  
7. PM-Challenge  
8. Analyst challenge response or revision  
9. PM-Decision

This order is consistent across configurations and preserves a clean interpretation of the mechanisms. Debate improves the analyst reports first, and then the portfolio-manager challenger stage reviews those revised reports before the final decision.

19. **Schema enforcement**

All major node outputs should be governed by strict schemas.

A schema is the required structured format that defines:

* what fields an output must contain  
* what type of values those fields may hold

In this architecture, schema compliance should be treated as a hard requirement rather than a soft preference.

This means:

1. a node produces a structured output  
2. the system validates it  
3. if needed, the system repairs or retries  
4. only then does the workflow continue

This is necessary for:

* reliable storage  
* reproducibility  
* execution logic  
* later evaluation  
20. **Configuration consistency**

All four configurations should share the same core architecture up to the point where their mechanisms differ.

The following should remain consistent across configurations:

* daily package  
* screening process  
* shared deep-analysis set  
* core analyst roles  
* portfolio manager function

The difference between configurations should come only from whether debate and challenger steps are inserted into the workflow.

This is important for experimental comparability.

21. **Baseline-first implementation logic**

The architecture should be implemented in layers. The first layer should be the baseline system without challenger and without debate. That baseline should work for both:

* Day 1 initial portfolio construction  
* Day 2 onward ongoing management

Only after the baseline is functioning should the architecture be extended with:

* debate branches  
* challenger branches

This staged implementation approach reduces engineering risk and keeps the artifact defendable.

22. **Phase 3 summary**

The artifact architecture should use LangGraph-style workflow orchestration with local agent reasoning inside controlled nodes. The portfolio manager is the central synthesis and final decision node. The system uses one shared per-day workflow state, while persistent data and memory are stored in Supabase. Analysts first perform independent screening of the full DJIA daily package using the statuses no issue, monitor, and flag for deeper analysis. The system then builds one shared deep-analysis set consisting of holdings, active candidates, and the union of newly flagged names. Analysts perform deeper analysis on that same stock set and produce initial full reports. Debate, when enabled, is implemented as a bounded peer-review and revision process. Challenger, when enabled, is implemented as a separate PM-Challenge stage before the final portfolio-manager decision. All major node outputs must follow strict schemas. The baseline architecture is implemented first and then extended with the resilience mechanisms.

