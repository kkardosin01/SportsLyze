"""Geração de relatório PDF (server-side, WeasyPrint) por partida ou por
jogador. Estrutura pronta para futuros formatos (áudio, slides) — ver
`reports.format` no schema."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from celery import shared_task
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from src.core.config import get_settings
from src.db.session import get_supabase_admin

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


@shared_task(name="tasks.generate_match_report")
def generate_match_report(match_id: str, created_by: str) -> str:
    db = get_supabase_admin()
    settings = get_settings()

    match = db.table("matches").select("*, clubs(name)").eq("id", match_id).single().execute().data
    videos = db.table("videos").select("id").eq("match_id", match_id).execute().data or []
    video_ids = [v["id"] for v in videos]

    stats_rows = (
        db.table("player_match_stats")
        .select("*, detected_players(label, athlete_id, athletes(full_name))")
        .in_("video_id", video_ids)
        .execute()
        .data
        if video_ids
        else []
    )

    players = [
        {
            "name": (row["detected_players"].get("athletes") or {}).get("full_name")
            or row["detected_players"]["label"],
            "distance_km": row["distance_km"] or 0,
            "avg_speed_kmh": row["avg_speed_kmh"] or 0,
            "max_speed_kmh": row["max_speed_kmh"] or 0,
        }
        for row in stats_rows
    ]

    template = _jinja_env.get_template("report_match.html")
    html_content = template.render(
        club_name=(match.get("clubs") or {}).get("name", "Atleta independente"),
        opponent_name=match.get("opponent_name"),
        match_date=match.get("match_date") or "",
        generated_at=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M"),
        players=players,
    )

    with tempfile.TemporaryDirectory(prefix="sportslyze_report_") as tmp_dir:
        pdf_path = Path(tmp_dir) / f"relatorio_partida_{match_id}.pdf"
        HTML(string=html_content).write_pdf(str(pdf_path))

        storage_path = f"matches/{match_id}/relatorio_{int(datetime.now(timezone.utc).timestamp())}.pdf"
        db.storage.from_(settings.supabase_storage_bucket_reports).upload(
            storage_path, pdf_path.read_bytes(), {"content-type": "application/pdf"}
        )

    report = db.table("reports").insert(
        {
            "scope": "match",
            "match_id": match_id,
            "format": "pdf",
            "storage_path": storage_path,
            "created_by": created_by,
        }
    ).execute().data[0]

    return report["id"]
