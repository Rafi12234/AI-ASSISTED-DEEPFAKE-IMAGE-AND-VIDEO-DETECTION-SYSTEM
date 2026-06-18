import uuid
from datetime import date, datetime
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.core import User


router = APIRouter(prefix="/reports", tags=["Reports"])


def make_json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, uuid.UUID):
        return str(value)

    return value


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        key: make_json_safe(value)
        for key, value in row._mapping.items()
    }


def fmt(value: Any) -> str:
    if value is None:
        return "N/A"

    if isinstance(value, float):
        return f"{round(value * 100)}%"

    return str(value)


async def fetch_report_data(
    *,
    db: AsyncSession,
    job_id: uuid.UUID,
    current_user: User,
) -> dict[str, Any]:
    if current_user.role == "admin":
        ownership_condition = ""
        params = {"job_id": job_id}
    else:
        ownership_condition = "AND mu.user_id = :user_id"
        params = {"job_id": job_id, "user_id": current_user.id}

    job_result = await db.execute(
        text(
            f"""
            SELECT
                aj.id AS job_id,
                aj.status AS job_status,
                aj.queued_at,
                aj.started_at,
                aj.completed_at,
                aj.error_message,

                mu.id AS upload_id,
                mu.original_filename,
                mu.file_type,
                mu.mime_type,
                mu.file_size_bytes,
                mu.upload_status,
                mu.created_at AS uploaded_at,

                u.email AS user_email
            FROM analysis_jobs aj
            INNER JOIN media_uploads mu ON mu.id = aj.media_upload_id
            INNER JOIN users u ON u.id = mu.user_id
            WHERE aj.id = :job_id
              AND mu.is_deleted = false
              {ownership_condition}
            LIMIT 1
            """
        ),
        params,
    )

    job_row = job_result.first()

    if job_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    result = await db.execute(
        text(
            """
            SELECT
                id,
                media_upload_id,
                analysis_job_id,
                final_score,
                risk_level,
                confidence,
                explanation,
                processing_time_ms,
                created_at
            FROM analysis_results
            WHERE analysis_job_id = :job_id
            LIMIT 1
            """
        ),
        {"job_id": job_id},
    )

    result_row = result.first()

    if result_row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report cannot be generated before analysis is completed.",
        )

    analysis_result = row_to_dict(result_row)
    analysis_result_id = analysis_result["id"]

    predictions_result = await db.execute(
        text(
            """
            SELECT
                model_name,
                model_version,
                raw_score,
                calibrated_score,
                prediction_label,
                target_region,
                inference_time_ms
            FROM model_predictions
            WHERE analysis_result_id = :analysis_result_id
            ORDER BY created_at ASC
            """
        ),
        {"analysis_result_id": analysis_result_id},
    )

    signals_result = await db.execute(
        text(
            """
            SELECT
                signal_type,
                signal_value,
                risk_contribution,
                details
            FROM forensic_signals
            WHERE analysis_result_id = :analysis_result_id
            ORDER BY created_at ASC
            """
        ),
        {"analysis_result_id": analysis_result_id},
    )

    return {
        "job": row_to_dict(job_row),
        "result": analysis_result,
        "predictions": [row_to_dict(row) for row in predictions_result.all()],
        "signals": [row_to_dict(row) for row in signals_result.all()],
    }


def build_pdf_report(data: dict[str, Any]) -> BytesIO:
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=26,
        spaceAfter=16,
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        spaceBefore=14,
        spaceAfter=8,
    )

    normal_style = ParagraphStyle(
        "CustomNormal",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
    )

    story = []

    job = data["job"]
    result = data["result"]
    predictions = data["predictions"]
    signals = data["signals"]

    story.append(Paragraph("Deepfake Detection Analysis Report", title_style))
    story.append(
        Paragraph(
            "This report is generated from the analysis result stored in the system.",
            normal_style,
        )
    )
    story.append(Spacer(1, 12))

    summary_table = Table(
        [
            ["Final Score", fmt(result.get("final_score"))],
            ["Risk Level", fmt(result.get("risk_level"))],
            ["Confidence", fmt(result.get("confidence"))],
            ["Processing Time", f"{fmt(result.get('processing_time_ms'))} ms"],
            ["Generated At", fmt(result.get("created_at"))],
        ],
        colWidths=[160, 340],
    )

    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E5E7EB")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.append(summary_table)

    story.append(Paragraph("Explanation", heading_style))
    story.append(Paragraph(fmt(result.get("explanation")), normal_style))

    story.append(Paragraph("File Information", heading_style))

    file_table = Table(
        [
            ["Filename", fmt(job.get("original_filename"))],
            ["Uploaded By", fmt(job.get("user_email"))],
            ["File Type", fmt(job.get("file_type"))],
            ["MIME Type", fmt(job.get("mime_type"))],
            ["File Size Bytes", fmt(job.get("file_size_bytes"))],
            ["Upload Status", fmt(job.get("upload_status"))],
            ["Job Status", fmt(job.get("job_status"))],
        ],
        colWidths=[160, 340],
    )

    file_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E5E7EB")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.append(file_table)

    story.append(Paragraph("Model Predictions", heading_style))

    prediction_rows = [
        [
            "Model",
            "Version",
            "Raw Score",
            "Calibrated",
            "Label",
            "Target",
        ]
    ]

    for prediction in predictions:
        prediction_rows.append(
            [
                fmt(prediction.get("model_name")),
                fmt(prediction.get("model_version")),
                fmt(prediction.get("raw_score")),
                fmt(prediction.get("calibrated_score")),
                fmt(prediction.get("prediction_label")),
                fmt(prediction.get("target_region")),
            ]
        )

    prediction_table = Table(
        prediction_rows,
        colWidths=[135, 60, 70, 70, 90, 60],
    )

    prediction_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(prediction_table)

    story.append(Paragraph("Forensic Signals", heading_style))

    signal_rows = [
        [
            "Type",
            "Signal",
            "Contribution",
            "Severity",
            "Description",
        ]
    ]

    for signal in signals:
        details = signal.get("details") or {}

        signal_rows.append(
            [
                fmt(signal.get("signal_type")),
                fmt(signal.get("signal_value")),
                fmt(signal.get("risk_contribution")),
                fmt(details.get("severity")),
                Paragraph(fmt(details.get("description")), normal_style),
            ]
        )

    signal_table = Table(
        signal_rows,
        colWidths=[70, 110, 80, 70, 170],
    )

    signal_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(signal_table)

    story.append(Paragraph("Reference IDs", heading_style))

    ids_table = Table(
        [
            ["Job ID", fmt(job.get("job_id"))],
            ["Upload ID", fmt(job.get("upload_id"))],
            ["Result ID", fmt(result.get("id"))],
        ],
        colWidths=[160, 340],
    )

    ids_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E5E7EB")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.append(ids_table)

    doc.build(story)

    buffer.seek(0)
    return buffer


@router.get("/jobs/{job_id}/pdf")
async def download_job_pdf_report(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await fetch_report_data(
        db=db,
        job_id=job_id,
        current_user=current_user,
    )

    pdf_buffer = build_pdf_report(data)

    filename = f"deepfake-analysis-report-{job_id}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )