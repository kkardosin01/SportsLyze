"""Testes de `src.services.report_service.ReportService` — controle de
acesso à partida (via clube ou atleta independente dono da partida),
enfileiramento da geração e resolução de URLs assinadas para download,
usando repositórios/celery falsos (sem tocar o Supabase real)."""

import os

os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test")

import pytest
from fastapi import HTTPException

from src.services.report_service import ReportService


class FakeMatchRepo:
    def __init__(self, match: dict):
        self._match = match

    def get_by_id(self, match_id):
        return self._match if match_id == self._match["id"] else None


class FakeAthleteRepo:
    def __init__(self, athlete: dict | None = None):
        self._athlete = athlete

    def get_by_id(self, athlete_id):
        return self._athlete if self._athlete and athlete_id == self._athlete["id"] else None


class FakeMemberRepo:
    def __init__(self, memberships=()):
        self._memberships = set(memberships)

    def find_membership(self, club_id, user_id):
        return {"club_id": club_id, "user_id": user_id} if (club_id, user_id) in self._memberships else None


class FakeReportRepo:
    def __init__(self, reports=()):
        self._reports = list(reports)

    def list_for_match(self, match_id):
        return [dict(r) for r in self._reports if r["match_id"] == match_id]


class FakeStorage:
    def create_signed_report_url(self, storage_path, expires_in=3600):
        return f"https://signed.example/{storage_path}"


class FakeCelery:
    def __init__(self):
        self.sent = []

    def send_task(self, name, args):
        self.sent.append((name, args))


def _service(match, athlete=None, memberships=(), reports=(), celery=None):
    return ReportService(
        FakeMatchRepo(match),
        FakeAthleteRepo(athlete),
        FakeMemberRepo(memberships),
        FakeReportRepo(reports),
        FakeStorage(),
        celery or FakeCelery(),
    )


def test_request_report_denied_for_unrelated_user():
    match = {"id": "match-1", "club_id": "club-1", "athlete_id": None}
    service = _service(match)

    with pytest.raises(HTTPException) as exc_info:
        service.request_report("match-1", "user-x", "pdf")

    assert exc_info.value.status_code == 403


def test_request_report_allowed_for_club_member_enqueues_task():
    match = {"id": "match-1", "club_id": "club-1", "athlete_id": None}
    celery = FakeCelery()
    service = _service(match, memberships=[("club-1", "user-x")], celery=celery)

    service.request_report("match-1", "user-x", "slides")

    assert celery.sent == [("tasks.generate_match_report", ["match-1", "user-x", "slides"])]


def test_request_report_allowed_for_owning_athlete():
    match = {"id": "match-1", "club_id": None, "athlete_id": "athlete-1"}
    athlete = {"id": "athlete-1", "user_id": "user-x"}
    celery = FakeCelery()
    service = _service(match, athlete=athlete, celery=celery)

    service.request_report("match-1", "user-x", "audio")

    assert celery.sent == [("tasks.generate_match_report", ["match-1", "user-x", "audio"])]


def test_request_report_match_not_found_raises_404():
    match = {"id": "match-1", "club_id": "club-1", "athlete_id": None}
    service = _service(match)

    with pytest.raises(HTTPException) as exc_info:
        service.request_report("match-does-not-exist", "user-x", "pdf")

    assert exc_info.value.status_code == 404


def test_list_reports_resolves_download_urls():
    match = {"id": "match-1", "club_id": "club-1", "athlete_id": None}
    reports = [
        {
            "id": "report-1",
            "match_id": "match-1",
            "storage_path": "matches/match-1/relatorio.pdf",
            "format": "pdf",
        }
    ]
    service = _service(match, memberships=[("club-1", "user-x")], reports=reports)

    result = service.list_reports("match-1", "user-x")

    assert result[0]["download_url"] == "https://signed.example/matches/match-1/relatorio.pdf"


def test_list_reports_denied_for_unrelated_user():
    match = {"id": "match-1", "club_id": "club-1", "athlete_id": None}
    service = _service(match)

    with pytest.raises(HTTPException) as exc_info:
        service.list_reports("match-1", "user-x")

    assert exc_info.value.status_code == 403
