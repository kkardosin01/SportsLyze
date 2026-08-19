"""Notificações in-app e por e-mail quando uma análise termina (ou falha)."""

import logging
import smtplib
from email.message import EmailMessage

from celery import shared_task

from src.core.config import get_settings
from src.db.session import get_supabase_admin

logger = logging.getLogger(__name__)


@shared_task(name="tasks.notify_analysis_done")
def notify_analysis_done(video_id: str) -> None:
    db = get_supabase_admin()
    video = db.table("videos").select("*").eq("id", video_id).single().execute().data
    user_id = _resolve_notification_recipient(db, video)

    db.table("notifications").insert(
        {
            "user_id": user_id,
            "type": "analysis_done",
            "title": "Análise concluída",
            "message": f"A análise do vídeo \"{video['original_filename']}\" está pronta.",
            "related_entity_type": "video",
            "related_entity_id": video_id,
        }
    ).execute()

    _send_email_best_effort(
        db, user_id, subject="Sua análise está pronta", body="Acesse a plataforma para conferir os resultados."
    )


@shared_task(name="tasks.notify_analysis_failed")
def notify_analysis_failed(video_id: str, error_message: str) -> None:
    db = get_supabase_admin()
    video = db.table("videos").select("*").eq("id", video_id).single().execute().data
    user_id = _resolve_notification_recipient(db, video)

    db.table("notifications").insert(
        {
            "user_id": user_id,
            "type": "analysis_failed",
            "title": "Falha ao processar vídeo",
            "message": error_message,
            "related_entity_type": "video",
            "related_entity_id": video_id,
        }
    ).execute()


def _resolve_notification_recipient(db, video: dict) -> str:
    if video["owner_type"] == "athlete":
        return video["owner_id"]
    return video["uploaded_by"]


def _send_email_best_effort(db, user_id: str, subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        return  # SMTP não configurado no ambiente (ex: dev local) — segue só com notificação in-app

    try:
        user = db.auth.admin.get_user_by_id(user_id)
        recipient_email = user.user.email if user and user.user else None
        if not recipient_email:
            return

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.email_from
        message["To"] = recipient_email
        message.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password or "")
            smtp.send_message(message)
    except Exception:  # noqa: BLE001 — falha de e-mail não pode derrubar a notificação in-app
        logger.exception("Falha ao enviar e-mail de notificação para %s", user_id)
