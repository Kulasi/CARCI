from __future__ import annotations

import html
import io

import pandas as pd
import plotly.express as px
import streamlit as st

from carci.analysis import build_analysis_result
from carci.reporting import build_report_dataframe


st.set_page_config(
    page_title="CARCI - Cost Anomaly Root Cause Intelligence",
    page_icon="C",
    layout="wide",
)


PAGE_CSS = """
<style>
body {
    background: linear-gradient(135deg, #f8fafc 0%, #ecfeff 100%);
}
header[data-testid="top-bar"],
.stApp {
    background: transparent !important;
}
.carci-header {
    border-radius: 12px;
    background: linear-gradient(90deg, #047857 0%, #0f766e 100%);
    color: white;
    padding: 1.9rem 2.1rem;
    box-shadow: 0 22px 48px rgba(15, 23, 42, 0.08);
    margin-bottom: 1.4rem;
}
.carci-header h1 {
    margin: 0;
    font-size: 2.6rem;
    font-weight: 800;
    letter-spacing: 0.01em;
}
.carci-header .carci-subtitle {
    margin: 0.9rem 0 0;
    font-size: 1.02rem;
    font-weight: 700;
    color: #ffffff;
}
.carci-header .carci-tagline {
    margin: 0.45rem 0 0;
    color: #d1fae5;
    font-size: 0.95rem;
}
/* Step indicator: one card per page, the active one gets the green rail. */
.step-card {
    border: 1px solid #e2e8f0;
    border-left: 4px solid #e2e8f0;
    border-radius: 8px;
    background: #ffffff;
    padding: 0.85rem 1.1rem;
    height: 100%;
}
.step-card.active {
    border-left-color: #0f766e;
    background: #ecfdf5;
}
.step-card .step-num {
    margin: 0;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #64748b;
}
.step-card.active .step-num {
    color: #0f766e;
}
.step-card .step-name {
    margin: 0.35rem 0 0;
    font-size: 1rem;
    font-weight: 700;
    color: #0f172a;
}
.carci-eyebrow {
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #0f766e;
    margin: 1.4rem 0 0.2rem;
}
.carci-page-title {
    margin: 0.1rem 0 0.6rem;
    font-size: 2.1rem;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.2;
}
.carci-page-note {
    margin: 0 0 1.1rem;
    color: #475569;
    font-size: 0.95rem;
    max-width: 62rem;
}
.carci-card-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0.1rem 0 0.2rem;
}
.carci-card {
    border-radius: 12px;
    background: white;
    padding: 1.25rem;
    box-shadow: 0 14px 36px rgba(15, 23, 42, 0.05);
    border: 1px solid #e2e8f0;
    margin-bottom: 1rem;
}
.carci-upload-box {
    border: 2px dashed #cbd5e1;
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
    background: #f8fafc;
    margin-bottom: 1rem;
}
.upload-label {
    margin: 0;
    color: #334155;
    font-size: 0.95rem;
}
.upload-name {
    margin: 0.4rem 0 0;
    font-size: 1.05rem;
    font-weight: 700;
    color: #0f172a;
}
.carci-small-note {
    color: #475569;
    margin-top: 0.5rem;
}
/* Metric tiles rendered as bordered cards, matching the summary page. */
div[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1rem 1.15rem;
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
}
div[data-testid="stMetric"] label p {
    color: #475569;
    font-size: 0.9rem;
}
div[data-testid="stMetricValue"] {
    font-size: 2rem;
    font-weight: 700;
    color: #0f172a;
}
/* Root cause card internals: headline banner, ranked hypotheses, evidence. */
.rca-headline {
    border: 1px solid;
    border-radius: 8px;
    padding: 0.65rem 0.85rem;
    margin-bottom: 0.9rem;
}
.rca-severity {
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 0.11em;
    margin-right: 0.6rem;
}
.rca-headline-text {
    font-size: 1.02rem;
    font-weight: 700;
    color: #0f172a;
}
.rca-cause {
    border-left: 3px solid #e2e8f0;
    padding: 0.15rem 0 0.15rem 0.75rem;
    margin: 0 0 0.7rem;
}
.rca-cause-head {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    flex-wrap: wrap;
}
.rca-rank {
    font-size: 0.78rem;
    font-weight: 800;
    color: #94a3b8;
}
.rca-chip {
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding: 0.1rem 0.45rem;
    border-radius: 999px;
    white-space: nowrap;
}
.rca-cause-text {
    font-size: 0.95rem;
    font-weight: 600;
    color: #0f172a;
}
.rca-evidence {
    margin: 0.25rem 0 0;
    font-size: 0.86rem;
    color: #475569;
}
</style>
"""


PAGES = {
    1: ("Step 1", "Upload CSV"),
    2: ("Step 2", "Anomaly Summary"),
    3: ("Step 3", "Investigation Details"),
}

# Severity and confidence are ranked words, so they are coloured on one warm-to-cool
# scale rather than by hue alone. The mark prefixes the collapsed expander title,
# where no HTML can be rendered.
SEVERITY_COLORS = {
    "critical": {"bg": "#fef2f2", "line": "#fecaca", "text": "#b91c1c"},
    "high": {"bg": "#fff7ed", "line": "#fed7aa", "text": "#c2410c"},
    "medium": {"bg": "#fefce8", "line": "#fde68a", "text": "#a16207"},
    "low": {"bg": "#f8fafc", "line": "#e2e8f0", "text": "#475569"},
}
SEVERITY_MARKS = {"critical": "!!!", "high": "!!", "medium": "!", "low": "·"}

CONFIDENCE_COLORS = {
    "high": {"bg": "#dcfce7", "text": "#15803d"},
    "medium": {"bg": "#fef9c3", "text": "#a16207"},
    "low": {"bg": "#f1f5f9", "text": "#64748b"},
}


def load_uploaded_csv(uploaded_file) -> pd.DataFrame:
    return pd.read_csv(uploaded_file, skipinitialspace=True)


@st.cache_data(show_spinner=False, max_entries=4)
def analyze_csv_bytes(file_bytes: bytes) -> dict:
    """Run the pipeline against raw upload bytes.

    Keyed on the bytes themselves, so re-running the same file is instant and
    two different uploads never collide in the cache.
    """
    raw_df = pd.read_csv(io.BytesIO(file_bytes), skipinitialspace=True)
    return build_analysis_result(raw_df)


def _show_header() -> None:
    st.markdown(
        """
        <div class="carci-header">
            <h1>CARCI</h1>
            <p class="carci-subtitle">Cost Anomaly Root Cause Intelligence</p>
            <p class="carci-tagline">AWS billing anomaly detection, root-cause analysis, and recommended cost actions.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _show_steps(current_page: int) -> None:
    """Three-card progress strip; the current page's card is highlighted."""
    columns = st.columns(len(PAGES))
    for column, (number, (step_label, step_name)) in zip(columns, PAGES.items()):
        state = "step-card active" if number == current_page else "step-card"
        column.markdown(
            f"""
            <div class="{state}">
                <p class="step-num">{step_label}</p>
                <p class="step-name">{step_name}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _show_section_title(eyebrow: str, title: str, note: str) -> None:
    st.markdown(
        f"""
        <p class="carci-eyebrow">{eyebrow}</p>
        <p class="carci-page-title">{title}</p>
        <p class="carci-page-note">{note}</p>
        """,
        unsafe_allow_html=True,
    )


def _goto(page: int) -> None:
    st.session_state.page = page
    st.rerun()


def _reset_analysis() -> None:
    st.session_state.analysis_result = None
    st.session_state.analysis_error = None


def _show_upload_state(uploaded_file) -> None:
    if uploaded_file:
        # Escaped: the filename is user-controlled and this block renders as raw HTML.
        safe_name = html.escape(uploaded_file.name)
        st.markdown(
            f"""
            <div class='carci-upload-box'>
                <p class='upload-label'>Selected file</p>
                <p class='upload-name'>{safe_name}</p>
                <p class='carci-small-note'>Ready to analyze. Click Start Analysis to continue.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class='carci-upload-box'>
                <p class='upload-label'>No file selected yet</p>
                <p class='upload-name'>Upload an AWS CUR-style CSV file to begin.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _anomaly_table(result: dict) -> pd.DataFrame:
    rows = result["service_comparison"]
    if not rows:
        return pd.DataFrame()

    table = pd.DataFrame(rows)
    # Costs are now service-day totals, so the headers say so explicitly.
    table["Status"] = [
        "Reference only" if record["is_fallback"] else "Detected"
        for record in rows
    ]
    table = table.rename(
        columns={
            "service_name": "Service",
            "date": "Date",
            "anomaly_value": "Service Day Cost",
            "driver_row_cost": "Driver Row Cost",
            "normal_value": "Normal Daily Cost",
            "impact_value": "Impact",
            "percentage": "Increase %",
            "region": "Region",
            "resource": "Resource",
            "tag": "Tag",
            "usage_type": "Usage Type",
            "model_anomaly_score": "Anomaly Score",
            "model_flag": "Model Flag",
        }
    )
    return table[
        [
            "Service",
            "Date",
            "Status",
            "Service Day Cost",
            "Driver Row Cost",
            "Normal Daily Cost",
            "Impact",
            "Increase %",
            "Region",
            "Resource",
            "Tag",
            "Usage Type",
            "Anomaly Score",
            "Model Flag",
        ]
    ]


def _show_metrics(result: dict) -> None:
    metadata = result["metadata"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows analyzed", f"{metadata['row_count']:,}")
    col2.metric("Services", f"{metadata['service_count']:,}")
    col3.metric("Detected anomalies", f"{metadata['anomaly_count']:,}")
    col4.metric("Total cost", f"${metadata['total_cost']:,.2f}")
    st.caption(f"Date range: {metadata['date_range']} | Attribution: {metadata['attribution_method']}")

    if metadata["anomaly_count"] == 0 and metadata["shown_count"] > 0:
        st.warning(
            "No service-day crossed the anomaly threshold. The single entry below is the "
            "highest-impact service-day, shown for reference only."
        )
    if metadata["truncated"]:
        st.info(
            f"{metadata['total_found']} service-days qualified as anomalies. "
            f"Showing the {metadata['shown_count']} highest-priority ones."
        )


def _show_charts(result: dict, anomaly_table: pd.DataFrame) -> None:
    daily_df = pd.DataFrame(result["daily_summary"])
    left, right = st.columns(2)

    with left:
        with st.container(border=True):
            st.markdown("<p class='carci-card-title'>Daily Cost Trend</p>", unsafe_allow_html=True)
            if daily_df.empty:
                st.info("No daily cost data available.")
            else:
                fig = px.line(daily_df, x="date", y="cost", markers=True)
                fig.update_traces(
                    line={"color": "#0f766e", "width": 2},
                    marker={"size": 6, "color": "#0f766e"},
                    showlegend=False,
                )
                anomaly_days = daily_df[daily_df["has_anomaly"]]
                if not anomaly_days.empty:
                    fig.add_scatter(
                        x=anomaly_days["date"],
                        y=anomaly_days["cost"],
                        mode="markers",
                        marker={"size": 11, "color": "#dc2626"},
                        name="Anomaly day",
                    )
                fig.update_layout(
                    height=340,
                    margin={"l": 20, "r": 20, "t": 30, "b": 20},
                    xaxis_title="Date",
                    yaxis_title="Cost",
                    yaxis_tickprefix="$",
                    plot_bgcolor="white",
                    legend={
                        "orientation": "h",
                        "yanchor": "bottom",
                        "y": 1.02,
                        "xanchor": "right",
                        "x": 1,
                    },
                )
                fig.update_xaxes(showgrid=False)
                fig.update_yaxes(gridcolor="#e2e8f0")
                st.plotly_chart(fig, use_container_width=True)

    with right:
        with st.container(border=True):
            st.markdown(
                "<p class='carci-card-title'>Top Anomaly Impact by Service</p>",
                unsafe_allow_html=True,
            )
            if anomaly_table.empty:
                st.info("No anomaly rows were produced for this upload.")
            else:
                service_fig = px.bar(
                    anomaly_table.head(10),
                    x="Impact",
                    y="Service",
                    orientation="h",
                )
                service_fig.update_traces(
                    marker_color="#2f54eb",
                    texttemplate="$%{x:,.0f}",
                    textposition="outside",
                    cliponaxis=False,
                )
                service_fig.update_layout(
                    height=340,
                    margin={"l": 20, "r": 40, "t": 30, "b": 20},
                    yaxis={"categoryorder": "total ascending"},
                    xaxis_tickprefix="$",
                    plot_bgcolor="white",
                )
                service_fig.update_xaxes(showgrid=False)
                service_fig.update_yaxes(showgrid=False)
                st.plotly_chart(service_fig, use_container_width=True)


def _show_breakdowns(result: dict) -> None:
    st.subheader("Overall Cost Breakdown")
    labels = {
        "service": "Service",
        "region": "Region",
        "resource": "Resource",
        "tag": "Tag",
        "usage_type": "Usage Type",
    }
    # Stacked rather than tabbed, so every dimension is visible on one scroll.
    for key, label in labels.items():
        st.markdown(f"**{label}**")
        data = pd.DataFrame(result["overall_breakdowns"].get(key, []))
        if data.empty:
            st.info("No data available for this breakdown.")
        else:
            st.dataframe(data, use_container_width=True)


def _show_headline(record: dict, severity: str) -> None:
    """The suspected cause, as a coloured banner above the narrative."""
    headline = record.get("headline")
    if not headline:
        return
    palette = SEVERITY_COLORS.get(severity, SEVERITY_COLORS["low"])
    st.markdown(
        f"""
        <div class="rca-headline" style="background:{palette['bg']};border-color:{palette['line']}">
            <span class="rca-severity" style="color:{palette['text']}">{severity.upper()}</span>
            <span class="rca-headline-text">{html.escape(headline)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _show_likely_causes(record: dict) -> None:
    """Ranked hypotheses. Empty in template mode, which is why this can be skipped."""
    causes = record.get("likely_causes") or []
    if not causes:
        return
    st.markdown("**Likely causes**")
    for rank, cause in enumerate(causes, start=1):
        confidence = cause.get("confidence", "low")
        palette = CONFIDENCE_COLORS.get(confidence, CONFIDENCE_COLORS["low"])
        st.markdown(
            f"""
            <div class="rca-cause">
                <div class="rca-cause-head">
                    <span class="rca-rank">{rank}</span>
                    <span class="rca-chip" style="background:{palette['bg']};color:{palette['text']}">
                        {confidence} confidence
                    </span>
                    <span class="rca-cause-text">{html.escape(cause.get('cause', ''))}</span>
                </div>
                <p class="rca-evidence">Evidence: {html.escape(cause.get('evidence', ''))}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _show_investigation_steps(record: dict) -> None:
    steps = record.get("investigation_steps") or []
    if not steps:
        return
    st.markdown("**How to confirm it**")
    for number, step in enumerate(steps, start=1):
        st.markdown(f"{number}. {step}")


def _show_anomaly_details(result: dict) -> None:
    st.subheader("Root Cause Analysis")
    if not result["service_comparison"]:
        st.info("No strong anomalies were detected in this file.")
        return

    method = result["metadata"].get("explanation_method", "deterministic template")
    if method.startswith("LLM"):
        st.caption(
            f"Explanations written by {method}. Every figure quoted is computed by the "
            "pipeline and passed to the model as JSON; the model words them and recommends "
            "the action."
        )
    else:
        st.caption(
            f"Explanations from the {method}. Set GEMINI_API_KEY in .env to have the LLM "
            "write them instead."
        )

    for record in result["service_comparison"]:
        severity = record.get("severity", "low")
        title = (
            f"{SEVERITY_MARKS.get(severity, '')} {record['service_name']} | {record['date']} "
            f"| impact ${record['impact_value']:,.2f}"
        )
        with st.expander(title, expanded=False):
            _show_headline(record, severity)
            st.write(record["root_cause_analysis"])
            _show_likely_causes(record)
            _show_investigation_steps(record)
            # The template paragraph ends with its own action line; the LLM returns
            # the action as a separate field, so it is rendered here instead.
            if record.get("explanation_method", "").startswith("LLM") and record.get("recommendation"):
                st.markdown(f"**Recommended action:** {record['recommendation']}")

            breakdown_tab, feature_tab = st.tabs(["Factor Contributions", "ML Feature Attribution"])
            with breakdown_tab:
                for label, key in [
                    ("Service", "service"),
                    ("Region", "region"),
                    ("Resource", "resource"),
                    ("Tag", "tag"),
                    ("Usage Type", "usage_type"),
                ]:
                    rows = pd.DataFrame(record["breakdowns"].get(key, []))
                    if not rows.empty:
                        st.markdown(f"**{label}**")
                        st.dataframe(rows, use_container_width=True)

            with feature_tab:
                feature_rows = pd.DataFrame(record["feature_contributions"])
                st.dataframe(feature_rows, use_container_width=True)


def _show_downloads(result: dict, anomaly_table: pd.DataFrame) -> None:
    st.subheader("Export")
    col1, col2, col3 = st.columns(3)
    col1.download_button(
        "Download Text Report",
        data=result["report_text"],
        file_name="carci_anomaly_report.txt",
        mime="text/plain",
        use_container_width=True,
    )
    col2.download_button(
        "Download Anomaly CSV",
        data=anomaly_table.to_csv(index=False).encode("utf-8"),
        file_name="carci_anomaly_table.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=anomaly_table.empty,
    )
    detailed = build_report_dataframe(result)
    col3.download_button(
        "Download Detailed CSV",
        data=detailed.to_csv(index=False).encode("utf-8"),
        file_name="carci_detailed_report.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=detailed.empty,
        help="Long-format export including metadata and per-feature SHAP contributions.",
    )


def _show_summary_page(result: dict, file_name: str | None) -> None:
    label = file_name or "the uploaded file"
    st.success(f"Analysis complete for **{label}**. Review the summary below.")
    _show_section_title(
        "Summary",
        "Rows analyzed, daily trend, and anomaly impact",
        "This page highlights the key signals: analyzed rows, total cost, anomaly count, "
        "daily cost movement, and the services driving the largest impact.",
    )
    _show_metrics(result)
    _show_charts(result, _anomaly_table(result))

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    if col1.button("Back to Upload", use_container_width=True, key="summary_back"):
        _goto(1)
    if col2.button(
        "Continue to Page 3: Investigation Details",
        type="primary",
        use_container_width=True,
        key="summary_next",
    ):
        _goto(3)
    if col3.button("New Analysis", use_container_width=True, key="summary_new"):
        _reset_analysis()
        _goto(1)


def _show_investigation_page(result: dict) -> None:
    _show_section_title(
        "Investigation",
        "Anomaly table, cost breakdown, and root cause",
        "Every flagged service-day with its driver row, the overall cost breakdown by "
        "dimension, and a per-anomaly explanation with ML feature attribution.",
    )

    anomaly_table = _anomaly_table(result)
    st.subheader("Anomaly Table")
    if anomaly_table.empty:
        st.info("No anomaly rows were produced for this upload.")
    else:
        st.dataframe(anomaly_table, use_container_width=True)

    _show_breakdowns(result)
    _show_anomaly_details(result)
    _show_downloads(result, anomaly_table)

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    if col1.button("Back to Summary", use_container_width=True, key="details_back"):
        _goto(2)
    if col2.button("Back to Upload", use_container_width=True, key="details_upload"):
        _goto(1)
    if col3.button("New Analysis", use_container_width=True, key="details_new"):
        _reset_analysis()
        _goto(1)


def _run_analysis(uploaded_file) -> bool:
    """Run the pipeline and record either the result or a readable error.

    Returns True when analysis succeeded, so the caller can advance the wizard.
    """
    st.session_state.analysis_error = None
    with st.spinner("Analyzing AWS CUR data and generating explanations..."):
        try:
            st.session_state.analysis_result = analyze_csv_bytes(uploaded_file.getvalue())
            return True
        # ParserError subclasses ValueError, so it must be caught first.
        except pd.errors.ParserError as exc:
            message = f"The file could not be parsed as CSV. {exc}"
        except ValueError as exc:
            # Raised by schema detection and preprocessing for unusable files.
            message = str(exc)
        # Last resort: the message is surfaced to the user, never swallowed.
        except Exception as exc:
            message = f"Unexpected {type(exc).__name__}: {exc}"

    st.session_state.analysis_error = message
    st.session_state.analysis_result = None
    return False


def _show_upload_page() -> None:
    _show_section_title(
        "Start Analysis",
        "Upload your AWS billing CSV",
        "Select the CUR-style CSV file. When analysis completes, CARCI opens the anomaly "
        "summary page automatically.",
    )

    uploaded_file = st.file_uploader(
        "Upload your AWS CUR CSV",
        type=["csv"],
        help="Upload a CUR-style CSV file exported from AWS billing or a synthetic dataset with matching columns.",
    )
    _show_upload_state(uploaded_file)

    # Selecting a different file invalidates results still on screen from the last one.
    # Only a real selection counts: returning here from page 2 or 3 re-creates the
    # uploader empty, and that must not discard the analysis being navigated around.
    current_name = uploaded_file.name if uploaded_file else None
    if current_name is not None and st.session_state.last_file_name != current_name:
        st.session_state.last_file_name = current_name
        _reset_analysis()

    col1, col2 = st.columns([1, 1])
    # Both buttons render unconditionally so the row keeps its layout before upload.
    start_clicked = col1.button(
        "Start Analysis",
        type="primary",
        use_container_width=True,
        disabled=uploaded_file is None,
    )
    clear_clicked = col2.button("Clear Results", use_container_width=True)

    if start_clicked and uploaded_file is not None:
        if _run_analysis(uploaded_file):
            _goto(2)

    if clear_clicked:
        _reset_analysis()
        st.rerun()

    if st.session_state.analysis_error:
        st.error(f"Unable to analyze the uploaded file: {st.session_state.analysis_error}")

    if st.session_state.analysis_result:
        st.info("Analysis is ready. Continue to the anomaly summary.")
        if st.button("Continue to Page 2: Anomaly Summary", type="primary", key="upload_next"):
            _goto(2)


def main() -> None:
    st.markdown(PAGE_CSS, unsafe_allow_html=True)

    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "analysis_error" not in st.session_state:
        st.session_state.analysis_error = None
    if "last_file_name" not in st.session_state:
        st.session_state.last_file_name = None
    if "page" not in st.session_state:
        st.session_state.page = 1

    # Pages 2 and 3 have nothing to show without a result, so fall back to upload.
    if st.session_state.analysis_result is None:
        st.session_state.page = 1

    _show_header()
    _show_steps(st.session_state.page)

    if st.session_state.page == 2:
        _show_summary_page(st.session_state.analysis_result, st.session_state.last_file_name)
    elif st.session_state.page == 3:
        _show_investigation_page(st.session_state.analysis_result)
    else:
        _show_upload_page()


if __name__ == "__main__":
    main()
