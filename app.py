from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for

from scanner import ScanJobRunner, ScanJobStore, ScannerConfig, StockScannerService
from scanner.models import SIGNAL_NONE, ScanFilters

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)


@app.template_filter("thousands")
def thousands(value):
    try:
        number = int(float(value or 0))
        return f"{number:,}".replace(",", ".")
    except (TypeError, ValueError):
        return "-"


@app.template_filter("fmt2")
def fmt2(value):
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "-"

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"

scanner_service = StockScannerService(ScannerConfig.from_project_root(PROJECT_ROOT))
job_store = ScanJobStore(DATA_DIR / "scan_jobs.sqlite3")
job_store.cleanup_old_jobs()
job_runner = ScanJobRunner(scanner_service, job_store)


def _scan_filters_from_state(form_state: dict) -> ScanFilters:
    def parse_float(value: str) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except ValueError:
            return None

    return ScanFilters(
        sector=form_state.get("sector", "all"),
        industry=form_state.get("industry", "all"),
        signal=form_state.get("signal", "all"),
        market_cap_min=parse_float(form_state.get("market_cap_min", "")),
        market_cap_max=parse_float(form_state.get("market_cap_max", "")),
        sort_by=form_state.get("sort_by", "ticker"),
        sort_dir=form_state.get("sort_dir", "asc"),
        trend_level=form_state.get("trend_level", "all"),
        momentum_level=form_state.get("momentum_level", "all"),
        timing_level=form_state.get("timing_level", "all"),
        breakout_level=form_state.get("breakout_level", "all"),
        risk_level=form_state.get("risk_level", "all"),
        rsi_min=parse_float(form_state.get("rsi_min", "")),
        rsi_max=parse_float(form_state.get("rsi_max", "")),
        atr_pct_min=parse_float(form_state.get("atr_pct_min", "")),
        atr_pct_max=parse_float(form_state.get("atr_pct_max", "")),
        bb_width_max=parse_float(form_state.get("bb_width_max", "")),
    )


def _filters_from_session(session_key: str = "form_state") -> ScanFilters:
    form_state = session.get(session_key, scanner_service.default_form_state())
    return _scan_filters_from_state(form_state)


def _format_job_timestamp(iso_timestamp: str | None) -> str | None:
    if not iso_timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(iso_timestamp)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone().strftime("%d.%m.%Y %H:%M:%S")


def _latest_scan_context() -> tuple[str | None, list[dict], str | None]:
    """Return (job_id, results, formatted_timestamp) for the latest completed scan."""
    latest_job_id, latest_results = job_runner.get_latest_completed_results()
    latest_completed_job = job_store.get_latest_completed_job()
    latest_scan_finished_at = _format_job_timestamp(
        latest_completed_job.get("finished_at") if latest_completed_job else None
    )
    return latest_job_id, latest_results, latest_scan_finished_at


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action", "filter")

        if action == "scan":
            job_id, created = job_runner.enqueue_scan()
            session["active_job_id"] = job_id
            if created:
                session["status_message"] = "Tarama arka planda başlatıldı."
            else:
                session["status_message"] = "Zaten çalışan bir tarama var."
            return redirect(url_for("index"))

        filters = ScanFilters.from_form(request.form)
        session["form_state"] = filters.to_form_dict()
        return redirect(url_for("index"))

    latest_job_id, latest_results, latest_scan_finished_at = _latest_scan_context()
    signal_hits = [item for item in latest_results if item.get("signal") != SIGNAL_NONE]
    filters = _filters_from_session("form_state")
    filtered_results = scanner_service.apply_filters(signal_hits, filters)
    status_message = session.get("status_message")
    active_job_id = session.get("active_job_id")
    active_job = job_runner.get_job(active_job_id) if active_job_id else None

    if active_job and active_job.get("status") in {"COMPLETED", "FAILED"}:
        session.pop("active_job_id", None)
        if active_job.get("status") == "FAILED":
            session["status_message"] = active_job.get("error") or "Tarama başarısız oldu."
        elif active_job.get("status") == "COMPLETED":
            session["status_message"] = f"Tarama tamamlandı. Sonuç: {active_job.get('result_count', 0)}"
        return redirect(url_for("index"))

    sectors, industries = scanner_service.build_filter_options(latest_results)

    return render_template(
        "index.html",
        results=filtered_results,
        error=None,
        sectors=sectors,
        industries=industries,
        form_state=filters.to_form_dict(),
        status_message=status_message,
        active_job=active_job,
        latest_job_id=latest_job_id,
        latest_scan_finished_at=latest_scan_finished_at,
    )


@app.route("/summary", methods=["GET"])
def summary():
    latest_job_id, latest_results, latest_scan_finished_at = _latest_scan_context()
    summary_data = scanner_service.build_signal_summary(latest_results)
    return render_template(
        "summary.html",
        summary=summary_data,
        latest_job_id=latest_job_id,
        latest_scan_finished_at=latest_scan_finished_at,
    )


@app.route("/signals", methods=["GET", "POST"])
def signals():
    if request.method == "POST":
        filters = ScanFilters.from_form(request.form)
        session["form_state_signals"] = filters.to_form_dict()
        return redirect(url_for("signals"))

    latest_job_id, latest_results, latest_scan_finished_at = _latest_scan_context()

    filters = _filters_from_session("form_state_signals")
    filtered_results = scanner_service.apply_filters(latest_results, filters)
    sectors, industries = scanner_service.build_filter_options(latest_results)

    return render_template(
        "signals.html",
        results=filtered_results,
        form_state=filters.to_form_dict(),
        sectors=sectors,
        industries=industries,
        latest_job_id=latest_job_id,
        latest_scan_finished_at=latest_scan_finished_at,
    )


@app.route("/signals-guide", methods=["GET"])
def signals_guide():
    return render_template("signals_guide.html")


@app.route("/scan_status/<job_id>", methods=["GET"])
def scan_status(job_id: str):
    job = job_runner.get_job(job_id)
    if not job:
        return jsonify({"error": "job_not_found"}), 404

    return jsonify(
        {
            "id": job["id"],
            "status": job["status"],
            "created_at": job["created_at"],
            "started_at": job["started_at"],
            "finished_at": job["finished_at"],
            "error": job["error"],
            "result_count": job["result_count"],
        }
    )


@app.route("/download_csv", methods=["GET"])
def download_csv():
    latest_job_id, latest_results, _ = _latest_scan_context()
    if not latest_job_id:
        dataframe = pd.DataFrame([])
    else:
        signal_hits = [item for item in latest_results if item.get("signal") != SIGNAL_NONE]
        dataframe = pd.DataFrame(scanner_service.apply_filters(signal_hits, _filters_from_session("form_state")))

    csv_bytes = dataframe.to_csv(index=False).encode("utf-8")
    csv_buffer = BytesIO(csv_bytes)

    return send_file(
        csv_buffer,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"tarama_sonuc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    )


@app.route("/download_csv_signals", methods=["GET"])
def download_csv_signals():
    """Export signals page data with technical indicators (28 columns) as CSV."""
    latest_job_id, latest_results, _ = _latest_scan_context()

    if not latest_job_id:
        dataframe = pd.DataFrame([])
    else:
        # Apply filters from signals session
        filters = _filters_from_session("form_state_signals")
        filtered_results = scanner_service.apply_filters(latest_results, filters)

        # Select 28 columns: basic info + technical indicators + badge text
        columns_to_select = [
            "ticker", "name", "sector", "industry", "close_price", "market_cap", "signal",
            "ema_9", "ema_20", "ema_50",
            "macd_line", "macd_signal", "macd_hist", "momentum_view",
            "rsi_14", "kdj_j", "timing_view",
            "bb_upper", "bb_lower", "bb_width_pct", "breakout_view",
            "atr_14", "atr_pct", "risk_view",
            "trend_view"
        ]

        # Convert to DataFrame and select columns
        dataframe = pd.DataFrame(filtered_results)
        # Keep only columns that exist
        existing_cols = [col for col in columns_to_select if col in dataframe.columns]
        dataframe = dataframe[existing_cols]

    csv_bytes = dataframe.to_csv(index=False).encode("utf-8")
    csv_buffer = BytesIO(csv_bytes)

    return send_file(
        csv_buffer,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"tarama_teknik_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    )


@app.route("/download_csv_summary", methods=["GET"])
def download_csv_summary():
    """Export summary page data (sector and industry breakdown) as CSV."""
    latest_job_id, latest_results, _ = _latest_scan_context()

    if not latest_job_id:
        dataframe = pd.DataFrame([])
    else:
        # Generate summary data
        summary_data = scanner_service.build_signal_summary(latest_results)

        if not summary_data or summary_data.get("total", 0) == 0:
            dataframe = pd.DataFrame([])
        else:
            # Build CSV with sector summary first, then industry details
            rows = []

            # Add sector summary header
            rows.append({"Bölüm": "SEKTOR ÖZETİ", "Toplam": "", "Bullish": "", "Bearish": ""})

            # Add sector summary rows
            for sector_row in summary_data.get("by_sector", []):
                rows.append({
                    "Bölüm": sector_row["name"],
                    "Toplam": sector_row["total"],
                    "Bullish": sector_row["bullish"],
                    "Bearish": sector_row["bearish"]
                })

            # Add empty row
            rows.append({"Bölüm": "", "Toplam": "", "Bullish": "", "Bearish": ""})

            # Add industry summary header
            rows.append({"Bölüm": "ENDÜSTRİ ÖZETİ (SEKTÖR BAZLI)", "Toplam": "", "Bullish": "", "Bearish": ""})

            # Add industry rows grouped by sector
            for sector_group in summary_data.get("by_sector_industry", []):
                sector_name = sector_group["sector"]
                # Add sector sub-header
                rows.append({"Bölüm": f"Sektör: {sector_name}", "Toplam": "", "Bullish": "", "Bearish": ""})

                # Add industry rows for this sector
                for industry_row in sector_group.get("industries", []):
                    rows.append({
                        "Bölüm": f"  {industry_row['name']}",
                        "Toplam": industry_row["total"],
                        "Bullish": industry_row["bullish"],
                        "Bearish": industry_row["bearish"]
                    })

            dataframe = pd.DataFrame(rows)

    csv_bytes = dataframe.to_csv(index=False).encode("utf-8")
    csv_buffer = BytesIO(csv_bytes)

    return send_file(
        csv_buffer,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"tarama_ozeti_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    )

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Render injects PORT; when present always bind all interfaces for health checks.
    render_port = os.environ.get("PORT")
    port = int(render_port or os.environ.get("FLASK_PORT", "5000"))
    host = "0.0.0.0" if render_port else os.environ.get("FLASK_HOST", "0.0.0.0")

    # Keep debug off by default in deployments unless explicitly enabled.
    debug = os.environ.get("FLASK_DEBUG", "0") in {"1", "true", "True"}
    app.run(debug=debug, host=host, port=port)
