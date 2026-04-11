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

The architecture should define two screening statuses:

* no issue  
* flag for deep analysis

These should mean:

1. No issue  
    The stock does not require further action from that analyst on that day.  
2. Flag for deep analysis  
    The stock should be considered for inclusion in the shared deep-analysis set for that day.

These statuses should be stored as structured screening outputs so that the screening logic is visible and comparable across configurations.

10. **Shared deep-analysis set**

After screening, the system should create one shared deep-analysis set for the day. This set ensures that all analysts perform deeper analysis on the same stocks on the same date, which is necessary for consistency across configurations.

The shared deep-analysis set should consist of:

* all current holdings  
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
12. **Memory design**

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

13. **Memory retrieval logic**

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
14. **Weekly summaries**

Every five trading days, each analyst should generate a structured weekly summary.

These summaries should be stored in Supabase and may later be retrieved as part of the context for future daily decisions. Their purpose is to create continuity and broader context without replacing the daily evidence-driven analysis.

15. **Debate architecture**

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

16. **Challenger architecture**

The challenger mechanism should be implemented as a separate portfolio-manager challenge stage rather than as a hidden behavior inside the final decision node.

In challenger configurations, the portfolio manager first performs a PM-Challenge stage. In this stage, the portfolio manager reviews the analyst reports and produces structured challenge points, objections, or requests for clarification directed back to the original analyst.

The challenged analyst then has one chance to:

* respond  
* clarify  
* revise its reasoning

Only after that does the workflow proceed to the final PM-Decision node, where the portfolio manager makes the final portfolio decision.

This design preserves the logic of the challenger as a distinct resilience mechanism and makes the interaction visible in the logs.

17. **Combined debate and challenger configuration**

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

18. **Schema enforcement**

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
19. **Configuration consistency**

All four configurations should share the same core architecture up to the point where their mechanisms differ.

The following should remain consistent across configurations:

* daily package  
* screening process  
* shared deep-analysis set  
* core analyst roles  
* portfolio manager function

The difference between configurations should come only from whether debate and challenger steps are inserted into the workflow.

This is important for experimental comparability.

20. **Baseline-first implementation logic**

The architecture should be implemented in layers. The first layer should be the baseline system without challenger and without debate. That baseline should work for both:

* Day 1 initial portfolio construction  
* Day 2 onward ongoing management

Only after the baseline is functioning should the architecture be extended with:

* debate branches  
* challenger branches

This staged implementation approach reduces engineering risk and keeps the artifact defendable.

21. **Phase 3 summary**

The artifact architecture should use LangGraph-style workflow orchestration with local agent reasoning inside controlled nodes. The portfolio manager is the central synthesis and final decision node. The system uses one shared per-day workflow state, while persistent data and memory are stored in Supabase. Analysts first perform independent screening of the full DJIA daily package using the statuses no issue and flag for deep analysis. The system then builds one shared deep-analysis set consisting of current holdings and the union of newly flagged names. Analysts perform deeper analysis on that same stock set and produce initial full reports. Debate, when enabled, is implemented as a bounded peer-review and revision process. Challenger, when enabled, is implemented as a separate PM-Challenge stage before the final portfolio-manager decision. All major node outputs must follow strict schemas. The baseline architecture is implemented first and then extended with the resilience mechanisms.
