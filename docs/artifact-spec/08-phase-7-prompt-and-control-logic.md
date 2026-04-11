**PHASE 7 — PROMPT AND CONTROL LOGIC**

1. **Purpose of this phase**

This phase defines how prompting and output control should work inside the workflow. The workflow remains the main architecture. Prompts exist to make each node behave correctly, stay within role boundaries, and return valid structured outputs.

The prompt layer should support the workflow by making each node:

* role-bounded  
* point-in-time correct  
* schema-compliant  
* easy to validate and repair

2. **Prompt layers**

Each node should use four prompt layers:

* `system prompt`  
* `role prompt`  
* `task prompt`  
* `schema instruction`

Each layer should have a clearly different job.

The intended distinction should be:

* `system prompt` = guardrails and output discipline  
* `role prompt` = role identity and analytical perspective  
* `task prompt` = the exact current workflow assignment  
* `schema instruction` = the exact required output format

3. **System prompts**

There should be:

* one shared `system prompt` for the three specialist analysts  
* one separate `system prompt` for the Portfolio Manager

The shared specialist-analyst system prompt should define:

* behavioral guardrails  
* role-boundary guardrails  
* output-discipline guardrails

In practical terms, the shared specialist-analyst system prompt should tell the model:

* operate only on the inputs and tool results provided by the workflow  
* do not invent evidence that is not present in those inputs or tool results  
* do not overstep into final portfolio-decision authority  
* return output only in the required structured format

The Portfolio Manager system prompt should define:

* behavioral guardrails  
* portfolio-decision guardrails  
* output-discipline guardrails

In practical terms, the Portfolio Manager system prompt should tell the model:

* operate only on the inputs and tool results provided by the workflow  
* stay within IPS, risk, and compliance constraints  
* do not invent execution arithmetic  
* return output only in the required structured format

The specialist analysts and the Portfolio Manager therefore need different system prompts because they do not share the same authority. The specialist analysts are not allowed to make final portfolio decisions, while the Portfolio Manager is required to do so.

4. **Role prompts**

Each role should have one stable role prompt reused across its stages.

This means:

* the News Analyst has one stable role prompt  
* the Fundamental Analyst has one stable role prompt  
* the Technical Analyst has one stable role prompt  
* the Portfolio Manager has one stable role prompt  
* the PM-Challenge stage has one stable role prompt

The role prompt should define:

* what that role is responsible for  
* what analytical perspective it should use  
* what kinds of evidence or questions it should focus on

The role prompt should not change between screening and deep analysis.

The role prompt should act as the node’s job description. It should not be overloaded with general output-discipline or workflow-safety rules that belong in the system prompt.

5. **Task prompts**

The `task prompt` should change depending on the workflow stage.

For specialist analysts, there should be separate task prompts for:

* screening  
* deep analysis

For debate mode, there should be separate task prompts for:

* peer review  
* revised analyst report

For challenger mode, there should be separate task prompts for:

* PM-Challenge  
* analyst challenge response

For the Portfolio Manager, there should be a separate final PM decision task prompt.

6. **Screening prompt logic**

The screening task prompt should explicitly say:

* use only the daily package  
* do not call tools  
* review all 30 DJIA stocks  
* return one screening output per stock  
* allowed statuses are only:
  * `no_issue`
  * `flag_for_deep_analysis`

So screening is:

* package-only  
* no tool use  
* a broad first-pass routing step

7. **Deep-analysis prompt logic**

The deep-analysis task prompt should explicitly say:

* analyze only the stocks in the shared deep-analysis set  
* start from the daily package row plus the bounded portfolio-state subset  
* use only the tools allowed for that analyst role  
* tool calls remain bounded to day *t*  
* return one structured deep-analysis report per stock

Deep analysis should not force unnecessary tool calls, but tool use is expected when needed because deeper evidence is retrieved through tools.

8. **Debate-stage prompt logic**

In debate configurations, the system should add:

* a peer review task prompt  
* a revised report task prompt

The peer review task prompt should instruct the reviewing analyst to:

* stay within its own role perspective  
* identify agreements, disagreements, missing risks, and questions  
* return only the peer review schema

The revised report task prompt should instruct the original analyst to:

* review peer feedback  
* revise or defend the report  
* explicitly state accepted, rejected, and partially incorporated points  
* return only the revised report schema

9. **Challenger-stage prompt logic**

In challenger configurations, the system should add:

* a PM-Challenge task prompt  
* an analyst challenge-response task prompt

The PM-Challenge task prompt should instruct the PM-Challenge stage to:

* target one analyst role at a time  
* identify weak evidence, weak reasoning, contradictions, or missing caveats  
* request clarification or revision  
* return only the challenge schema

The analyst challenge-response task prompt should instruct the challenged analyst to:

* answer the challenge directly  
* revise the recommendation or rationale if needed  
* state what challenge points were addressed  
* return only the challenge-response schema

10. **PM decision prompt logic**

The PM decision task prompt should explicitly require the Portfolio Manager to:

* synthesize the specialist analyst reports  
* consider current portfolio state and allowed PM tool outputs  
* make the target portfolio decision in weights  
* provide stock-level decision records for changed positions and explicit holds  
* provide the PM daily decision object  
* not produce execution arithmetic

The PM decision task prompt should also explicitly require the PM to state:

* which analyst role most strongly supported each stock-level decision  
* which evidence items were carried into the decision where relevant

11. **Schema instruction**

Each node should also receive a short separate schema instruction that says:

* return only the required structured output  
* do not add commentary outside the schema  
* do not wrap output in markdown fences  
* use the exact required field names

12. **Workflow-enforced data control**

Point-in-time correctness should be enforced primarily by workflow and code, not by prompt wording alone.

This means:

* the workflow chooses which package rows are passed to each node  
* the workflow chooses which stocks are in the shared deep-analysis set  
* the workflow constructs tool instances that are already bounded to the current trading day  
* the agents should not be given a mechanism to request future data in the first place

The prompts may reinforce these boundaries, but the real guarantee should come from the system design.

13. **Tool-use control**

Tool rules should be:

* screening:
  * no tools
* deep analysis:
  * only role-allowed tools
* PM stage:
  * only bounded PM tools
* debate and challenger stages:
  * no unrestricted extra retrieval unless explicitly enabled later

14. **Output validation and repair**

After a node produces output:

1. the system validates the output against the schema  
2. if invalid, the system sends one repair prompt  
3. if still invalid, the system logs the failure and stops or routes according to workflow policy

In practical terms, the repair prompt should ask the model to fix the format of the same answer rather than rethink the entire analysis from scratch.

The baseline rule should therefore be:

* validate  
* one repair attempt  
* then fail loudly and log the issue if still invalid

15. **Prompt minimalism principle**

Prompting should stay simple, controlled, and role-bounded.

The prompts should support the workflow, not replace it. The workflow should remain responsible for:

* what step runs next  
* what data is available  
* what tools are allowed  
* how outputs are validated and routed

In summary:

* the workflow enforces data access and sequencing  
* the system prompt enforces guardrails and output discipline  
* the role prompt defines the analytical identity of the node  
* the task prompt defines the current assignment  
* the schema instruction defines the output format
