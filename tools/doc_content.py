"""The prose of the CARCI code documentation.

Source listings are not stored here. Each chapter names a file and the builder
reads it off disk, so "complete source code" cannot go stale. Only the
explanations live in this module, and they carry line references that must be
checked whenever the corresponding file is restructured.
"""

from __future__ import annotations

from doc_blocks import (
    chapter,
    diagram,
    line_count,
    note,
    snippet,
    source_chapter,
    table,
)

# ==========================================================================
# Front matter
# ==========================================================================

COVER = """
<div class="cover">
  <h1>CARCI</h1>
  <p class="sub">Cost Anomaly Root Cause Intelligence</p>
  <div class="rule"></div>
  <p class="doc">Complete Code Documentation</p>
  <p class="tag">A teaching guide to every file and every line</p>
  <div class="meta">
    AWS Cost Anomaly Detection using Isolation Forest<br>
    Python &middot; scikit-learn &middot; SHAP &middot; Streamlit &middot; Google Gemini<br>
    Dataset: 10,000 rows &middot; F1 score 0.751
  </div>
</div>
"""

CONTENTS = [
    ("1", "What this system does",
     ["The architecture", "Every file at a glance"]),
    ("2", "The concepts you need first",
     ["Supervised vs unsupervised", "Isolation Forest explained",
      "Feature engineering", "The four metrics"]),
    ("3", "app.py — The user interface",
     ["Purpose and concepts", "Complete source code"]),
    ("4", "carci/schema.py — Finding the right columns",
     ["Purpose and concepts", "Complete source code"]),
    ("5", "carci/preprocessing.py — Cleaning the data",
     ["Purpose and concepts", "Complete source code"]),
    ("6", "carci/shared.py — Feature engineering and data splitting",
     ["Purpose and concepts", "Complete source code"]),
    ("7", "carci/isolation_forest_model.py — The machine learning model",
     ["Purpose and concepts", "Complete source code"]),
    ("8", "carci/analysis.py — From scores to explanations",
     ["Purpose and concepts", "Complete source code"]),
    ("9", "carci/llm_reasoning.py — Writing the root cause",
     ["Purpose and concepts", "Complete source code"]),
    ("10", "carci/reporting.py — Building the exports",
     ["Purpose and concepts", "Complete source code"]),
    ("11", "How the evaluation works",
     ["The results", "Label leakage: why 1.000 is a bug",
      "Testing your own design decisions"]),
    ("12", "Known limitations", []),
    ("13", "Glossary", []),
    ("14", "Questions to test understanding", []),
]


def contents_html() -> str:
    parts = ['<div class="chapter"><h2 class="contents-title">Contents</h2>']
    for number, title, subs in CONTENTS:
        parts.append(
            '<p class="toc-1"><span class="n">{}.</span> {}</p>'.format(number, title)
        )
        for index, sub in enumerate(subs, start=1):
            parts.append(
                '<p class="toc-2"><span class="n">{}.{}</span> {}</p>'.format(
                    number, index, sub
                )
            )
    parts.append("</div>")
    return "".join(parts)


# ==========================================================================
# 1 - What this system does
# ==========================================================================

ARCHITECTURE = """
   THE WEB APP (detection)                 THE COMMAND LINE (evaluation)
   app.py                                  python -m carci.isolation_forest_model
        |                                       |
        |  upload a billing file                |  needs a file WITH labels
        v                                       v
   schema.py        find the columns        shared.py    split into train / test
        |                                       |
        v                                       v
   preprocessing.py clean the data          isolation_forest_model.py
        |                                       |   fit on normal rows only
        v                                       |   predict on the test set
   shared.py        build 7 features            v
        |                                   print Accuracy / Precision / Recall / F1
        v
   isolation_forest_model.py
        |           score + SHAP
        v
   analysis.py      service-day rules
        |           every figure computed here
        v
   llm_reasoning.py Gemini writes the explanation
        |           template fallback if offline
        v
   reporting.py     text + CSV exports
        |
        v
   app.py           charts, tables, downloads
"""

CHAPTER_1 = chapter(1, "What this system does", (
    "<p>CARCI &mdash; Cost Anomaly Root Cause Intelligence &mdash; reads an AWS billing file and "
    "answers three questions in order:</p>"
    "<ol>"
    "<li><strong>What is unusual?</strong> An Isolation Forest scores every line item.</li>"
    "<li><strong>Why is it unusual?</strong> SHAP attribution identifies which features drove "
    "the score.</li>"
    "<li><strong>What should I do?</strong> A language model turns those figures into a written "
    "explanation and a recommended action naming the service, day, region and resource.</li>"
    "</ol>"
    "<p>Most anomaly detectors stop after step 1. Steps 2 and 3 are what make this a root cause "
    "system.</p>"

    "<h3>1.1 &nbsp; The architecture</h3>"
    "<p>There are two separate entry points that share the same model. Students confuse these "
    "constantly, so be explicit about the difference:</p>"
    + diagram(ARCHITECTURE)
    + table(["", "The web app", "The CLI"], [
        ["<strong>Purpose</strong>", "Find anomalies in a new file",
         "Measure how good the model is"],
        ["<strong>Needs labels?</strong>", "No", "Yes &mdash; needs <code>is_anomaly</code>"],
        ["<strong>Produces</strong>", "Charts, cards, explanations",
         "Accuracy, Precision, Recall, F1"],
        ["<strong>Runs SHAP?</strong>", "Yes (slow)", "No (fast)"],
        ["<strong>Calls the LLM?</strong>", "Yes, once per analysis", "No"],
        ["<strong>Trains on</strong>", "The uploaded file itself", "80% of the normal rows"],
    ])
    + note("The most common misunderstanding",
           "<p>The web app produces <strong>no accuracy score</strong>, and it cannot. Accuracy "
           "requires knowing the right answer, and a real billing file has no "
           "<code>is_anomaly</code> column &mdash; that is the entire reason the system exists. "
           "Evaluation happens only on the labelled <code>dataset.csv</code>, from the command "
           "line.</p>")

    + "<h3>1.2 &nbsp; Every file at a glance</h3>"
    + table(["File", "Lines", "Responsibility"], [
        ["<code>app.py</code>", line_count("app.py"),
         "Streamlit interface, three-page wizard. No ML at all"],
        ["<code>carci/schema.py</code>", line_count("carci/schema.py"),
         "Work out which column means what"],
        ["<code>carci/preprocessing.py</code>", line_count("carci/preprocessing.py"),
         "Clean and standardise the data"],
        ["<code>carci/shared.py</code>", line_count("carci/shared.py"),
         "Build the 7 features; split train/test"],
        ["<code>carci/isolation_forest_model.py</code>",
         line_count("carci/isolation_forest_model.py"),
         "The model, scoring, SHAP, evaluation"],
        ["<code>carci/analysis.py</code>", line_count("carci/analysis.py"),
         "Business rules, anomaly facts, orchestration"],
        ["<code>carci/llm_reasoning.py</code>", line_count("carci/llm_reasoning.py"),
         "The Gemini call that writes the root cause text"],
        ["<code>carci/reporting.py</code>", line_count("carci/reporting.py"),
         "Text and CSV exports"],
        ["<code>dataset.csv</code>", "10,000 rows", "Training and testing data"],
        ["<code>requirements.txt</code>", line_count("requirements.txt"),
         "Pinned dependencies"],
    ])
    + "<h4>How to read the rest of this document</h4>"
    "<p>Sections 3 to 10 cover one file each. Every section gives the purpose, the concepts a "
    "student needs, a walkthrough of the important parts, and then the complete source code with "
    "line numbers, so the walkthrough can be followed against the real thing.</p>"
    "<p>Those listings are not typed into this document. They are read from the source tree each "
    "time it is built by <code>tools/build_code_documentation.py</code>, so the code printed here "
    "is the code that runs. Line references in the prose are maintained by hand and are the one "
    "part that can fall behind &mdash; if a number looks wrong, trust the listing.</p>"
))


# ==========================================================================
# 2 - The concepts you need first
# ==========================================================================

CHAPTER_2 = chapter(2, "The concepts you need first", (
    "<h3>2.1 &nbsp; Supervised versus unsupervised learning</h3>"
    + table(["", "Supervised", "Unsupervised"], [
        ["<strong>Needs labels?</strong>", "Yes &mdash; you must know the answers", "No"],
        ["<strong>Learns</strong>", "The mapping from input to known answer",
         "The structure of the data"],
        ["<strong>Example here</strong>", "Gradient Boosting (comparison only)",
         "Isolation Forest (the real model)"],
    ])
    + "<p>CARCI must be unsupervised, because nobody hand-labels a real AWS bill. The system has "
    "to identify unusual spending without ever being told what unusual looks like.</p>"

    "<h3>2.2 &nbsp; Isolation Forest in one paragraph</h3>"
    "<p>Pick a random feature. Pick a random value to split on. Cut the data in two. Repeat until "
    "every point sits alone. Count the cuts each point required. A point buried inside a dense "
    "cluster needs many cuts; a point far from everything is separated almost immediately. "
    "Anomalies are the easy ones to isolate. Build 1,000 such trees, average the path lengths, and "
    "you have a robust anomaly score.</p>"

    "<h3>2.3 &nbsp; Feature engineering</h3>"
    "<p>The model can only split on one feature at a time, so it cannot by itself discover that "
    "\"cost is high relative to usage\". We compute that relationship for it as a single number, "
    "<code>cost_per_usage</code>. That is feature engineering: giving the model the relationships "
    "it cannot derive on its own.</p>"

    "<h3>2.4 &nbsp; The four metrics</h3>"
    "<p>Given TP (correctly flagged anomalies), FP (false alarms), FN (missed anomalies) and TN "
    "(correctly ignored normals):</p>"
    + table(["Metric", "Formula", "The question it answers", "CARCI"], [
        ["Accuracy", "(TP+TN) / all", "How often is it right overall?", "0.845"],
        ["Precision", "TP / (TP+FP)", "When it raises an alarm, is it real?", "0.877"],
        ["Recall", "TP / (TP+FN)", "What fraction of anomalies did it catch?", "0.657"],
        ["F1", "harmonic mean of P and R", "The balance between the two", "0.751"],
    ])
    + "<p>Read CARCI's numbers as a sentence: \"When CARCI raises an alarm it is right about 88% of "
    "the time, but it only catches about 66% of the anomalies that exist.\" For a cost tool that "
    "trade-off is the right way round &mdash; a tool that cries wolf gets ignored.</p>"
    + note("Why accuracy alone is a trap",
           "<p>If only 5% of rows are anomalies, a model that flags nothing at all scores 95% "
           "accuracy. It is also completely useless. This is why precision and recall must always "
           "be reported alongside accuracy.</p>")
))


# ==========================================================================
# 3 - app.py
# ==========================================================================

EXCEPT_ORDER = """
except pd.errors.ParserError as exc:   # MUST come first
except ValueError as exc:              # ParserError is a subclass of this
except Exception as exc:               # last resort, never silent
"""

CHAPTER_3 = source_chapter(
    3, "app.py", "The user interface", "The user interface",
    "<h3>3.1 &nbsp; Purpose and concepts</h3>"
    "<p><strong>What it is:</strong> the entire Streamlit web application &mdash; upload box, "
    "buttons, charts, tables, expanders and download buttons. It is the only file a user ever "
    "interacts with directly.</p>"
    "<p><strong>What it is not:</strong> it contains no machine learning whatsoever. Not one line "
    "of model code. Every ML operation happens behind the single call to "
    "<code>build_analysis_result()</code> on line 253.</p>"

    + note("Teaching point",
           "<p>This is the clearest example of <em>separation of concerns</em> in the project. You "
           "could delete this file and replace Streamlit with a Flask API, a desktop app, or a "
           "command-line tool, and the detection logic would not change by a single character. When "
           "you design software, ask yourself: \"if I changed the interface, how much else would "
           "break?\" Here, the answer is nothing.</p>")

    + "<h4>The three-page wizard</h4>"
    "<p>The interface is a wizard, not a single scrolling page. <code>PAGES</code> at lines "
    "217&ndash;221 declares the three steps, and <code>st.session_state.page</code> records which "
    "one the user is on:</p>"
    + table(["Page", "Function", "What it shows"], [
        ["1 &mdash; Upload CSV", "<code>_show_upload_page()</code> (line 716)",
         "File uploader, Start Analysis, error messages"],
        ["2 &mdash; Anomaly Summary", "<code>_show_summary_page()</code> (line 633)",
         "Four metric tiles, daily trend chart, impact-by-service bar chart"],
        ["3 &mdash; Investigation Details", "<code>_show_investigation_page()</code> (line 661)",
         "Anomaly table, cost breakdowns, root cause cards, exports"],
    ])
    + "<p><code>_goto()</code> at line 296 is how navigation happens: it writes the new page number "
    "into session state and calls <code>st.rerun()</code>. Streamlit has no router &mdash; the "
    "whole script re-executes and the <code>if</code> chain at lines 785&ndash;790 draws whichever "
    "page the state names.</p>"

    "<h4>How the page flows</h4>"
    "<p><code>main()</code> at line 766 is the whole application. Read it first &mdash; everything "
    "else is a helper it calls:</p>"
    "<ol>"
    "<li>Inject the CSS (line 767).</li>"
    "<li>Set up four <em>session state</em> variables (769&ndash;776). Streamlit re-runs the entire "
    "script on every click, so ordinary Python variables would be wiped. Session state is how a "
    "value survives from one click to the next.</li>"
    "<li><strong>Guard the wizard</strong> (779&ndash;780). Pages 2 and 3 have nothing to show "
    "without a result, so a missing result forces the user back to page 1. Without this, a cleared "
    "analysis would leave the app rendering a page whose data no longer exists.</li>"
    "<li>Draw the header and the three-card step indicator (782&ndash;783).</li>"
    "<li>Route to the current page (785&ndash;790).</li>"
    "</ol>"
    "<p>Inside page 1, the sequence is the familiar one: draw the uploader (724&ndash;728), detect "
    "a file change (734&ndash;737), draw the two buttons (741&ndash;747), then run the analysis and "
    "advance to page 2 (749&ndash;751).</p>"

    "<h4>Three details worth pointing out to students</h4>"
    "<p><strong>1. The caching decorator (lines 245&ndash;253).</strong> "
    "<code>@st.cache_data</code> stores the result so that re-analysing the same file is instant. "
    "Critically, it is keyed on <code>file_bytes</code> &mdash; the actual <em>contents</em> &mdash; "
    "not the filename. If it were keyed on the name, two different files both called "
    "<code>data.csv</code> would collide and the second would silently show the first one's "
    "results. The cache also means navigating between pages 2 and 3 does not re-run the model, and "
    "does not call the LLM again.</p>"

    "<p><strong>2. Detecting a file change (lines 734&ndash;737).</strong> If the user selects a "
    "different file, any results still on screen belong to the old file and must be cleared. Note "
    "the condition <code>current_name is not None</code>: returning to page 1 from page 2 or 3 "
    "re-creates the uploader empty, and that must not be mistaken for the user removing the file.</p>"

    "<p><strong>3. The order of the except blocks (lines 701&ndash;709).</strong> This is a real bug "
    "that was fixed:</p>"
    + snippet(EXCEPT_ORDER)
    + "<p><code>ParserError</code> inherits from <code>ValueError</code>. Python checks "
    "<code>except</code> clauses top to bottom and takes the first match, so if "
    "<code>ValueError</code> came first it would swallow parser errors and the user would get the "
    "wrong message for a corrupt CSV. Order your exception handlers from most specific to most "
    "general.</p>"

    "<h4>Where the root cause appears</h4>"
    "<p><code>_show_anomaly_details()</code> at line 549 draws the \"Root Cause Analysis\" section "
    "on page 3, one expander per anomaly. Two things there are worth reading closely:</p>"
    "<ul>"
    "<li>Lines 555&ndash;566 print a caption naming the source of the wording &mdash; either "
    "<code>LLM (gemini-3.5-flash-lite)</code> or the deterministic template. This is the fastest "
    "way to tell at a glance whether the language model actually ran. See section 9.</li>"
    "<li>Lines 581&ndash;582 render the recommended action as its own bold line, but only in LLM "
    "mode. The template paragraph already ends with its own \"Recommended action:\" sentence, so "
    "printing it twice would be duplication.</li>"
    "</ul>"
    "<p>Three helpers draw the investigation itself, and each one returns immediately when its "
    "section is empty &mdash; which is what makes the same card work in both LLM and template "
    "mode:</p>"
    + table(["Helper", "Line", "Draws"], [
        ["<code>_show_headline()</code>", "497",
         "The suspected cause as a banner, coloured by severity"],
        ["<code>_show_likely_causes()</code>", "514",
         "Ranked hypotheses, each with a confidence chip and its evidence"],
        ["<code>_show_investigation_steps()</code>", "540",
         "The numbered checks that would confirm or eliminate them"],
    ])
    + "<p><code>SEVERITY_COLORS</code> and <code>CONFIDENCE_COLORS</code> (lines 226&ndash;239) hold "
    "the palettes. <code>SEVERITY_MARKS</code> exists because the collapsed expander title is plain "
    "text &mdash; no HTML renders there &mdash; so severity is carried into it as a short "
    "punctuation mark instead of a coloured badge.</p>"
    "<p>Note that <code>html.escape()</code> is applied again at lines 507, 531 and 533. The "
    "headline, cause and evidence strings are written by a language model and rendered as raw HTML, "
    "so they are untrusted input for exactly the same reason the filename is.</p>"

    + note("Security note",
           "<p>Line 309 calls <code>html.escape()</code> on the uploaded filename before displaying "
           "it. The upload box is rendered with <code>unsafe_allow_html=True</code>, and the "
           "filename is controlled by the user. Without escaping, a file named "
           "<code>&lt;script&gt;alert(1)&lt;/script&gt;.csv</code> would execute code in the "
           "browser. This is a cross-site scripting (XSS) vulnerability, and escaping is the "
           "fix.</p>")
)


# ==========================================================================
# 4 - schema.py
# ==========================================================================

CHAPTER_4 = source_chapter(
    4, "carci/schema.py", "Finding the right columns", "Finding the right columns",
    "<h3>4.1 &nbsp; Purpose and concepts</h3>"
    "<p><strong>The problem it solves:</strong> a real AWS Cost and Usage Report does not have a "
    "column called <code>cost</code>. It has <code>line_item_unblended_cost</code>. Or "
    "<code>lineitemunblendedcost</code>. Or <code>net_unblended_cost</code>. A student dataset "
    "might just say <code>amount</code>. If the rest of the program had to handle all of these, "
    "every single file would be full of if-statements.</p>"
    "<p>This file solves it once. It maps roughly ninety possible real-world column names onto "
    "eleven logical fields.</p>"

    "<h4>The three-stage matching strategy</h4>"
    "<p><code>detect_columns()</code> (line 155) tries progressively looser matching:</p>"
    "<ol>"
    "<li><strong>Normalise (line 127).</strong> <code>_normalize_name()</code> lowercases and strips "
    "every character that is not alphanumeric or underscore. So \"Line Item Unblended Cost\", "
    "\"line-item-unblended-cost\" and \"LineItemUnblendedCost\" all collapse to the same string.</li>"
    "<li><strong>Exact alias lookup (lines 159&ndash;162).</strong> Check the normalised name "
    "against the known alias list.</li>"
    "<li><strong>Token fallback (line 131).</strong> If nothing matched, look for a substring. Any "
    "column whose name contains \"cost\", \"unblended\", \"blended\", \"amount\" or \"ondemand\" is "
    "accepted as the cost column. This is what lets the system handle a CSV it has never seen "
    "before.</li>"
    "</ol>"

    "<h4>Required versus optional</h4>"
    "<p>Only three fields are required: <code>date</code>, <code>service</code> and "
    "<code>cost</code>. Without those, cost anomaly detection is meaningless, so "
    "<code>find_column()</code> raises a <code>ValueError</code> listing the columns it did find "
    "&mdash; a helpful error, not a crash. Everything else passes <code>required=False</code> and "
    "returns <code>None</code> when absent.</p>"

    + note("Teaching point",
           "<p><code>NormalizedColumns</code> (line 9) is a <code>@dataclass(frozen=True)</code>. "
           "\"Frozen\" means immutable &mdash; once created it cannot be modified. This is "
           "deliberate: the detected column mapping is a fact about the uploaded file, and nothing "
           "downstream should ever be able to change it by accident.</p>")
)


# ==========================================================================
# 5 - preprocessing.py
# ==========================================================================

REGION_PATTERN = """
"region": (
    df[cols.region].fillna("Unknown Region").astype(str)
    if cols.region        # did schema.py find this column?
    else "Unknown Region" # no - use a safe default for every row
),
"""

CHAPTER_5 = source_chapter(
    5, "carci/preprocessing.py", "Cleaning the data", "Cleaning the data",
    "<h3>5.1 &nbsp; Purpose and concepts</h3>"
    "<p><strong>Its one job:</strong> take the messy uploaded file plus the column mapping from "
    "<code>schema.py</code>, and return one predictable DataFrame with fixed column names and clean "
    "data types.</p>"
    "<p>Look at the shape of <code>preprocess_cur_data()</code>. It builds a brand-new DataFrame "
    "rather than modifying the old one, and every single field follows the same pattern:</p>"
    + snippet(REGION_PATTERN)
    + "<p>This is the mechanism behind \"missing optional columns produce a partial explanation "
    "rather than an error\". A file with no region column still analyses perfectly; the explanations "
    "simply say \"Unknown Region\".</p>"

    "<h4>The three cleaning rules</h4>"
    + table(["Line", "Rule", "Why"], [
        ["13", "<code>errors=\"coerce\"</code> on dates",
         "Unparseable dates become <code>NaT</code> instead of throwing an exception"],
        ["59", "<code>dropna(subset=[\"date\"])</code>",
         "A row with no valid date cannot be placed on a timeline, so it is removed"],
        ["61", "<code>cost &gt;= 0</code>",
         "Negative costs are AWS credits and refunds, not spending anomalies"],
    ])
    + "<p>Line 63 raises a clear error if nothing survives, rather than letting an empty DataFrame "
    "cause a confusing crash five files later.</p>"

    + note("Teaching point",
           "<p><code>errors=\"coerce\"</code> appears on every numeric and date conversion. It means "
           "\"if this value cannot be converted, produce a null instead of raising\". For "
           "user-uploaded data this is almost always what you want: one malformed cell in row 4,000 "
           "should not destroy the entire analysis.</p>")
)


# ==========================================================================
# 6 - shared.py
# ==========================================================================

CHAPTER_6 = source_chapter(
    6, "carci/shared.py", "Feature engineering and data splitting",
    "Feature engineering and data splitting",
    "<h3>6.1 &nbsp; Purpose and concepts</h3>"
    "<p>This file answers the most important question in any ML project: <strong>what numbers does "
    "the model actually look at?</strong> The answer is <code>FEATURE_COLUMNS</code> at line 10 "
    "&mdash; exactly seven values per row.</p>"
    + table(["Feature", "Where it comes from", "What it tells the model"], [
        ["<code>cost</code>", "raw", "How much this line item cost"],
        ["<code>usage_quantity</code>", "raw", "How much was used"],
        ["<code>autoscaling_count</code>", "raw", "How much scaling activity"],
        ["<code>data_transfer_gb</code>", "raw", "How much network transfer"],
        ["<code>cost_per_usage</code>", "<code>cost / (usage_quantity + 1)</code>",
         "Unit price. Catches \"paid a lot for very little\""],
        ["<code>transfer_per_cost</code>", "<code>data_transfer_gb / (cost + 1)</code>",
         "Transfer efficiency. Catches unusual data movement"],
        ["<code>daily_z</code>", "<code>add_daily_context()</code>",
         "Whether this row sits on a quiet day or a spike day"],
    ])
    + note("Why the + 1 in the denominators?",
           "<p>If <code>usage_quantity</code> is 0, then <code>cost / usage_quantity</code> is a "
           "division by zero, producing infinity, which breaks the scaler and then the model. Adding "
           "1 is a standard trick that guarantees a finite result while barely affecting large "
           "values. This is worth pointing out to students &mdash; the maths must survive every "
           "possible input, not just typical ones.</p>")

    + "<h4>Engineered features: the interesting part</h4>"
    "<p>The first four features are copied straight from the file. The last three are "
    "<em>engineered</em> &mdash; computed by combining other columns. This matters because an "
    "Isolation Forest splits on one feature at a time. It cannot discover the relationship \"cost is "
    "high relative to usage\" on its own. By computing <code>cost_per_usage</code> for it, we hand "
    "it that relationship as a single number it can split on directly.</p>"
    "<p><code>daily_z</code> (lines 91&ndash;118) deserves special attention. Every other feature is "
    "row-local &mdash; it describes one line item in isolation. But the project's goal is detecting "
    "unusual <em>daily</em> spending. So <code>add_daily_context()</code> totals the cost of every "
    "calendar day, converts those totals to z-scores, and gives every row on a given day the same "
    "value. Note lines 99&ndash;113: if there is no date column, or only one day, or zero variance, "
    "it degrades safely to 0.0 rather than crashing.</p>"

    "<h4>The three split functions &mdash; do not confuse them</h4>"
    + table(["Function", "Used by", "What it does"], [
        ["<code>prepare_train_test_features</code> (line 141)", "CLI evaluation",
         "Trains on 80% of normal rows only; tests on the other 20% of normals plus every anomaly"],
        ["<code>prepare_inference_features</code> (line 185)", "The web app",
         "Trains and scores on the same upload. Excludes labelled anomalies from training if a "
         "label column exists"],
        ["<code>prepare_external_test_features</code> (line 170)", "Two-file CLI mode",
         "Trains on file A, tests on all of file B &mdash; the cleanest setup"],
    ])
    + note("The single most important idea in this file",
           "<p>Look at lines 148&ndash;159. The training set contains <strong>only normal rows</strong>. "
           "The model never sees a single anomaly during training. It learns what normal looks like, "
           "then meets all the anomalies for the first time at test. This is what makes the reported "
           "scores honest. If anomalies were in the training set, the model could memorise them and "
           "the results would be meaningless.</p>")

    + "<h4>Notice what is missing</h4>"
    "<p><code>usage_type</code> is <strong>not</strong> in <code>FEATURE_COLUMNS</code>. In this "
    "dataset that column happens to give away the answer exactly. Because the Isolation Forest never "
    "sees it, the Isolation Forest results are trustworthy. See section 11 for the full story.</p>"
)


# ==========================================================================
# 7 - isolation_forest_model.py
# ==========================================================================

CHAPTER_7 = source_chapter(
    7, "carci/isolation_forest_model.py", "The machine learning model",
    "The machine learning model",
    "<h3>7.1 &nbsp; Purpose and concepts</h3>"
    "<p>This is the heart of the system. It contains the model, the scoring function used by the "
    "app, and the evaluation routine used from the command line.</p>"

    "<h4>How Isolation Forest works &mdash; explain it this way</h4>"
    "<p>Most anomaly detection algorithms build a picture of \"normal\" and measure distance from "
    "it. Isolation Forest does the opposite, and the intuition is beautifully simple:</p>"
    "<p><em>Pick a random feature. Pick a random split point. Cut the data in two. Repeat until "
    "every point is alone in its own box. Now count how many cuts each point needed.</em></p>"
    "<p>A point in the middle of a dense cluster is surrounded by neighbours, so it takes many cuts "
    "to isolate. A point far away from everything gets separated almost immediately. Anomalies are "
    "the points that are <em>easy to isolate</em>. Fewer cuts means more anomalous.</p>"
    "<p>The forest builds 1,000 such random trees and averages the path length over all of them. "
    "<code>decision_function()</code> returns that averaged score: low means anomalous, high means "
    "normal.</p>"

    "<h4>The model configuration (lines 52&ndash;59)</h4>"
    + table(["Parameter", "Value", "Meaning"], [
        ["<code>n_estimators</code>", "1000",
         "Number of random trees. More trees means a more stable score but slower training"],
        ["<code>contamination</code>", "0.05",
         "The assumed proportion of anomalies. This sets where the cut-off lands"],
        ["<code>max_samples</code>", "1.0", "Each tree sees 100% of the training rows"],
        ["<code>random_state</code>", "123",
         "Fixes the randomness so results reproduce exactly every run"],
    ])
    + note("contamination = 0.05 has a consequence students always miss",
           "<p>It does not mean \"5% of rows are anomalies\". It means <strong>the model will flag "
           "5% of rows no matter what you give it</strong>. Upload a perfectly clean file and it "
           "still flags 5%. The parameter defines where the cut-off sits, not how many anomalies "
           "exist.</p>")

    + "<h4>The threshold problem (lines 62&ndash;88)</h4>"
    "<p>The original code used a hardcoded cut-off of <code>-0.0034</code>. That is wrong, and "
    "understanding why teaches something important about ML systems.</p>"
    "<p><code>decision_function</code> scores are only meaningful <em>relative to the forest that "
    "produced them</em>. A different dataset produces a different forest, which produces a different "
    "score distribution. A constant tuned on one file is a meaningless number on another.</p>"
    "<p><code>_resolve_threshold()</code> fixes this by taking the 5% quantile of the training "
    "scores &mdash; recalibrating for every file. Read the docstring on lines 67&ndash;81: it is "
    "honest that scikit-learn's <code>offset_</code> already does this internally, so the rule is "
    "equivalent to <code>model.predict() == -1</code>. The gain is portability, not accuracy.</p>"

    "<h4>The two entry points</h4>"
    "<p><code>score_records()</code> (line 91) &mdash; used by the app. Fit, score, threshold, and "
    "optionally explain with SHAP. Note line 109: <code>anomaly_score</code> is the <em>negated</em> "
    "decision score, so that higher always means \"more anomalous\", which is more intuitive for "
    "display.</p>"
    "<p><code>run_model()</code> (line 155) &mdash; used by the CLI. This is the evaluation. Split, "
    "fit, calibrate, predict, then print four metrics for three different models.</p>"

    "<h4>SHAP attribution (lines 120&ndash;152)</h4>"
    "<p>The model says \"this row is anomalous\". SHAP says <em>why</em> &mdash; it assigns each of "
    "the seven features a number showing how much it pushed the score up or down. This is what turns "
    "a flag into an explanation, and it is the input the language model is later asked to put into "
    "words.</p>"
    "<p>Notice the <code>try/except</code> wrapping the whole thing. If SHAP is not installed or "
    "fails, line 142 falls back to a simple statistical measure: how many standard deviations each "
    "feature sits from the training median, scaled by the anomaly score. The app keeps working, and "
    "<code>attribution_method</code> honestly reports which method was used.</p>"

    + note("Performance warning",
           "<p>SHAP is by far the slowest part of the system &mdash; roughly 170 ms per row on a "
           "10,000-row file, which is about 28 minutes, or 99% of total runtime. Worse, per-row cost "
           "grows with the training set, because <code>max_samples=1.0</code> makes trees deeper on "
           "bigger files. The CLI evaluation does not run SHAP and is unaffected.</p>", "warn")

    + "<h4>Why compare against a baseline? (lines 191&ndash;200)</h4>"
    "<p>A model scoring 0.75 F1 sounds good, but good <em>compared to what?</em> A reviewer will "
    "always ask: could a simple rule do this? So the code implements the obvious rule &mdash; \"flag "
    "anything above the 90th percentile of cost\" &mdash; and scores it on the same test set. The "
    "model gets 0.751; the rule gets 0.473.</p>"
    "<p>Read the docstring: an earlier <code>mean + 2*std</code> rule scored exactly 0.0, and was "
    "replaced precisely because beating a rule that detects nothing proves nothing. <strong>Always "
    "compare against the strongest simple alternative, not the weakest.</strong></p>"
)


# ==========================================================================
# 8 - analysis.py
# ==========================================================================

PIPELINE = """
preprocess_cur_data()       clean the upload             (preprocessing.py)
        |
_score_input_rows()         run the model + SHAP         (isolation_forest_model.py)
        |
_attach_service_context()   compute per-service-day baselines
        |
_build_service_comparison() apply rules, build the records
        |                        |
        |                        +--> _apply_llm_explanations()   (llm_reasoning.py)
        |                             one Gemini call for the whole batch
        v
_build_daily_summary()      data for the trend chart
        |
_build_report_text()        the downloadable text report
"""

DETECTION_RULE = """
has_baseline  = service_day_count >= 2      # need another day to compare against
model_flagged = model_is_anomaly == 1       # the ML model said so
large_change  = percentage >= 75 AND impact >= $5   # the business rule said so

report if:  has_baseline AND (model_flagged OR large_change) AND impact > 0
"""

CHAPTER_8 = source_chapter(
    8, "carci/analysis.py", "From scores to explanations", "Business rules and orchestration",
    "<h3>8.1 &nbsp; Purpose and concepts</h3>"
    "<p>This is the largest file and the one that makes CARCI \"Root Cause Intelligence\" rather "
    "than just an anomaly detector. The model produces a number; this file turns it into a set of "
    "facts a finance manager can act on, and then hands those facts to "
    "<code>llm_reasoning.py</code> to be written up in English.</p>"

    "<h4>The pipeline: <code>build_analysis_result()</code> (line 466)</h4>"
    "<p>Read this function first. It orchestrates everything:</p>"
    + diagram(PIPELINE)

    + "<h4>The key idea: service-day aggregation (lines 102&ndash;138)</h4>"
    "<p>Read the docstring on lines 103&ndash;109 &mdash; it describes a real bug that was fixed. "
    "The original code compared each row against the average of all other rows. That is wrong, "
    "because a service which is <em>always</em> expensive would look anomalous on its priciest row "
    "even when nothing had changed.</p>"
    "<p>The fix aggregates to the <code>(service, date)</code> level and compares each service-day "
    "against the mean of <strong>that same service's other days</strong>. Now the question becomes "
    "the right one: <em>\"is AmazonEC2 more expensive today than AmazonEC2 usually is?\"</em></p>"

    "<h4>The detection rule (lines 147&ndash;150)</h4>"
    + snippet(DETECTION_RULE)
    + "<p>Two independent detectors joined by OR. The model catches strange <em>combinations</em> "
    "that no rule would express; the rule catches large obvious increases the model might miss. The "
    "<code>$5</code> floor stops the system reporting a rise from $0.02 to $0.05 &mdash; technically "
    "a 150% increase, but nobody cares.</p>"

    "<h4>The fallback (lines 153&ndash;159)</h4>"
    "<p>If nothing qualifies, rather than showing an empty screen the system displays the single "
    "highest-impact service-day marked <code>is_fallback = 1</code>. The UI labels it \"Reference "
    "only\" and it is <strong>excluded from the anomaly count</strong> (see line 475). This is good "
    "interface design: always show the user something, but never let informational content "
    "masquerade as a detection.</p>"

    "<h4>Deduplication (lines 164&ndash;166)</h4>"
    "<p>A service-day usually contains many rows. Without <code>drop_duplicates</code>, each one "
    "would produce its own identical card. The code sorts by anomaly score and keeps the "
    "highest-scoring row as the \"driver\" &mdash; one card per service-day, showing which specific "
    "line item caused it. Line 172 then caps the list at <code>MAX_ANOMALIES</code> (20), which is "
    "also the batch size the LLM is asked to handle.</p>"

    "<h4>Assembling the facts (lines 242&ndash;277)</h4>"
    "<p><code>_build_root_cause_text()</code> assembles an English paragraph from parts: what "
    "happened, how it compares to baseline, where it came from, why the system flagged it, and what "
    "to do. Note the three-way branch at lines 243&ndash;254 &mdash; the wording changes depending "
    "on whether the model flagged it, the business rule flagged it, or it is only a reference row. "
    "The system never claims the model detected something when it did not.</p>"
    "<p>Line 256 handles a subtle case: if a service has no previous spending day, the baseline is "
    "zero. Reporting \"a 100% increase\" would be misleading, so it says \"new spend\" instead.</p>"
    "<p><code>_recommendation_for()</code> (line 194) maps the usage type to concrete advice &mdash; "
    "data transfer issues get CDN advice, compute issues get instance-sizing advice. Simple keyword "
    "matching.</p>"
    "<p>Two neighbours do the same job for the other card fields. <code>_headline_for()</code> "
    "(line 207) writes a one-line summary, and <code>_severity_for()</code> (line 221) ranks the "
    "anomaly by money at stake and then by how sharp the rise was. Both are computed from the "
    "pipeline's own figures, so a severity exists even with the LLM switched off &mdash; and note "
    "what the template headline cannot do: it can only describe the <em>symptom</em>, because "
    "naming a probable <em>cause</em> is precisely the judgement no keyword rule can make.</p>"

    + note("This paragraph is now the fallback, not the product",
           "<p>In the current design the text built here is the <em>deterministic template</em>. It "
           "is what the user sees when no API key is configured or the network is down. When the "
           "language model is available, its wording replaces this paragraph. Both are always "
           "computed and kept, so the two can be compared side by side.</p>", "new")

    + "<h4>Handing over to the LLM (lines 343&ndash;382)</h4>"
    "<p><code>_apply_llm_explanations()</code> is the seam between the deterministic pipeline and "
    "the language model. It does three things, in this order:</p>"
    "<ol>"
    "<li><strong>Preserve the template first (lines 356&ndash;363).</strong> Every record copies its "
    "paragraph, advice and headline into <code>template_explanation</code>, "
    "<code>template_recommendation</code> and <code>template_headline</code>, and sets "
    "<code>explanation_method</code> to \"deterministic template\". This happens before any network "
    "call, so the deterministic text can never be lost. <code>likely_causes</code> and "
    "<code>investigation_steps</code> are set to empty lists here, because they have no template "
    "equivalent at all.</li>"
    "<li><strong>Call the model once (line 367).</strong> All records go in a single batched "
    "request. See section 9.</li>"
    "<li><strong>Overwrite only what came back (lines 371&ndash;382).</strong> Results are matched "
    "by index. A record the model did not answer for keeps its template text, and each individual "
    "field falls back to the pipeline's own value, so a reply that omits the headline or the "
    "severity is degraded rather than blank.</li>"
    "</ol>"
    "<p>Line 368 is the whole safety design in one statement: if <code>generate_explanations()</code> "
    "returns nothing, the function simply returns and the analysis proceeds unchanged. <strong>The "
    "app has no hard dependency on the API being reachable.</strong></p>"
    "<p><code>explanation_method</code> is copied into the result metadata at lines 489&ndash;493, "
    "which is what the caption on page 3 of the app reads.</p>"

    + note("Teaching point &mdash; this is the real product",
           "<p>The Isolation Forest says: <em>\"row 4,271 has a decision score of -0.0512.\"</em></p>"
           "<p>This file says: <em>\"AmazonECS cost $1,049.81 on 16 January against a normal "
           "baseline of $201.57, an increase of 421%, driven by one resource in ap-southeast-1.\"</em></p>"
           "<p>Same information. Only one of them is useful to a human. Translating model output "
           "into decisions is where most of the value in an applied ML system lives.</p>")
)


# ==========================================================================
# 9 - llm_reasoning.py  (new chapter)
# ==========================================================================

PAYLOAD_EXAMPLE = """
{
  "index": 0,
  "service": "AmazonEC2",
  "date": "13 January 2026",
  "observed_cost_usd": 2979.72,
  "baseline_cost_usd": 446.67,
  "increase_pct": 567.1,
  "impact_usd": 2533.05,
  "driver_line_item_cost_usd": 1011.65,
  "region": "ap-southeast-1",
  "region_share_pct": 72.01,
  "resource": "db-1cd8dd14-73b0-43ee-bcab-4831009223e3",
  "usage_type": "CryptoMiningTraffic",
  "tag": "AIResearch",
  "top_features": ["usage_quantity", "cost", "data_transfer_gb"],
  "feature_attribution": [
    {"feature": "usage_quantity",   "value": 16049.04, "shap_value": -2.3399},
    {"feature": "cost",             "value": 1011.65,  "shap_value": -2.2855},
    {"feature": "data_transfer_gb", "value": 770.18,   "shap_value": -2.2010}
  ],
  "attribution_method": "SHAP TreeExplainer",
  "model_flagged": true,
  "reference_only": false,
  "no_prior_baseline": false
}
"""

REPLY_EXAMPLE = """
{
  "index": 0,
  "headline": "Crypto-mining traffic on EC2 instance db-1cd8dd14",
  "severity": "critical",
  "explanation": "On 13 January 2026, AmazonEC2 spend surged by 567.10% to reach an
                  observed cost of 2979.72 USD ... (three more paragraphs)",
  "likely_causes": [
    {"cause":      "Compromised EC2 instance running unauthorized mining scripts",
     "confidence": "high",
     "evidence":   "usage_type is CryptoMiningTraffic with 16049.04 usage quantity
                    and 770.18 GB data transfer"},
    {"cause":      "Unintended deployment of heavy proof-of-work algorithms under
                    the AIResearch tag",
     "confidence": "medium",
     "evidence":   "Tag is AIResearch and ap-southeast-1 holds 72.01% region share"}
  ],
  "investigation_steps": [
    "Open the Amazon EC2 Console and inspect resource db-1cd8dd14-... in
     ap-southeast-1.",
    "Review VPC Flow Logs and CloudTrail for unexpected inbound connections or
     credential misuse on the instance.",
    "Check security group rules associated with the resource for overly
     permissive access."
  ],
  "recommended_action": "Immediately isolate and stop the compromised instance
                         db-1cd8dd14-..., revoke any compromised IAM credentials,
                         and perform a security audit of the AIResearch
                         environment."
}
"""

ENV_EXAMPLE = """
# .env at the project root - never commit this file
GEMINI_API_KEY=your-key-here

# Set to 0 to force the deterministic template instead of the LLM.
CARCI_LLM_REASONING=1
"""

CHAPTER_9 = source_chapter(
    9, "carci/llm_reasoning.py", "Writing the root cause", "The language model layer",
    "<h3>9.1 &nbsp; Purpose and concepts</h3>"
    "<p>This file writes the investigation the user actually reads. Everything before it in the "
    "pipeline produces numbers; this is the step that produces reasoning.</p>"
    "<p>It sends the anomaly facts computed by <code>analysis.py</code> to Google Gemini "
    "(<code>gemini-3.5-flash-lite</code>, line 43) over the REST API, and receives back a structured "
    "report per anomaly: a headline naming the suspected cause, a severity, a narrative explanation, "
    "ranked cause hypotheses with confidence and evidence, the checks that would confirm them, and a "
    "recommended action.</p>"

    + note("The idea that makes this safe: facts and hypotheses are different things",
           "<p>A root cause report has to do two incompatible things. It must quote figures with "
           "absolute fidelity, and it must speculate about causes &mdash; because the cause is never "
           "in the billing data. Treating those as one task is what makes language models dangerous "
           "in financial reporting.</p>"
           "<p>So the prompt splits them explicitly. <strong>Facts</strong> may only be repeated from "
           "the input; the model never calculates, re-rounds or invents a figure. "
           "<strong>Hypotheses</strong> are where the model is expected to reason past the data, but "
           "each one must be ranked, carry a confidence, cite the field it rests on, and be worded as "
           "a possibility rather than a finding.</p>"
           "<p>The result reads like an analyst wrote it, without the model ever being trusted with "
           "arithmetic.</p>")

    + "<h4>Where the key comes from</h4>"
    "<p><code>api_key()</code> (line 198) checks, in order, the <code>GEMINI_API_KEY</code> and "
    "<code>GOOGLE_API_KEY</code> environment variables, falling back to a <code>.env</code> file at "
    "the project root read by <code>_load_env_file()</code> (line 175). That loader is deliberately "
    "about twenty lines of plain Python rather than a dependency on <code>python-dotenv</code>, and "
    "it never overwrites a variable that is already set.</p>"
    + snippet(ENV_EXAMPLE)
    + "<p><code>is_enabled()</code> (line 207) makes the feature <strong>on by default whenever a "
    "key exists</strong>. Setting <code>CARCI_LLM_REASONING=0</code> forces the deterministic "
    "template instead, which is how you demonstrate the fallback path without deleting your key.</p>"

    "<h4>What is sent</h4>"
    "<p><code>_to_payload()</code> (line 219) reduces each anomaly record to the facts the model is "
    "allowed to talk about. This narrowing is a security and correctness decision, not a bandwidth "
    "one. Read the docstring on lines 220&ndash;226: passing the whole record would hand the model "
    "fields it has no business repeating, and <em>every extra key is a chance for it to state "
    "something the pipeline never computed</em>.</p>"
    "<p>Note also what is deliberately <em>absent</em>: the rule-based recommendation from "
    "<code>_recommendation_for()</code> is not included, so the action the model returns is its own "
    "reading of the facts rather than a rewrite of a keyword rule.</p>"
    "<p>One entry of the JSON array, taken from a real run:</p>"
    + diagram(PAYLOAD_EXAMPLE)

    + "<h4>The system prompt (lines 60&ndash;127)</h4>"
    "<p>The prompt is in three parts: the FACTS rules, the HYPOTHESES rules, and a specification of "
    "each field. Every rule exists to prevent a specific failure:</p>"
    + table(["Rule", "The failure it prevents"], [
        ["<em>Facts:</em> use only the numbers present in the input",
         "The model inventing, re-rounding or recomputing a figure &mdash; the single most damaging "
         "error in a billing report"],
        ["<em>Facts:</em> do not claim a detection that did not happen",
         "Presenting a <code>reference_only</code> row, or one the model did not flag, as a "
         "confirmed detection"],
        ["<em>Facts:</em> new spend is not an increase",
         "Describing a first-ever charge as a percentage rise against a zero baseline"],
        ["<em>Hypotheses:</em> ground every cause in a given field",
         "Plausible-sounding speculation with nothing behind it"],
        ["<em>Hypotheses:</em> rank them and state confidence",
         "Three guesses presented as though equally likely"],
        ["<em>Hypotheses:</em> never word a guess as a finding",
         "A reader acting on \"was caused by\" when the evidence only supports \"consistent with\""],
        ["<em>Fields:</em> headline names the cause, not the symptom",
         "Sixteen cards that all read \"service X cost increase\""],
        ["<em>Fields:</em> a specific mechanism, not a category",
         "\"Increased usage\", which is a restatement of the anomaly rather than an explanation"],
        ["<em>Fields:</em> three or four paragraphs, no markdown",
         "Headings and bullets rendering as literal asterisks inside a Streamlit expander"],
    ])

    + "<h4>Forcing a machine-readable reply (lines 132&ndash;173, 293&ndash;300)</h4>"
    "<p>The request sets <code>responseMimeType: application/json</code> together with an explicit "
    "<code>responseSchema</code>. The schema requires every field above, and constrains "
    "<code>severity</code> and <code>confidence</code> to enumerations, so the UI can colour a badge "
    "from the value without guarding against a word it has no palette for.</p>"
    "<p>This matters more than it looks. Without it, the reply is prose that has to be scraped with "
    "regular expressions, and every change in the model's phrasing breaks the parser. With it, the "
    "reply is parsed by <code>json.loads()</code> and the structure is guaranteed by the API rather "
    "than hoped for.</p>"
    "<p><code>temperature</code> is set to 0.2 (line 298). Even for hypothesis generation this stays "
    "low: the creativity wanted here is domain reasoning, not linguistic variety, and drift at higher "
    "temperatures reads as invented numbers.</p>"
    "<p><code>MAX_OUTPUT_TOKENS</code> (line 47) is 32768. The single paragraph this layer originally "
    "returned fit comfortably in 8192; a full investigation for twenty anomalies runs to roughly "
    "8,000 output tokens on its own, and a truncated reply loses whole records.</p>"

    "<h4>What comes back</h4>"
    + diagram(REPLY_EXAMPLE)
    + "<p><code>generate_explanations()</code> (line 367) parses this into a dictionary keyed by "
    "<code>index</code>, which is how each investigation finds its way back to the anomaly it "
    "describes.</p>"

    "<h4>Trusting the reply as little as possible (lines 324&ndash;364)</h4>"
    "<p>The schema guarantees the <em>shape</em> of the reply, not its <em>content</em>. Three small "
    "cleaners sit between the API and the UI:</p>"
    "<ul>"
    "<li><code>_clean_choice()</code> (line 324) drops any severity or confidence that is not one of "
    "the expected words, rather than passing an unknown string to a UI that colours a badge from "
    "it.</li>"
    "<li><code>_clean_causes()</code> (line 335) discards any hypothesis missing either its mechanism "
    "or its evidence. A cause with no evidence is exactly the unsupported speculation the prompt "
    "forbids, so it never reaches the screen.</li>"
    "<li><code>_clean_steps()</code> (line 361) strips blanks and caps the list.</li>"
    "</ul>"
    "<p>A record whose <code>explanation</code> came back empty is skipped entirely, so it keeps its "
    "template text instead of rendering as a half-filled card.</p>"

    + note("Teaching point &mdash; validate at the boundary",
           "<p>The schema is enforced by someone else's server. These cleaners are the first code you "
           "control that touches the reply, and they are where the assumption \"the response is "
           "well-formed\" gets checked instead of trusted. Treat any external API the same way, "
           "including one whose contract you believe you have pinned down.</p>")

    + "<h4>Batching (line 54)</h4>"
    "<p><code>MAX_RECORDS_PER_CALL = 20</code>, and all twenty anomalies travel in a single request. "
    "The comment states the reason plainly: twenty separate requests would cost twenty times the "
    "latency for the same work. This also matches <code>MAX_ANOMALIES</code> in "
    "<code>analysis.py</code>, so a full page of results is always one API call.</p>"

    "<h4>Failure handling &mdash; read this part twice</h4>"
    "<p><code>_call_gemini()</code> (line 269) retries once, and only for the transient status codes "
    "429, 500 and 503 (line 309). A 400 or a 403 means the request or the key is wrong; retrying "
    "those just doubles the wait before the same failure.</p>"
    "<p>Lines 405&ndash;409 handle a case that is easy to miss: a safety block returns HTTP 200 with "
    "no content parts at all. The code checks <code>finishReason</code> <em>before</em> touching "
    "<code>parts[0]</code>, so a blocked response produces a readable diagnostic instead of an "
    "<code>IndexError</code>. <code>MAX_TOKENS</code> is treated as recoverable, because a truncated "
    "reply may still contain usable entries.</p>"
    "<p>Every failure path sets <code>_LAST_ERROR</code> (line 58) and returns <code>None</code>. "
    "Read the docstring on lines 375&ndash;377:</p>"
    "<p><em>\"None is not an error condition. It is the normal signal that the caller should keep the "
    "deterministic template text.\"</em></p>"

    + note("Teaching point &mdash; graceful degradation",
           "<p>There are five separate ways this layer can produce nothing: no key, the feature "
           "switched off, a network failure, an HTTP error, and an unparseable reply. All five lead "
           "to the same outcome &mdash; the user gets the template paragraph and the app keeps "
           "working. None of them raises.</p>"
           "<p>The counterpart is that a silent fallback is invisible, which is why "
           "<code>last_error()</code> (line 215) exists and why the app prints which method wrote "
           "the text. <strong>Degrade quietly, but always leave a way to find out that you "
           "did.</strong></p>"
           "<p>Note what the fallback costs. The narrative, headline and severity all have template "
           "equivalents, so they survive. The ranked hypotheses and investigation steps do not "
           "&mdash; naming a probable cause is a judgement no keyword rule can make. Offline, those "
           "sections are simply absent from the card rather than filled with something weaker.</p>")

    + "<h4>How to check it is actually working</h4>"
    "<p>Because the fallback is silent by design, \"the explanations look fine\" is not evidence "
    "that the model ran. Three checks, in increasing order of certainty:</p>"
    "<ol>"
    "<li><strong>The caption on page 3 of the app.</strong> It reads either <em>\"Explanations "
    "written by LLM (gemini-3.5-flash-lite)\"</em> or <em>\"Explanations from the deterministic "
    "template\"</em>.</li>"
    "<li><strong>The Recommended action line.</strong> It is only rendered as a separate bold line "
    "in LLM mode. In template mode the advice sits inside the paragraph.</li>"
    "<li><strong>Inspect the result directly.</strong> "
    "<code>result[\"metadata\"][\"explanation_method\"]</code> names the source, and "
    "<code>llm_reasoning.last_error()</code> explains any failure.</li>"
    "</ol>"

    + note("Cost and privacy &mdash; worth stating in a report",
           "<p>The billing figures for up to twenty anomalies leave the machine and are sent to a "
           "third-party API. A measured batch of sixteen anomalies costs roughly 7,700 input tokens "
           "and 8,000 output tokens. No raw CSV is uploaded and no credentials travel with it, but "
           "resource identifiers and tag names do. For coursework this is fine; for a real finance "
           "deployment it is a decision that needs to be made deliberately, and the "
           "<code>CARCI_LLM_REASONING=0</code> switch exists so it can be turned off.</p>", "warn")
)


# ==========================================================================
# 10 - reporting.py
# ==========================================================================

CHAPTER_10 = source_chapter(
    10, "carci/reporting.py", "Building the exports", "Text and CSV exports",
    "<h3>10.1 &nbsp; Purpose and concepts</h3>"
    "<p>The smallest and simplest file. It converts the analysis result into the two downloadable "
    "formats.</p>"
    "<p><code>build_report_text()</code> &mdash; note line 7. If the analysis already produced a "
    "<code>report_text</code> (which <code>analysis.py</code> does), it returns that directly. The "
    "loop below is only a fallback for results built some other way. This is defensive programming: "
    "the function works correctly regardless of which path produced its input.</p>"
    "<p><code>build_report_dataframe()</code> &mdash; produces the \"Detailed CSV\" in long format: "
    "one fact per row, with section, metric and value columns, including per-feature SHAP "
    "contributions. Long format is harder to read directly but far easier to filter and pivot in "
    "Excel, which is what a finance analyst will actually do with it.</p>"
    "<p>Both exports carry whichever explanation the analysis produced. A report downloaded with the "
    "LLM enabled contains the model's wording; the same file analysed offline contains the template "
    "wording. The numbers are identical either way.</p>"
)


# ==========================================================================
# 11 - How the evaluation works
# ==========================================================================

EVALUATION = """
dataset.csv  (10,000 rows: 9,000 normal + 1,000 anomaly)
      |
 1.   add_engineered_features()   ->  build the 7 features
      |
 2.   SPLIT   train = 7,200   80% of the NORMAL rows only, no anomalies
              test  = 2,800   1,800 held-out normals + all 1,000 anomalies
      |
 3.   StandardScaler   fit on train, then transform test
      |
 4.   IsolationForest(1000 trees).fit(x_train)
      |
 5.   threshold = 5% quantile of the TRAINING scores      -> 0.000000
      |
 6.   y_pred = decision_function(x_test) < threshold
      |
 7.   compare y_pred against the true labels
      -> Accuracy, Precision, Recall, F1
"""

CHAPTER_11 = chapter(11, "How the evaluation works", (
    "<p>Run it with:</p>"
    + snippet("python -m carci.isolation_forest_model dataset.csv")
    + "<p>This calls <code>run_model()</code> in <code>isolation_forest_model.py</code>, which "
    "performs seven steps:</p>"
    + diagram(EVALUATION)
    + note("Why step 2 is the one that matters",
           "<p>The anomalies are removed from the training set entirely. The model learns only what "
           "normal looks like, and meets all 1,000 anomalies for the first time during testing. If "
           "the anomalies were in the training data, the model could memorise them and the scores "
           "would be worthless. When you review any ML project, this is the first thing to "
           "check.</p>")

    + "<h3>11.1 &nbsp; The results</h3>"
    + table(["Model", "Accuracy", "Precision", "Recall", "F1"], [
        ["Isolation Forest", "0.845", "0.877", "0.657", "0.751"],
        ["Cost percentile baseline", "0.708", "0.665", "0.367", "0.473"],
        ["Gradient Boosting (5-fold CV)", "1.000", "1.000", "1.000", "1.000"],
    ])
    + "<p>Averaged over 10 different random splits the Isolation Forest scores F1 = 0.748 &plusmn; "
    "0.004. That small standard deviation is important: it proves the result is stable and not a "
    "lucky split. Always report a spread, never a single number.</p>"

    "<h3>11.2 &nbsp; The perfect score is a bug, not an achievement</h3>"
    "<h4>Label leakage &mdash; the most valuable lesson in this project</h4>"
    "<p>The Gradient Boosting row scores a flawless 1.000 on every metric. That is not a good model. "
    "It is a broken experiment.</p>"
    "<p>The <code>usage_type</code> column in this dataset maps <strong>perfectly</strong> onto the "
    "label: <code>NormalUsage</code>, <code>BurstUsage</code>, <code>BackupWindow</code> and "
    "<code>BatchJob</code> are 100% normal, while <code>SuspiciousSpike</code>, "
    "<code>CryptoMiningTraffic</code>, <code>RunawayJob</code>, <code>MassiveDataTransfer</code>, "
    "<code>UnauthorizedScaling</code>, <code>SubtleCostDrift</code> and "
    "<code>MisconfiguredTagging</code> are 100% anomaly, with no overlap at all. Gradient Boosting "
    "uses that column, so it simply reads the answer instead of detecting anything.</p>"
    "<p>The Isolation Forest is <strong>unaffected</strong>, because <code>usage_type</code> is not "
    "in <code>FEATURE_COLUMNS</code> &mdash; it only ever sees the seven numeric features.</p>"
    + note("The lesson: treat a perfect score as a bug report",
           "<p>Real problems are never solved perfectly. When you see 1.000, go looking for the "
           "leak.</p>")

    + "<h3>11.3 &nbsp; Testing your own design decisions</h3>"
    "<p><code>daily_z</code> was added to give the model day-level context. Does it actually help? "
    "Testing all four combinations over the same 10 splits:</p>"
    + table(["Features used", "Fixed threshold", "Calibrated threshold"], [
        ["6 features (no <code>daily_z</code>)", "0.759", "0.760"],
        ["7 features (with <code>daily_z</code>)", "0.748", "0.748"],
    ])
    + "<p>Two honest conclusions. The threshold change is score-neutral &mdash; its value is "
    "portability between files, not accuracy. And <code>daily_z</code> actually costs about 0.012 F1 "
    "on this dataset. It helps when anomalies cluster onto a few days, but this file spreads 1,000 "
    "anomalies across 206 days, so daily totals barely move and the feature mostly dilutes the other "
    "six.</p>"
    + note("Teaching point",
           "<p>This result is unflattering, and it is reported anyway. Testing your own ideas and "
           "publishing the answer even when it contradicts you is what separates engineering from "
           "advocacy. An examiner will trust every other number in a report that contains a result "
           "like this one.</p>")
))


# ==========================================================================
# 12 - Known limitations
# ==========================================================================

CHAPTER_12 = chapter(12, "Known limitations", (
    "<ol>"
    "<li><strong>Recall is 0.657</strong> &mdash; roughly a third of anomalies are missed. Be "
    "explicit about this rather than letting the F1 score imply more.</li>"
    "<li><strong>SHAP is slow.</strong> About 170 ms per row: 28 minutes for a 10,000-row file, some "
    "99% of total runtime. The app appears frozen for the duration. Explaining only the rows "
    "actually displayed would fix it.</li>"
    "<li><strong><code>contamination = 0.05</code> guarantees false positives.</strong> A perfectly "
    "clean file still gets 5% of its rows flagged. On <code>dataset.csv</code> the app flags 1,107 "
    "of 10,000 rows: 450 false positives (5% of the 9,000 normal training rows) plus the 657 "
    "anomalies genuinely caught.</li>"
    "<li><strong>The model is fitted on the file it scores</strong> in app mode. Standard for "
    "unsupervised detection with no training corpus, but it means the forest sees the anomalies it "
    "is hunting.</li>"
    "<li><strong>The test set is 36% anomalies</strong> against the file's true 10%, which inflates "
    "precision for every model in the comparison table.</li>"
    "<li><strong>No model persistence.</strong> Nothing is saved to disk; the forest is rebuilt on "
    "every single run.</li>"
    "<li><strong>The explanation depends on a third-party API.</strong> The wording the user reads "
    "comes from Gemini. The fallback keeps the app working offline, but the two versions do not read "
    "alike, so output is not byte-reproducible between runs or between machines.</li>"
    "<li><strong>The fallback is silent.</strong> An expired key or a blocked network produces "
    "template text and no error dialog. The caption on page 3 is the only thing that distinguishes "
    "them, and a reader who does not know to look will not notice.</li>"
    "<li><strong>Prompt adherence is not enforced.</strong> The system prompt asks for three or four "
    "short paragraphs; the model frequently returns one. Nothing validates the returned prose "
    "against the rules &mdash; only its JSON shape is guaranteed by the schema.</li>"
    "<li><strong>Only the first 20 anomalies are explained.</strong> "
    "<code>MAX_RECORDS_PER_CALL</code> caps the batch, which is invisible when "
    "<code>MAX_ANOMALIES</code> is also 20, but would silently leave records unexplained if that cap "
    "were raised.</li>"
    "</ol>"
))


# ==========================================================================
# 13 - Glossary
# ==========================================================================

GLOSSARY = [
    ["Anomaly", "A data point that does not fit the pattern of the rest"],
    ["Baseline", "What is normal. Here: the mean of a service's other days"],
    ["Contamination", "The assumed proportion of anomalies; sets the cut-off"],
    ["CUR", "Cost and Usage Report &mdash; AWS's detailed billing export"],
    ["<code>decision_function</code>", "The raw score. Low means anomalous"],
    ["Feature", "One number describing a row that the model can use"],
    ["Feature engineering", "Creating new features by combining existing ones"],
    ["F1 score", "The harmonic mean of precision and recall"],
    ["Graceful degradation", "Losing a feature without losing the system, as when the LLM is "
                             "unreachable and the template is used instead"],
    ["Label leakage", "When a feature secretly contains the answer"],
    ["LLM", "Large language model. Here Gemini, used only to word figures the pipeline computed"],
    ["Overfitting", "Memorising the training data instead of learning the pattern"],
    ["Precision", "Of everything flagged, what fraction was truly anomalous"],
    ["Prompt", "The instructions sent to a language model. Here split into a system prompt of "
               "rules and a user message of anomaly facts"],
    ["<code>random_state</code>", "A fixed seed so random results reproduce exactly"],
    ["Recall", "Of all true anomalies, what fraction was found"],
    ["Response schema", "A structure the API is required to return, making the reply parseable "
                        "instead of scraped"],
    ["SHAP", "A method assigning each feature a contribution to one prediction"],
    ["<code>StandardScaler</code>", "Rescales features to mean 0, standard deviation 1"],
    ["Temperature", "How much randomness a language model uses when choosing words. 0.2 here"],
    ["Unsupervised", "Learning without labelled answers"],
    ["z-score", "How many standard deviations a value sits from the mean"],
]

CHAPTER_13 = chapter(13, "Glossary", table(["Term", "Meaning"], GLOSSARY))


# ==========================================================================
# 14 - Questions to test understanding
# ==========================================================================

QUESTIONS = [
    "Why can the web app not report an accuracy score?",
    "Why are anomalies removed from the training set?",
    "A clean file with no anomalies still produces flags. Why is that expected?",
    "Why is <code>cost / (usage_quantity + 1)</code> written with the <code>+ 1</code>?",
    "Gradient Boosting scored 1.000. Why is that bad news?",
    "Why must <code>ParserError</code> be caught before <code>ValueError</code>?",
    "Why compare against a 90th-percentile cost rule at all?",
    "Why is comparing a row against its own service's other days better than comparing it against "
    "every other row?",
    "Precision is 0.877 and recall is 0.657. For a cost alerting tool, is that the right trade-off? "
    "Argue both sides.",
    "SHAP takes 28 minutes on 10,000 rows. Propose two different fixes and give the drawback of each.",
    "The language model is given the anomaly figures but is forbidden from calculating anything. "
    "Why is that restriction the single most important rule in the prompt?",
    "<code>_to_payload()</code> sends nineteen named fields rather than the whole record. Give two "
    "distinct reasons why sending less is safer.",
    "<code>generate_explanations()</code> returns <code>None</code> on failure instead of raising. "
    "Defend that choice, then argue against it.",
    "A user reads a root cause paragraph and finds it useful. What evidence would you need before "
    "concluding that the language model produced it?",
    "The reply is constrained by a <code>responseSchema</code>. What class of bug does that "
    "eliminate, and what class does it leave untouched?",
]

CHAPTER_14 = chapter(14, "Questions to test understanding", (
    "<ol>" + "".join("<li>{}</li>".format(q) for q in QUESTIONS) + "</ol>"
    + '<p class="small">Questions 11 to 15 cover the language model layer described in section 9.</p>'
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
    CHAPTER_12,
    CHAPTER_13,
    CHAPTER_14,
]
