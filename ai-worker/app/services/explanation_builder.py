from __future__ import annotations

from typing import Any


def get_risk_label(risk_level: str) -> str:
    labels = {
        "likely_authentic": "Likely Authentic",
        "uncertain": "Uncertain",
        "suspicious": "Suspicious",
        "high_risk": "High Risk",
    }

    return labels.get(risk_level, risk_level)


def get_score_band(final_score: float) -> str:
    percentage = round(final_score * 100)

    if final_score < 0.33:
        return (
            f"The score is {percentage}%, which is in the low-risk range. "
            "The analyzed visual signals do not strongly indicate manipulation."
        )

    if final_score < 0.61:
        return (
            f"The score is {percentage}%, which is in the uncertain range. "
            "Some signals are normal, but some require additional review."
        )

    if final_score < 0.8:
        return (
            f"The score is {percentage}%, which is in the suspicious range. "
            "Several visual or forensic signals deserve careful review."
        )

    return (
        f"The score is {percentage}%, which is in the high-risk range. "
        "The analyzed signals show stronger warning patterns and should be reviewed carefully."
    )


def get_recommended_action(risk_level: str) -> str:
    if risk_level == "likely_authentic":
        return (
            "No urgent action is required. Keep the result as a reference, but do not treat it as absolute proof."
        )

    if risk_level == "uncertain":
        return (
            "Manual review is recommended. Check the original source, upload history, and visual consistency."
        )

    if risk_level == "suspicious":
        return (
            "Human review is strongly recommended before trusting or sharing this media."
        )

    if risk_level == "high_risk":
        return (
            "Prioritize human review. Do not rely on this media as authentic without additional verification."
        )

    return "Review the media manually before making a decision."


def get_limitations(media_type: str) -> list[str]:
    base_limitations = [
        "This is a foundation analysis service, not a final trained deepfake detection model.",
        "A high score does not prove that the media is fake.",
        "A low score does not prove that the media is authentic.",
        "Compression, social media uploads, screenshots, and editing can affect the result.",
    ]

    if media_type == "video":
        base_limitations.append(
            "Video analysis is currently based on sampled frames, not full temporal deepfake model inference."
        )

    if media_type == "image":
        base_limitations.append(
            "Image analysis is currently based on pixel-level forensic signals, not face-specific deepfake model inference."
        )

    return base_limitations


def select_top_signals(signals: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    sorted_signals = sorted(
        signals,
        key=lambda item: float(item.get("score", 0.0)),
        reverse=True,
    )

    top_signals = []

    for signal in sorted_signals[:limit]:
        top_signals.append(
            {
                "signal_type": signal.get("signal_type"),
                "signal_name": signal.get("signal_name"),
                "score": signal.get("score"),
                "severity": signal.get("severity"),
                "description": signal.get("description"),
            }
        )

    return top_signals


def build_explanation_pack(
    *,
    media_type: str,
    final_score: float,
    risk_level: str,
    confidence: float,
    forensic_signals: list[dict[str, Any]],
    engine: str,
) -> dict[str, Any]:
    risk_label = get_risk_label(risk_level)
    score_band = get_score_band(final_score)
    recommended_action = get_recommended_action(risk_level)
    limitations = get_limitations(media_type)
    top_signals = select_top_signals(forensic_signals)

    signal_names = [
        str(signal.get("signal_name") or signal.get("signal_type"))
        for signal in top_signals
    ]

    if signal_names:
        top_signal_text = ", ".join(signal_names)
    else:
        top_signal_text = "No major signals were available"

    human_summary = (
        f"Verdict: {risk_label}. {score_band} "
        f"The strongest contributing signals were: {top_signal_text}. "
        f"Recommended action: {recommended_action}"
    )

    return {
        "verdict": risk_label,
        "risk_level": risk_level,
        "final_score": round(final_score, 4),
        "confidence": round(confidence, 4),
        "score_interpretation": score_band,
        "top_signals": top_signals,
        "recommended_action": recommended_action,
        "limitations": limitations,
        "engine": engine,
        "human_summary": human_summary,
    }