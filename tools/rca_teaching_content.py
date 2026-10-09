"""Teaching guide: how CARCI turns an anomaly score into a root cause.

Written for a student audience. Every code fragment is quoted from the live
source tree by `excerpt()`, with the real line numbers preserved, so a reader can
open the file and find the same lines.
"""

from __future__ import annotations

from doc_blocks import chapter, diagram, excerpt, note, snippet, table

# ==========================================================================
# Front matter
# ==========================================================================

COVER = """
<div class="cover">
  <h1>Root Cause Analysis in CARCI</h1>
  <p class="sub">How an anomaly score becomes an explanation someone can act on</p>
  <div class="rule"></div>
  <p class="doc">Teaching Guide</p>
  <p class="tag">Six stages, with the code for each one</p>
  <div class="meta">
    Cost Anomaly Root Cause Intelligence<br>
    Isolation Forest &middot; SHAP &middot; service-day baselines &middot; Google Gemini<br>
    Companion to the Complete Code Documentation
  </div>
</div>
"""

CONTENTS = [
    ("1", "What root cause analysis actually means", [
        "The three questions", "Why a score is not a cause", "The six stages"]),
    ("2", "Stage 1 - Detect: what is unusual", [
        "The model's contribution", "The two-detector rule"]),
    ("3", "Stage 2 - Localise: where and when", [
        "The bug that shaped this stage", "Service-day baselines", "Picking the driver row"]),
    ("4", "Stage 3 - Attribute: which measurements drove it", [
        "Reading a SHAP value", "From features to plain language"]),
    ("5", "Stage 4 - Decompose: which slice carries the cost", []),
    ("6", "Stage 5 - Narrate: facts into sentences", [
        "The template engine", "Severity without a model"]),
    ("7", "Stage 6 - Reason: hypotheses about the cause", [
        "The facts/hypotheses split", "What is sent", "What comes back",
        "Distrusting the reply", "Failing safely"]),
    ("8", "A worked example, end to end", []),
    ("9", "How to verify any of this yourself", []),
    ("10", "What this system cannot do", []),
    ("11", "Teaching notes and exercises", [
        "A 60-minute session", "Exercises", "Exam-style questions with answers"]),
]


def contents_html() -> str:
    parts = ['<div class="chapter"><h2 class="contents-title">Contents</h2>']
    for number, title, subs in CONTENTS:
        parts.append(
            '<p class="toc-1"><span class="n">{}.</span> {}</p>'.format(number, title)
        )
        for index, sub in enumerate(subs, start=1):
            parts.append(
                '<p class="toc-2"><span class="n">{}.{}</span> {}</p>'.format(number, index, sub)
            )
    parts.append("</div>")
    return "".join(parts)


def stage(text: str) -> str:
    return '<div class="stage">{}</div>'.format(text)


# ==========================================================================
# 1 - What root cause analysis actually means
# ==========================================================================

SIX_STAGES = """
   a billing CSV
        |
   1. DETECT      Isolation Forest scores every row      "row 4,271 is odd"
        |         + a business rule
        v
   2. LOCALISE    aggregate to (service, date)           "AmazonEC2, 13 Jan"
        |         compare against that service's
        |         other days
        v
   3. ATTRIBUTE   SHAP splits the score across           "usage_quantity,
        |         the 7 features                          cost, transfer"
        v
   4. DECOMPOSE   share by region / resource /           "72% in
        |         tag / usage type                         ap-southeast-1"
        v
   5. NARRATE     facts become sentences                 a paragraph
        |
        v
   6. REASON      ranked hypotheses about the cause      "consistent with
                  + how to confirm them                    crypto mining"
"""

CHAPTER_1 = chapter(1, "What root cause analysis actually means", (
    "<h3>1.1 &nbsp; The three questions</h3>"
    "<p>Any anomaly system worth using answers three questions, and they get progressively "
    "harder:</p>"
    + table(["Question", "Answered by", "Difficulty"], [
        ["<strong>What is unusual?</strong>", "A model that scores rows",
         "Solved. Dozens of algorithms do this"],
        ["<strong>Why is it unusual?</strong>", "Attribution and decomposition",
         "Harder. Needs the model to be interpretable"],
        ["<strong>What caused it, and what do I do?</strong>",
         "Reasoning over the evidence",
         "Hardest. The cause is <em>not in the data</em>"],
    ])
    + "<p>Most anomaly detectors stop after the first question. That is why so many of them get "
    "switched off: an alert that says \"row 4,271 is unusual\" gives the person reading it no way "
    "to decide whether to care.</p>"

    "<h3>1.2 &nbsp; Why a score is not a cause</h3>"
    "<p>This is the single most important idea in the guide, so it is worth stating bluntly.</p>"
    + note("The cause is never in the billing data",
           "<p>A billing file records <em>what you were charged</em>. It does not record that "
           "someone left a test cluster running, or that a deployment introduced a retry loop, or "
           "that an instance was compromised. Those facts live in CloudTrail, in a deployment log, "
           "in someone's memory &mdash; not in the CSV.</p>"
           "<p>So no amount of statistics can extract a root cause from the file. What the "
           "statistics can do is narrow the search: identify which service, which day, which "
           "resource, which measurements moved. The final step from evidence to cause is an act of "
           "<em>reasoning</em>, and CARCI treats it as one.</p>")
    + "<p>Everything in this guide follows from that. Stages 1 to 4 build evidence, and are exact. "
    "Stage 5 puts the evidence into words, and is still exact. Stage 6 reasons from it, and is "
    "explicitly uncertain &mdash; which is why every hypothesis it produces carries a confidence "
    "level and cites the evidence it rests on.</p>"

    "<h3>1.3 &nbsp; The six stages</h3>"
    + diagram(SIX_STAGES)
    + "<p>Sections 2 to 7 take one stage each: what it contributes, the code that does it, and the "
    "mistake it exists to prevent. Section 8 follows one real anomaly through all six.</p>"
))


# ==========================================================================
# 2 - Stage 1: Detect
# ==========================================================================

CHAPTER_2 = chapter(2, "Stage 1 &mdash; Detect: what is unusual", (
    stage("STAGE 1 of 6 &nbsp;&middot;&nbsp; Input: cleaned billing rows &nbsp;&middot;&nbsp; "
          "Output: candidate rows")
    + "<h3>2.1 &nbsp; The model's contribution</h3>"
    "<p>An Isolation Forest scores every line item. The intuition: pick a random feature, pick a "
    "random split, cut the data in two, repeat until every point sits alone, then count the cuts "
    "each point needed. Points far from everything get isolated in very few cuts. <em>Anomalies "
    "are the ones that are easy to isolate.</em></p>"
    "<p>For root cause purposes the important property is not accuracy but <em>what kind</em> of "
    "anomaly it finds. The forest looks at seven numeric features at once, so it can flag a "
    "combination that no single threshold would catch &mdash; moderate cost, moderate usage, but "
    "an unusual <em>ratio</em> between them.</p>"

    "<h3>2.2 &nbsp; The two-detector rule</h3>"
    "<p>The model alone is not trusted to decide what gets reported. A business rule runs beside "
    "it, and the two are joined by OR:</p>"
    + excerpt("carci/analysis.py", 147, 150,
              "carci/analysis.py - the detection rule")
    + "<p>Read the last line carefully, because it encodes four separate decisions:</p>"
    + table(["Condition", "Why it is there"], [
        ["<code>has_baseline</code>",
         "A service with only one day in the file has nothing to be compared against. Reporting it "
         "would mean inventing a baseline"],
        ["<code>model_flagged OR large_change</code>",
         "Two independent detectors. The model catches strange combinations a rule could not "
         "express; the rule catches large obvious rises the model might miss"],
        ["<code>impact_value &gt; 0</code>",
         "A service-day cheaper than usual is not a cost anomaly worth reporting"],
        ["<code>&gt;= 75%</code> and <code>&gt;= $5</code>",
         "The percentage alone would report $0.02 rising to $0.05 &mdash; a 150% increase nobody "
         "cares about. The dollar floor filters noise the percentage cannot"],
    ])
    + note("Teaching point &mdash; why OR and not AND",
           "<p>Students almost always suggest AND, reasoning that requiring both detectors would "
           "reduce false positives. It would. It would also mean the system reports nothing unless "
           "an unsupervised model and a hand-written threshold happen to agree, which throws away "
           "the distinct thing each one is good at.</p>"
           "<p>Ask them: which anomalies does each detector catch that the other misses? That "
           "question is the whole design.</p>")
))


# ==========================================================================
# 3 - Stage 2: Localise
# ==========================================================================

CHAPTER_3 = chapter(3, "Stage 2 &mdash; Localise: where and when", (
    stage("STAGE 2 of 6 &nbsp;&middot;&nbsp; Input: candidate rows &nbsp;&middot;&nbsp; "
          "Output: one (service, date) per incident")
    + "<h3>3.1 &nbsp; The bug that shaped this stage</h3>"
    "<p>This stage exists because of a real defect, and the docstring still records it:</p>"
    + excerpt("carci/analysis.py", 102, 109,
              "carci/analysis.py - _attach_service_context")
    + "<p>The original code compared each row against the mean of every other row in the file. "
    "That sounds reasonable and is badly wrong. Consider a file containing cheap S3 requests and "
    "expensive EC2 instances. Every EC2 row sits far above the all-rows mean, so EC2 looks "
    "anomalous <em>constantly</em> &mdash; not because anything changed, but because EC2 is "
    "expensive.</p>"
    + note("The question you compare against decides what you find",
           "<p><strong>Wrong question:</strong> \"is this row expensive compared to all rows?\" "
           "Answer: yes, it is EC2.</p>"
           "<p><strong>Right question:</strong> \"is AmazonEC2 today more expensive than "
           "AmazonEC2 usually is?\" Answer: that is an anomaly.</p>"
           "<p>Anomaly detection is comparison, and choosing the comparison group is a modelling "
           "decision, not an implementation detail. Most bad anomaly systems fail here.</p>")

    + "<h3>3.2 &nbsp; Service-day baselines</h3>"
    "<p>The fix aggregates to <code>(service, date)</code> and builds a leave-one-out mean over "
    "that service's <em>other</em> days:</p>"
    + excerpt("carci/analysis.py", 113, 126,
              "carci/analysis.py - building the baseline")
    + "<p>Three things to point out in that fragment:</p>"
    "<ol>"
    "<li><code>transform(\"sum\")</code> totals the whole service-day but keeps one value per "
    "<em>row</em>, so the total can sit alongside the row that drove it.</li>"
    "<li><code>drop_duplicates</code> before the per-service totals stops a service-day with 40 "
    "rows counting 40 times in the average.</li>"
    "<li>The leave-one-out arithmetic &mdash; subtract today, divide by the remaining day count "
    "&mdash; keeps the day being judged out of its own baseline. Leaving it in would drag the "
    "baseline toward the anomaly and shrink the very increase you are trying to measure.</li>"
    "</ol>"

    "<h3>3.3 &nbsp; Picking the driver row</h3>"
    "<p>A service-day may contain hundreds of line items. Reporting all of them would produce "
    "hundreds of identical cards, so one row is chosen to represent the incident:</p>"
    + excerpt("carci/analysis.py", 163, 172,
              "carci/analysis.py - deduplication and capping")
    + "<p>The highest-scoring row becomes the <em>driver</em>: the specific line item that best "
    "explains the day. This is why the UI shows both a \"Service Day Cost\" and a \"Driver Row "
    "Cost\" &mdash; the first is the size of the incident, the second is where to start looking.</p>"
))


# ==========================================================================
# 4 - Stage 3: Attribute
# ==========================================================================

CHAPTER_4 = chapter(4, "Stage 3 &mdash; Attribute: which measurements drove it", (
    stage("STAGE 3 of 6 &nbsp;&middot;&nbsp; Input: the driver row &nbsp;&middot;&nbsp; "
          "Output: per-feature contributions")
    + "<p>The forest gives one number per row. SHAP splits that number across the seven features, "
    "so instead of \"this row scored -0.0512\" you get \"the score was driven mostly by "
    "usage_quantity, then cost, then data_transfer_gb\".</p>"

    "<h3>4.1 &nbsp; Reading a SHAP value</h3>"
    + excerpt("carci/analysis.py", 176, 191,
              "carci/analysis.py - _get_feature_contributions")
    + table(["Field", "Meaning"], [
        ["<code>feature_value</code>", "What this row actually measured, in its own units"],
        ["<code>shap_value</code>",
         "How far this feature pushed the anomaly score, and in which direction"],
        ["<code>impact_strength</code>",
         "<code>abs(shap_value)</code> &mdash; how much the feature mattered, ignoring direction"],
    ])
    + note("Why the ranking uses the absolute value",
           "<p>Sorting by <code>impact_strength</code> rather than by <code>shap_value</code> is "
           "deliberate. A feature that pushes the score strongly toward \"normal\" is just as much "
           "part of the explanation as one pushing toward \"anomalous\" &mdash; it tells you what "
           "was <em>not</em> wrong. Ranking by the signed value would bury those.</p>"
           "<p>Note also the <code>&gt; 0</code> filter on the last line: a feature with exactly "
           "zero contribution explains nothing and is left out of the top list entirely.</p>")
    + note("A caveat to state plainly to students",
           "<p>SHAP values are attributions of the <em>model's score</em>, not of the money. A "
           "feature can dominate the SHAP ranking without being where the dollars went. Stage 4 "
           "exists precisely because these two questions are different, and confusing them is the "
           "most common misreading of an explainability output.</p>", "warn")

    + "<h3>4.2 &nbsp; From features to plain language</h3>"
    "<p><code>top_ml_features</code> carries raw column names like <code>cost_per_usage</code>. "
    "Those are meaningless to a finance reader, so the naming is deferred: the template quotes them "
    "as-is, and the language model in stage 6 is instructed to render them in plain language "
    "instead. \"Unit price\" is what <code>cost_per_usage</code> means; the pipeline never has to "
    "hard-code that translation.</p>"
))


# ==========================================================================
# 5 - Stage 4: Decompose
# ==========================================================================

CHAPTER_5 = chapter(5, "Stage 4 &mdash; Decompose: which slice carries the cost", (
    stage("STAGE 4 of 6 &nbsp;&middot;&nbsp; Input: the service-day &nbsp;&middot;&nbsp; "
          "Output: share by region, resource, tag, usage type")
    + "<p>Stage 3 said which <em>measurements</em> moved. Stage 4 says which <em>slice of the "
    "business</em> the money went to, and it is pure arithmetic with no model involved:</p>"
    + excerpt("carci/analysis.py", 33, 50, "carci/analysis.py - _to_breakdown")
    + "<p>The same function runs for each of five dimensions, always within the anomalous "
    "service-day:</p>"
    + table(["Dimension", "The question it answers"], [
        ["<code>region</code>", "Is this concentrated in one region, or spread everywhere?"],
        ["<code>resource</code>", "One runaway instance, or the whole fleet drifting up?"],
        ["<code>tag</code>", "Which team or project owns this spend?"],
        ["<code>usage_type</code>", "Compute, storage, data transfer, or requests?"],
        ["<code>service</code>", "How does this service compare to others on the same day?"],
    ])
    + note("Concentration is the most useful signal here",
           "<p><code>region_share_pct</code> at 72% and at 12% mean completely different things. "
           "High concentration points at a single misbehaving thing &mdash; one instance, one job, "
           "one bucket. Low concentration points at something systemic &mdash; a price change, a "
           "traffic increase, a fleet-wide deployment.</p>"
           "<p>This is why the share percentage, not just the top name, is passed forward to the "
           "reasoning stage. \"ap-southeast-1\" alone would not distinguish those two cases.</p>")
))


# ==========================================================================
# 6 - Stage 5: Narrate
# ==========================================================================

CHAPTER_6 = chapter(6, "Stage 5 &mdash; Narrate: facts into sentences", (
    stage("STAGE 5 of 6 &nbsp;&middot;&nbsp; Input: all the evidence &nbsp;&middot;&nbsp; "
          "Output: a paragraph, a headline, a severity")
    + "<h3>6.1 &nbsp; The template engine</h3>"
    "<p>Before any language model is involved, the evidence is assembled into English by string "
    "formatting. The most instructive part is how it words the <em>flag</em>:</p>"
    + excerpt("carci/analysis.py", 243, 254,
              "carci/analysis.py - the three-way flag branch")
    + "<p>Three branches, because there are genuinely three situations, and collapsing them would "
    "be a lie:</p>"
    + table(["Situation", "What the text must not claim"], [
        ["<code>is_fallback</code> &mdash; nothing crossed the threshold",
         "That anything was detected at all. It says \"informational, not a detection\""],
        ["<code>model_flag</code> &mdash; the forest flagged it",
         "Nothing; this is the honest case"],
        ["Neither &mdash; only the business rule fired",
         "That the model found it. It says so explicitly"],
    ])
    + note("Teaching point &mdash; never overstate the evidence",
           "<p>It would be easy, and much shorter, to write one sentence saying \"the system "
           "detected an anomaly\" for all three cases. It would also be false in two of them.</p>"
           "<p>A system that tells a user something was machine-detected when it was actually "
           "caught by a hand-written <code>&gt;= 75%</code> rule has misrepresented its own "
           "confidence. Users calibrate their trust on exactly this kind of wording.</p>")

    + "<h3>6.2 &nbsp; Severity without a model</h3>"
    "<p>Severity is computed arithmetically, so it exists whether or not the language model runs:</p>"
    + excerpt("carci/analysis.py", 221, 240, "carci/analysis.py - _severity_for")
    + "<p>Note that it takes impact and percentage <em>together</em>. A 900% rise on $3 is not an "
    "incident; a 40% rise on $8,000 is. Either signal alone would rank the list badly.</p>"
    "<p>The fallback row is forced to <code>low</code> regardless of its numbers, for the same "
    "reason the template refuses to call it a detection: it is context, not an incident.</p>"
))


# ==========================================================================
# 7 - Stage 6: Reason
# ==========================================================================

FACTS_HYP = """
   EVIDENCE (stages 1-4)          computed by the pipeline
        |                         exact, reproducible, auditable
        |
        +---> FACTS               quoted verbatim, never recomputed
        |                         "2979.72 USD against a baseline of 446.67"
        |
        +---> HYPOTHESES          reasoned, ranked, uncertain
                                  "consistent with a compromised instance"
                                  confidence: high
                                  evidence:   usage_type is CryptoMiningTraffic
"""

CHAPTER_7 = chapter(7, "Stage 6 &mdash; Reason: hypotheses about the cause", (
    stage("STAGE 6 of 6 &nbsp;&middot;&nbsp; Input: the evidence as JSON &nbsp;&middot;&nbsp; "
          "Output: ranked causes and checks")
    + "<h3>7.1 &nbsp; The facts/hypotheses split</h3>"
    "<p>A root cause report has to do two things that pull in opposite directions. It must quote "
    "figures with absolute fidelity, and it must speculate about causes &mdash; because, as "
    "section 1.2 established, the cause is not in the data.</p>"
    "<p>Treating those as one task is what makes language models dangerous in financial reporting. "
    "So the prompt separates them explicitly:</p>"
    + diagram(FACTS_HYP)
    + excerpt("carci/llm_reasoning.py", 78, 88,
              "carci/llm_reasoning.py - the HYPOTHESES rules")
    + table(["", "FACTS", "HYPOTHESES"], [
        ["<strong>Source</strong>", "The pipeline", "The model's reasoning"],
        ["<strong>May the model invent?</strong>", "Never", "That is the point"],
        ["<strong>Certainty</strong>", "Exact", "Ranked, with a confidence"],
        ["<strong>Must cite evidence?</strong>", "It <em>is</em> the evidence", "Yes, a named field"],
        ["<strong>Wording</strong>", "Plain assertion",
         "\"consistent with\", never \"was caused by\""],
    ])
    + note("Why this is the right division of labour",
           "<p>The model is bad at arithmetic and good at pattern-matching against a large body of "
           "engineering knowledge. So it is given zero arithmetic and asked for exactly the thing "
           "it is good at: <em>given these symptoms, what conditions typically produce them?</em></p>"
           "<p>That is also what a human analyst does. They do not recompute the bill; they read "
           "the evidence and propose what would explain it.</p>")

    + "<h3>7.2 &nbsp; What is sent</h3>"
    "<p>Only a narrow, named set of fields leaves the pipeline:</p>"
    + excerpt("carci/llm_reasoning.py", 219, 227,
              "carci/llm_reasoning.py - _to_payload")
    + "<p>The narrowing is a correctness decision, not a bandwidth one: every extra key is a "
    "chance for the model to repeat something the pipeline never computed. Note also what is "
    "<em>absent</em> &mdash; the keyword-based recommendation is withheld, so the action the model "
    "returns is its own reading of the evidence rather than a paraphrase of a rule.</p>"

    "<h3>7.3 &nbsp; What comes back</h3>"
    "<p>The reply is constrained by an explicit <code>responseSchema</code>, so it arrives as "
    "parseable JSON rather than prose to be scraped:</p>"
    + table(["Field", "Kind", "Purpose"], [
        ["<code>headline</code>", "Hypothesis", "Names the suspected cause, not the symptom"],
        ["<code>severity</code>", "Judgement", "critical / high / medium / low"],
        ["<code>explanation</code>", "Facts", "Three or four paragraphs of narrative"],
        ["<code>likely_causes</code>", "Hypothesis",
         "Ranked, each with <code>confidence</code> and <code>evidence</code>"],
        ["<code>investigation_steps</code>", "Method", "Checks that confirm or eliminate a cause"],
        ["<code>recommended_action</code>", "Judgement", "What to do once confirmed"],
    ])
    + note("The investigation steps are what make it falsifiable",
           "<p>A hypothesis you cannot check is just an opinion. Requiring each anomaly to come "
           "with the specific console page, log or command that would settle the question turns "
           "the output from a guess into something a reader can act on and disprove.</p>"
           "<p>This is the difference between \"probably crypto mining\" and \"open CloudTrail for "
           "this instance in ap-southeast-1 and look for unexpected inbound connections\".</p>")

    + "<h3>7.4 &nbsp; Distrusting the reply</h3>"
    "<p>The schema guarantees the <em>shape</em> of the reply. It guarantees nothing about the "
    "content, so the first code that touches the response validates it:</p>"
    + excerpt("carci/llm_reasoning.py", 335, 341,
              "carci/llm_reasoning.py - _clean_causes")
    + "<p>A hypothesis missing either its mechanism or its evidence is discarded outright. That is "
    "the rule from 7.1 enforced in code rather than merely requested in a prompt &mdash; "
    "unsupported speculation never reaches the screen.</p>"
    + note("Teaching point &mdash; validate at the boundary",
           "<p>The schema is enforced by someone else's server. These cleaners are the first code "
           "<em>you</em> control that touches the reply, and they are where \"the response is "
           "well-formed\" gets checked instead of assumed.</p>"
           "<p>Treat every external API this way, including ones whose contract you believe you "
           "have pinned down. A prompt is a request, not a guarantee.</p>")

    + "<h3>7.5 &nbsp; Failing safely</h3>"
    "<p>Five different things can stop this stage producing output: no API key, the feature "
    "switched off, a network failure, an HTTP error, or an unparseable reply. All five produce the "
    "same outcome &mdash; the stage-5 template text is kept and the app carries on:</p>"
    + excerpt("carci/analysis.py", 356, 368,
              "carci/analysis.py - _apply_llm_explanations, the safe part")
    + "<p>The template is copied into <code>template_*</code> fields <em>before</em> any network "
    "call, so it cannot be lost. <code>likely_causes</code> and <code>investigation_steps</code> "
    "start empty because they have no template equivalent: naming a probable cause is exactly the "
    "judgement no keyword rule can make. Offline, those sections are simply absent rather than "
    "filled with something weaker.</p>"
    + note("Graceful degradation has a cost you must design for",
           "<p>A silent fallback is invisible. A student demonstrating this project with an expired "
           "key would see plausible explanations and never notice the model had not run.</p>"
           "<p>That is why <code>explanation_method</code> is recorded on every record and printed "
           "in the UI. <strong>Degrade quietly, but always leave a way to find out that you "
           "did.</strong></p>", "warn")
))


# ==========================================================================
# 8 - Worked example
# ==========================================================================

WORKED_EVIDENCE = """
STAGE 1  DETECT
   model_is_anomaly = 1          the forest flagged the driver row
   percentage       = 567.1      the business rule would have caught it too

STAGE 2  LOCALISE
   service_date_cost = 2979.72   AmazonEC2, 13 January 2026
   normal_value      =  446.67   mean of EC2's other days in the file
   impact_value      = 2533.05   2979.72 - 446.67
   driver_row_cost   = 1011.65   the single line item that scored highest

STAGE 3  ATTRIBUTE
   usage_quantity     value 16049.04    shap -2.3399
   cost               value  1011.65    shap -2.2855
   data_transfer_gb   value   770.18    shap -2.2010

STAGE 4  DECOMPOSE
   region      ap-southeast-1    72.01% of the service-day
   resource    db-1cd8dd14-...
   usage_type  CryptoMiningTraffic
   tag         AIResearch

STAGE 5  NARRATE
   severity    critical          impact >= 1000
   headline    "AmazonEC2 CryptoMiningTraffic up 567% in ap-southeast-1"
"""

WORKED_OUTPUT = """
headline   Crypto-mining traffic on EC2 instance db-1cd8dd14
severity   critical

explanation
   On 13 January 2026, AmazonEC2 spend surged by 567.10% to reach an observed
   cost of 2979.72 USD, generating an impact of 2533.05 USD over a baseline of
   446.67 USD. A single line item contributed 1011.65 USD.

   The cost was heavily concentrated in the ap-southeast-1 region, which
   accounted for 72.01% of the regional share, tied to resource db-1cd8dd14-...
   under the AIResearch tag. The usage type was explicitly flagged as
   CryptoMiningTraffic, indicating unauthorized or unintended workload execution.

   Feature attribution highlights usage quantity at 16049.04, total cost at
   1011.65 USD, and data transfer of 770.18 GB as the primary drivers behind the
   anomaly score. These metrics reflect high throughput and prolonged compute
   utilization consistent with cryptocurrency mining operations.

   (fourth paragraph: escalation)

likely_causes
   1. [high]   Compromised EC2 instance running unauthorized cryptocurrency
               mining scripts
      evidence usage_type is CryptoMiningTraffic with 16049.04 usage quantity
               and 770.18 GB data transfer

   2. [medium] Unintended deployment of heavy proof-of-work algorithms under the
               AIResearch tag
      evidence Tag is AIResearch and ap-southeast-1 holds 72.01% region share

investigation_steps
   1. Open the Amazon EC2 Console and inspect resource db-1cd8dd14-... in
      region ap-southeast-1.
   2. Review VPC Flow Logs and CloudTrail logs for unexpected inbound
      connections or credential misuse on the instance.
   3. Check security group rules associated with the resource to identify
      overly permissive access.
"""

CHAPTER_8 = chapter(8, "A worked example, end to end", (
    "<p>One anomaly, followed through all six stages. Every number below is real output from "
    "<code>data set/test_2_obvious_anomalies.csv</code>.</p>"
    "<h4>The evidence the pipeline built (stages 1&ndash;5)</h4>"
    + diagram(WORKED_EVIDENCE)
    + "<h4>What stage 6 made of it</h4>"
    + diagram(WORKED_OUTPUT)

    + "<h4>Now check the model's work</h4>"
    "<p>This is the exercise worth doing with students. Take every number in the generated prose "
    "and find it in the evidence block above:</p>"
    + table(["Number in the prose", "Where it came from", "Invented?"], [
        ["567.10%", "<code>percentage</code>, stage 2", "No"],
        ["2979.72 USD", "<code>service_date_cost</code>, stage 2", "No"],
        ["2533.05 USD", "<code>impact_value</code>, stage 2", "No"],
        ["446.67 USD", "<code>normal_value</code>, stage 2", "No"],
        ["1011.65 USD", "<code>driver_row_cost</code>, stage 2", "No"],
        ["72.01%", "<code>region_share_pct</code>, stage 4", "No"],
        ["16049.04, 770.18", "SHAP feature values, stage 3", "No"],
    ])
    + "<p>Every figure traces back. Automated over the full 16-anomaly run, 453 numbers were "
    "checked and none was unmatched.</p>"
    + note("Now do the same to the hypotheses &mdash; and notice the difference",
           "<p>\"Compromised EC2 instance running unauthorized mining scripts\" appears nowhere in "
           "the evidence. It <em>cannot</em>, because compromise is not a billing fact.</p>"
           "<p>That is not a failure &mdash; it is stage 6 doing its job. The controls that make it "
           "responsible are that it is labelled a hypothesis, ranked second-to-none rather than "
           "asserted, given a confidence of <code>high</code> rather than certainty, tied to the "
           "specific fields that motivated it, and shipped with three checks that would prove it "
           "wrong.</p>"
           "<p><strong>The lesson: separate what you know from what you infer, and label which is "
           "which.</strong> That principle is older than machine learning and applies well beyond "
           "this project.</p>")
))


# ==========================================================================
# 9 - Verification
# ==========================================================================

VERIFY_SNIPPET = """
import pandas as pd
from carci.analysis import build_analysis_result
from carci import llm_reasoning

result = build_analysis_result(pd.read_csv("dataset.csv", skipinitialspace=True))

# Which engine wrote the text?
print(result["metadata"]["explanation_method"])
# -> "LLM (gemini-3.5-flash-lite)"   or   "deterministic template"

# If it fell back, why?
print(llm_reasoning.last_error())

record = result["service_comparison"][0]
print(record["severity"], "|", record["headline"])
for cause in record["likely_causes"]:
    print(cause["confidence"], "-", cause["cause"])
    print("   evidence:", cause["evidence"])

# The template is always kept, so the two can be compared side by side
print(record["template_explanation"])
"""

CHAPTER_9 = chapter(9, "How to verify any of this yourself", (
    "<p>Because the fallback is silent, \"the explanations look good\" is not evidence that the "
    "reasoning stage ran. Three checks, in increasing order of certainty:</p>"

    "<h4>1. Look at the caption in the app</h4>"
    "<p>Page 3, under the \"Root Cause Analysis\" heading. It reads either <em>\"Explanations "
    "written by LLM (gemini-3.5-flash-lite)\"</em> or <em>\"Explanations from the deterministic "
    "template\"</em>.</p>"

    "<h4>2. Look at the card</h4>"
    "<p>Ranked causes and investigation steps appear <strong>only</strong> in LLM mode. If a card "
    "shows a narrative and a severity but no \"Likely causes\" section, stage 6 did not run.</p>"

    "<h4>3. Inspect the result object</h4>"
    + snippet(VERIFY_SNIPPET)

    + "<h4>Forcing each state for a demonstration</h4>"
    + table(["To show", "Do this"], [
        ["The full six-stage output", "A valid <code>GEMINI_API_KEY</code> in <code>.env</code>"],
        ["The template fallback", "Set <code>CARCI_LLM_REASONING=0</code> and re-run"],
        ["A diagnosable failure",
         "Corrupt the key. <code>last_error()</code> reports the cause; the app still works"],
    ])
    + note("A demonstration worth doing in front of a class",
           "<p>Run the same file twice, once with the key and once with "
           "<code>CARCI_LLM_REASONING=0</code>, and put the two cards side by side.</p>"
           "<p>The numbers are identical. The severity is identical. Only the wording and the "
           "hypotheses differ. That single comparison teaches the architecture better than any "
           "diagram: it shows exactly which parts of the output the language model is, and is not, "
           "responsible for.</p>")
))


# ==========================================================================
# 10 - Limits
# ==========================================================================

CHAPTER_10 = chapter(10, "What this system cannot do", (
    "<p>State these plainly. A report that lists its own limits is more credible, not less.</p>"
    "<ol>"
    "<li><strong>It cannot confirm a cause.</strong> Stage 6 produces hypotheses. Confirmation "
    "requires the investigation steps to actually be run against CloudTrail, the console or the "
    "logs &mdash; none of which CARCI reads.</li>"
    "<li><strong>It misses about a third of anomalies.</strong> Recall is 0.657 on the labelled "
    "dataset. The explanations are only as good as the detection that precedes them.</li>"
    "<li><strong>It always flags roughly 5% of rows.</strong> <code>contamination = 0.05</code> "
    "sets where the cut-off sits, not how many anomalies exist. A perfectly clean file still "
    "produces flags.</li>"
    "<li><strong>SHAP attributes the score, not the money.</strong> The most important feature is "
    "not necessarily where the dollars went.</li>"
    "<li><strong>Prompt adherence is not enforced.</strong> The schema guarantees the reply's "
    "structure; nothing validates that the prose obeys the writing rules.</li>"
    "<li><strong>The reasoning stage is not reproducible.</strong> The same file analysed twice can "
    "produce different wording and different hypotheses. The facts do not change; the narrative "
    "does.</li>"
    "<li><strong>Billing details leave the machine.</strong> Resource identifiers, tags and figures "
    "are sent to a third-party API. <code>CARCI_LLM_REASONING=0</code> exists so this can be turned "
    "off.</li>"
    "</ol>"
    + note("The honest summary",
           "<p>CARCI narrows a 10,000-row bill down to twenty incidents, tells you exactly what "
           "changed and where, and proposes what to check first. It does not tell you what "
           "happened. A human still closes that gap &mdash; the system's job is to make the gap "
           "small enough to close quickly.</p>")
))


# ==========================================================================
# 11 - Teaching notes
# ==========================================================================

QA = [
    ("Why can a root cause not be computed from the billing file alone?",
     "The file records what you were charged, not why. Compromise, misconfiguration and "
     "deployment mistakes leave no column in a CUR export. Statistics can localise the anomaly "
     "to a service, day, region and resource, but the final step to a cause is inference from "
     "evidence, not a calculation over it."),
    ("The detection rule joins two detectors with OR. Why not AND?",
     "They catch different things. The forest catches unusual combinations across seven features "
     "that no threshold expresses; the rule catches large obvious rises the forest may score as "
     "unremarkable. AND would report only cases where both agree, discarding what each is "
     "individually good at."),
    ("Why compare a service-day against that service's other days rather than against all rows?",
     "Because comparing against all rows measures how expensive a service is, not whether it "
     "changed. An always-expensive service would be flagged permanently. The comparison group "
     "defines what counts as an anomaly, so choosing it is a modelling decision."),
    ("Why does the baseline exclude the day being judged?",
     "Including it would drag the baseline toward the anomaly, shrinking the measured increase. "
     "The leave-one-out mean keeps the comparison independent of the value being tested."),
    ("Why is the feature ranking sorted by the absolute SHAP value?",
     "Because a feature pushing strongly toward normal is part of the explanation too. Sorting "
     "by the signed value would rank those last and hide what was not wrong."),
    ("A card says severity critical but the model never flagged the row. Is that a contradiction?",
     "No. Severity is computed from impact and percentage, so the business rule alone can produce "
     "a critical entry. The narrative states explicitly that the model did not flag it, which is "
     "why the three-way branch in the template exists."),
    ("What is the difference between the `explanation` field and the `likely_causes` field?",
     "`explanation` restates facts the pipeline computed and may contain no invented figure. "
     "`likely_causes` is inference, is ranked, carries a confidence, and must cite the evidence "
     "it rests on. They are held to opposite standards on purpose."),
    ("Why does the code discard a hypothesis that has no evidence field?",
     "Because a cause with nothing behind it is the unsupported speculation the prompt forbids. "
     "The prompt is a request; the cleaner is the enforcement. Never rely on an external service "
     "to obey your instructions."),
    ("Both engines produce a headline. What can the template's headline never do?",
     "Name a probable cause. It can only describe the symptom, because identifying a cause is a "
     "judgement no keyword rule can make. This is the clearest illustration of what the reasoning "
     "stage actually adds."),
    ("A user reads a root cause paragraph and finds it useful. What evidence would you need "
     "before concluding the language model produced it?",
     "The caption naming the method, the presence of the likely-causes section, or "
     "`result[\"metadata\"][\"explanation_method\"]`. Usefulness is not evidence: the template is "
     "designed to be useful too, which is exactly why the fallback is safe and exactly why it is "
     "invisible."),
]

CHAPTER_11 = chapter(11, "Teaching notes and exercises", (
    "<h3>11.1 &nbsp; A 60-minute session</h3>"
    + table(["Time", "Topic", "Material"], [
        ["0&ndash;10 min", "Why a score is not a cause", "Section 1.2. Ask what a billing file "
         "does <em>not</em> record before showing the answer"],
        ["10&ndash;20 min", "Detection and localisation", "Sections 2 and 3. The all-rows baseline "
         "bug is the strongest teaching moment in the project"],
        ["20&ndash;30 min", "Attribution and decomposition", "Sections 4 and 5, emphasising that "
         "they answer different questions"],
        ["30&ndash;45 min", "The facts/hypotheses split", "Section 7.1, then the worked example in "
         "section 8"],
        ["45&ndash;55 min", "Live demo", "Run with and without the key, cards side by side"],
        ["55&ndash;60 min", "Limits", "Section 10. Close on what the system cannot do"],
    ])

    + "<h3>11.2 &nbsp; Exercises</h3>"
    "<ol>"
    "<li>Change the business rule from 75% to 40% and re-run. How many more anomalies appear, and "
    "how many are worth acting on? Argue for a threshold from the result.</li>"
    "<li>Remove the <code>impact_value &gt;= 5.0</code> floor. Find an anomaly that now appears "
    "which nobody would care about, and explain in one sentence why the percentage alone was "
    "misleading.</li>"
    "<li>Set <code>CARCI_LLM_REASONING=0</code> and write down three things the report loses. For "
    "each, say whether it could be recovered by a rule.</li>"
    "<li>Take one generated explanation and verify every number against "
    "<code>record[\"feature_contributions\"]</code> and the record fields. Report anything that "
    "does not trace.</li>"
    "<li>Write a hypothesis for an anomaly yourself, before reading the model's. Compare. Which of "
    "you cited better evidence?</li>"
    "<li>The system caps output at 20 anomalies. Design an alternative ranking to "
    "<code>priority_score</code> and justify it in terms of what a finance team actually needs "
    "first.</li>"
    "<li>Propose a way to measure whether the hypotheses are any good. This is genuinely hard: "
    "there are no labels for causes. A serious answer is worth more than a confident one.</li>"
    "</ol>"

    + "<h3>11.3 &nbsp; Exam-style questions with answers</h3>"
    + "".join(
        '<h4>Q{}. {}</h4><p class="small">{}</p>'.format(number, question, answer)
        for number, (question, answer) in enumerate(QA, start=1)
    )
))


# ==========================================================================

DOCUMENT = [
    COVER,
    contents_html(),
    CHAPTER_1,
    CHAPTER_2,
    CHAPTER_3,
    CHAPTER_4,
    CHAPTER_5,
    CHAPTER_6,
    CHAPTER_7,
    CHAPTER_8,
    CHAPTER_9,
    CHAPTER_10,
    CHAPTER_11,
]
