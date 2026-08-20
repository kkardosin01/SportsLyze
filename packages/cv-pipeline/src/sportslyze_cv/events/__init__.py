"""Detecção de eventos (passe, drible, desarme, falta, finalização,
triangulação, jogada ensaiada) a partir de heurísticas sobre o tracking.

v1 (Fase 2, primeiro incremento) implementou apenas "passe", via heurística
de posse de bola: a cada frame amostrado, o jogador mais próximo da bola
(dentro de um raio proporcional ao seu próprio tamanho na imagem) é
considerado o "dono" da posse; quando a posse muda de um track de jogador
para outro, é registrado um evento de passe entre os dois. Não depende de
homografia — usa proximidade em coordenadas de pixel, robusta a qualquer
resolução de vídeo.

Este incremento adiciona quatro heurísticas construídas sobre os mesmos
dados (posse por frame + posições rastreadas), sem exigir nenhum sinal novo
de visão computacional:

- **drible**: mesmo jogador mantém a posse por vários frames consecutivos
  *enquanto* se desloca uma distância mínima — distingue "conduzindo a
  bola" de "parado com a bola nos pés". Usa a homografia (metros reais)
  quando o campo está calibrado; cai para uma proxy em pixels (múltiplo da
  própria bbox) quando não está.
- **triangulação**: sequência de 3+ passes consecutivos (o receptor de um
  passe é o autor do próximo) envolvendo 3+ jogadores distintos, dentro de
  uma janela de tempo curta. Construída inteiramente em cima dos eventos de
  passe já detectados.
- **finalização**: bola perde a posse de um jogador sem ser recuperada
  rapidamente por ninguém (ao contrário de um passe) e, nos frames
  seguintes, se desloca em alta velocidade em direção a uma das zonas de
  finalização do campo (últimos ~20% do comprimento, perto de qualquer um
  dos dois gols). *Só é detectável quando o campo está calibrado* — mesma
  limitação que heatmap/distância já têm.
- **falta**: transição de posse "disputada" (confiança baixa) entre dois
  jogadores cujas bounding boxes ficaram sobrepostas por vários frames
  seguidos, sinal aproximado de contato físico. É a heurística mais
  aproximada deste incremento — não há dados de contato real nem de
  arbitragem — por isso nunca reporta confiança alta, e disputas caóticas
  demais para gerar sequer uma transição de posse com confiança mínima não
  são capturadas.

Os tipos "desarme" e "jogada ensaiada" ficam para um próximo incremento:
exigem saber a que time cada jogador pertence (para diferenciar disputa
entre times de simples troca de passes dentro do mesmo time), sinal que o
pipeline ainda não produz (nenhuma classificação de time/uniforme). Ver
PRD: precisão de eventos via heurística é aproximada por natureza e evolui
em fases.
"""

import math
from dataclasses import dataclass
from typing import Literal

from sportslyze_cv.homography import FIELD_LENGTH_M, Homography, pixel_to_field
from sportslyze_cv.tracking import TrackedObject

EventType = Literal[
    "passe", "drible", "desarme", "falta", "finalizacao", "triangulacao", "jogada_ensaiada"
]

# Distância máxima entre o centro da bola e o centro de um jogador, expressa
# como múltiplo da diagonal da bbox do próprio jogador, para considerá-lo em
# posse da bola. Relativo ao tamanho do jogador na imagem em vez de um valor
# fixo em pixels, para não depender da resolução/distância da câmera.
POSSESSION_PROXIMITY_FACTOR = 2.5

# Frames consecutivos sem posse clara (ex.: bola no ar durante o passe) que
# ainda são tolerados entre a posse do jogador A e a do jogador B para
# considerá-la uma transição direta (passe), não duas jogadas desconectadas.
MAX_GAP_FRAMES = 2

# Confiança mínima (baseada na proximidade nos dois extremos da transição)
# para registrar um evento — abaixo disso a heurística está pouco segura de
# que a posse realmente mudou entre esses dois jogadores.
MIN_TRANSITION_CONFIDENCE = 0.15

# --- Drible ---

# Frames consecutivos mínimos de posse contínua do mesmo jogador (a
# SAMPLE_FPS = 2.0 do pipeline, 4 frames ~ 1.5s) para considerar que ele
# esteve "conduzindo" a bola, e não apenas a recebeu e já passou.
MIN_DRIBBLE_FRAMES = 4

# Deslocamento real mínimo (metros, via homografia) do jogador durante a
# posse contínua para distinguir "conduzindo a bola andando/correndo" de
# "parado com a bola nos pés" (ex.: aguardando reposição).
MIN_DRIBBLE_DISPLACEMENT_M = 3.0

# Sem homografia disponível: mesmo critério, mas expresso como múltiplo da
# diagonal da própria bbox do jogador (proxy em pixels, menos preciso).
MIN_DRIBBLE_DISPLACEMENT_PX_FACTOR = 3.0

# --- Triangulação ---

# Tempo máximo (ms) entre o fim de um passe e o início do próximo para
# considerá-los parte da mesma sequência de troca de passes.
MAX_CHAIN_GAP_MS = 4000

# Nº mínimo de passes consecutivos e de jogadores distintos envolvidos para
# considerar a sequência uma "triangulação" (e não apenas dois passes soltos).
MIN_CHAIN_PASSES = 3
MIN_CHAIN_DISTINCT_PLAYERS = 3

# --- Finalização ---

# Fração do comprimento do campo, a partir de cada linha de fundo, que
# conta como "zona de finalização" — não depende de coordenadas exatas da
# trave (não detectadas pelo módulo de homografia), apenas da proximidade
# ao gol mais próximo.
SHOOTING_ZONE_FACTOR = 0.2

# Velocidade mínima real da bola (km/h, via homografia) no trecho analisado
# para considerar que foi "batida" (chute) e não apenas rolando/conduzida.
MIN_SHOT_SPEED_KMH = 40.0

# Janela de frames após a bola escapar da posse de um jogador, dentro da
# qual a trajetória da bola é avaliada como possível finalização.
SHOT_WINDOW_FRAMES = 4

# --- Falta ---

# IoU mínimo entre as bboxes de dois jogadores para considerar que houve
# contato físico entre eles (sobreposição, não apenas proximidade).
FALTA_CONTACT_IOU = 0.12

# Frames consecutivos mínimos de contato sustentado para não confundir um
# esbarrão casual de um único frame (ruído de tracking) com disputa física.
MIN_FALTA_CONTACT_FRAMES = 2

# Heurística mais aproximada deste incremento — nunca reporta confiança
# acima deste teto, mesmo quando os sinais (contato + posse disputada)
# estão presentes.
FALTA_CONFIDENCE_CEILING = 0.35


@dataclass
class DetectedEvent:
    event_type: EventType
    start_time_ms: int
    end_time_ms: int
    primary_track_id: int
    secondary_track_id: int | None
    confidence: float
    metadata: dict


def _bbox_center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2, (y1 + y2) / 2


def _bbox_diagonal(bbox: tuple[float, float, float, float]) -> float:
    x1, y1, x2, y2 = bbox
    return math.hypot(x2 - x1, y2 - y1)


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _iou(box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    inter_area = max(0.0, inter_x2 - inter_x1) * max(0.0, inter_y2 - inter_y1)
    if inter_area == 0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union_area = area_a + area_b - inter_area
    return inter_area / union_area if union_area > 0 else 0.0


class EventDetector:
    """Heurísticas sobre o tracking já produzido pela Fase 1
    (`sportslyze_cv.pipeline`). Recebe todas as detecções rastreadas
    (jogadores e bola misturados, cada uma com `frame_index`), o fps de
    amostragem usado na extração de frames (para converter índice de frame
    em timestamp) e, opcionalmente, a homografia do campo já calibrada
    (necessária apenas para "drible" com precisão real e "finalização";
    sem ela, "drible" cai para uma proxy em pixels e "finalização" não é
    detectada)."""

    def detect(
        self,
        tracked_positions: list[TrackedObject],
        sample_fps: float,
        homography: Homography | None = None,
    ) -> list[DetectedEvent]:
        possession_by_frame = self._possession_by_frame(tracked_positions)
        passe_events = self._events_from_possession(possession_by_frame, sample_fps)

        player_positions = self._player_positions_by_track(tracked_positions)
        ball_by_frame = self._ball_by_frame(tracked_positions)

        events = list(passe_events)
        events.extend(
            self._detect_drible(possession_by_frame, player_positions, sample_fps, homography)
        )
        events.extend(self._detect_triangulacao(passe_events))
        events.extend(
            self._detect_finalizacao(possession_by_frame, ball_by_frame, sample_fps, homography)
        )
        events.extend(self._detect_falta(passe_events, player_positions, sample_fps))
        return events

    # --- Posse de bola (base do "passe", inalterada) ---

    def _possession_by_frame(
        self, tracked_positions: list[TrackedObject]
    ) -> dict[int, tuple[int, float]]:
        by_frame: dict[int, list[TrackedObject]] = {}
        for obj in tracked_positions:
            by_frame.setdefault(obj.frame_index, []).append(obj)

        possession: dict[int, tuple[int, float]] = {}
        for frame_index, objs in by_frame.items():
            balls = [o for o in objs if o.detection_class == "ball"]
            players = [o for o in objs if o.detection_class == "player"]
            if not balls or not players:
                continue

            ball = max(balls, key=lambda o: o.confidence)
            ball_center = _bbox_center(ball.bbox_xyxy)

            nearest = min(players, key=lambda p: _distance(ball_center, _bbox_center(p.bbox_xyxy)))
            distance = _distance(ball_center, _bbox_center(nearest.bbox_xyxy))
            threshold = _bbox_diagonal(nearest.bbox_xyxy) * POSSESSION_PROXIMITY_FACTOR
            if threshold <= 0 or distance > threshold:
                continue

            closeness = max(0.0, 1 - distance / threshold)
            possession[frame_index] = (nearest.track_id, closeness)

        return possession

    def _events_from_possession(
        self, possession_by_frame: dict[int, tuple[int, float]], sample_fps: float
    ) -> list[DetectedEvent]:
        ordered_frames = sorted(possession_by_frame)
        if not ordered_frames:
            return []

        events: list[DetectedEvent] = []
        current_track_id, current_closeness = possession_by_frame[ordered_frames[0]]
        last_seen_frame = ordered_frames[0]

        for frame_index in ordered_frames[1:]:
            track_id, closeness = possession_by_frame[frame_index]
            gap = frame_index - last_seen_frame

            if track_id == current_track_id:
                current_closeness = max(current_closeness, closeness)
                last_seen_frame = frame_index
                continue

            if gap <= MAX_GAP_FRAMES + 1:
                confidence = round(min(current_closeness, closeness), 2)
                if confidence >= MIN_TRANSITION_CONFIDENCE:
                    events.append(
                        DetectedEvent(
                            event_type="passe",
                            start_time_ms=round(last_seen_frame / sample_fps * 1000),
                            end_time_ms=round(frame_index / sample_fps * 1000),
                            primary_track_id=current_track_id,
                            secondary_track_id=track_id,
                            confidence=confidence,
                            metadata={},
                        )
                    )

            current_track_id = track_id
            current_closeness = closeness
            last_seen_frame = frame_index

        return events

    # --- Índices auxiliares compartilhados pelas heurísticas novas ---

    def _player_positions_by_track(
        self, tracked_positions: list[TrackedObject]
    ) -> dict[int, dict[int, tuple[float, float, float, float]]]:
        positions: dict[int, dict[int, tuple[float, float, float, float]]] = {}
        for obj in tracked_positions:
            if obj.detection_class == "player":
                positions.setdefault(obj.track_id, {})[obj.frame_index] = obj.bbox_xyxy
        return positions

    def _ball_by_frame(self, tracked_positions: list[TrackedObject]) -> dict[int, TrackedObject]:
        balls_by_frame: dict[int, list[TrackedObject]] = {}
        for obj in tracked_positions:
            if obj.detection_class == "ball":
                balls_by_frame.setdefault(obj.frame_index, []).append(obj)
        return {frame: max(objs, key=lambda o: o.confidence) for frame, objs in balls_by_frame.items()}

    # --- Drible ---

    def _detect_drible(
        self,
        possession_by_frame: dict[int, tuple[int, float]],
        player_positions: dict[int, dict[int, tuple[float, float, float, float]]],
        sample_fps: float,
        homography: Homography | None,
    ) -> list[DetectedEvent]:
        ordered_frames = sorted(possession_by_frame)
        if not ordered_frames:
            return []

        events: list[DetectedEvent] = []
        run_track_id, run_min_closeness = possession_by_frame[ordered_frames[0]]
        run_start = ordered_frames[0]
        run_last_seen = ordered_frames[0]

        for frame_index in ordered_frames[1:]:
            track_id, closeness = possession_by_frame[frame_index]
            gap = frame_index - run_last_seen

            if track_id == run_track_id and gap <= MAX_GAP_FRAMES + 1:
                run_last_seen = frame_index
                run_min_closeness = min(run_min_closeness, closeness)
                continue

            event = self._maybe_drible_event(
                run_track_id, run_start, run_last_seen, run_min_closeness, player_positions, sample_fps, homography
            )
            if event:
                events.append(event)

            run_track_id, run_start, run_last_seen, run_min_closeness = (
                track_id,
                frame_index,
                frame_index,
                closeness,
            )

        event = self._maybe_drible_event(
            run_track_id, run_start, run_last_seen, run_min_closeness, player_positions, sample_fps, homography
        )
        if event:
            events.append(event)

        return events

    def _maybe_drible_event(
        self,
        track_id: int,
        start_frame: int,
        end_frame: int,
        min_closeness: float,
        player_positions: dict[int, dict[int, tuple[float, float, float, float]]],
        sample_fps: float,
        homography: Homography | None,
    ) -> DetectedEvent | None:
        if end_frame - start_frame + 1 < MIN_DRIBBLE_FRAMES:
            return None

        positions = player_positions.get(track_id, {})
        start_bbox = positions.get(start_frame)
        end_bbox = positions.get(end_frame)
        if start_bbox is None or end_bbox is None:
            return None

        start_center = _bbox_center(start_bbox)
        end_center = _bbox_center(end_bbox)

        if homography is not None:
            start_field = pixel_to_field(start_center, homography)
            end_field = pixel_to_field(end_center, homography)
            if _distance(start_field, end_field) < MIN_DRIBBLE_DISPLACEMENT_M:
                return None
        else:
            displacement_px = _distance(start_center, end_center)
            if displacement_px < _bbox_diagonal(start_bbox) * MIN_DRIBBLE_DISPLACEMENT_PX_FACTOR:
                return None

        return DetectedEvent(
            event_type="drible",
            start_time_ms=round(start_frame / sample_fps * 1000),
            end_time_ms=round(end_frame / sample_fps * 1000),
            primary_track_id=track_id,
            secondary_track_id=None,
            confidence=round(min_closeness, 2),
            metadata={},
        )

    # --- Triangulação ---

    def _detect_triangulacao(self, passe_events: list[DetectedEvent]) -> list[DetectedEvent]:
        if len(passe_events) < MIN_CHAIN_PASSES:
            return []

        events: list[DetectedEvent] = []
        chain = [passe_events[0]]

        for event in passe_events[1:]:
            prev = chain[-1]
            gap_ms = event.start_time_ms - prev.end_time_ms
            continues_chain = (
                event.primary_track_id == prev.secondary_track_id and 0 <= gap_ms <= MAX_CHAIN_GAP_MS
            )
            if continues_chain:
                chain.append(event)
                continue

            self._maybe_append_chain_event(chain, events)
            chain = [event]

        self._maybe_append_chain_event(chain, events)
        return events

    def _maybe_append_chain_event(
        self, chain: list[DetectedEvent], events: list[DetectedEvent]
    ) -> None:
        if len(chain) < MIN_CHAIN_PASSES:
            return

        distinct_players = {chain[0].primary_track_id}
        distinct_players.update(event.secondary_track_id for event in chain if event.secondary_track_id is not None)
        if len(distinct_players) < MIN_CHAIN_DISTINCT_PLAYERS:
            return

        avg_confidence = sum(event.confidence for event in chain) / len(chain)
        events.append(
            DetectedEvent(
                event_type="triangulacao",
                start_time_ms=chain[0].start_time_ms,
                end_time_ms=chain[-1].end_time_ms,
                primary_track_id=chain[0].primary_track_id,
                secondary_track_id=chain[-1].secondary_track_id,
                confidence=round(avg_confidence, 2),
                metadata={},
            )
        )

    # --- Finalização ---

    def _detect_finalizacao(
        self,
        possession_by_frame: dict[int, tuple[int, float]],
        ball_by_frame: dict[int, TrackedObject],
        sample_fps: float,
        homography: Homography | None,
    ) -> list[DetectedEvent]:
        if homography is None:
            return []

        ordered_frames = sorted(possession_by_frame)
        if len(ordered_frames) < 2:
            return []

        events: list[DetectedEvent] = []
        for i, frame_index in enumerate(ordered_frames[:-1]):
            track_id, _ = possession_by_frame[frame_index]
            next_frame = ordered_frames[i + 1]
            if next_frame - frame_index <= MAX_GAP_FRAMES + 1:
                continue  # posse recuperada rápido demais para ser um chute — mais provável um passe normal

            event = self._maybe_finalizacao_event(track_id, frame_index, ball_by_frame, sample_fps, homography)
            if event:
                events.append(event)

        return events

    def _maybe_finalizacao_event(
        self,
        shooter_track_id: int,
        release_frame: int,
        ball_by_frame: dict[int, TrackedObject],
        sample_fps: float,
        homography: Homography,
    ) -> DetectedEvent | None:
        window_frames = sorted(
            f for f in ball_by_frame if release_frame <= f <= release_frame + SHOT_WINDOW_FRAMES
        )
        if len(window_frames) < 2:
            return None

        elapsed_s = (window_frames[-1] - window_frames[0]) / sample_fps
        if elapsed_s <= 0:
            return None

        start_field = pixel_to_field(_bbox_center(ball_by_frame[window_frames[0]].bbox_xyxy), homography)
        end_field = pixel_to_field(_bbox_center(ball_by_frame[window_frames[-1]].bbox_xyxy), homography)

        speed_kmh = (_distance(start_field, end_field) / elapsed_s) * 3.6
        if speed_kmh < MIN_SHOT_SPEED_KMH:
            return None

        end_x = end_field[0]
        heading_to_near_goal = (end_x < FIELD_LENGTH_M / 2 and end_field[0] < start_field[0]) or (
            end_x >= FIELD_LENGTH_M / 2 and end_field[0] > start_field[0]
        )
        in_shooting_zone = end_x <= FIELD_LENGTH_M * SHOOTING_ZONE_FACTOR or end_x >= FIELD_LENGTH_M * (
            1 - SHOOTING_ZONE_FACTOR
        )
        if not (heading_to_near_goal and in_shooting_zone):
            return None

        confidence = round(min(1.0, speed_kmh / (MIN_SHOT_SPEED_KMH * 2)), 2)
        return DetectedEvent(
            event_type="finalizacao",
            start_time_ms=round(release_frame / sample_fps * 1000),
            end_time_ms=round(window_frames[-1] / sample_fps * 1000),
            primary_track_id=shooter_track_id,
            secondary_track_id=None,
            confidence=confidence,
            metadata={},
        )

    # --- Falta ---

    def _detect_falta(
        self,
        passe_events: list[DetectedEvent],
        player_positions: dict[int, dict[int, tuple[float, float, float, float]]],
        sample_fps: float,
    ) -> list[DetectedEvent]:
        events: list[DetectedEvent] = []
        for event in passe_events:
            if event.confidence >= FALTA_CONFIDENCE_CEILING or event.secondary_track_id is None:
                continue  # transição "limpa" o suficiente para ser só um passe, não uma disputa física

            start_frame = round(event.start_time_ms / 1000 * sample_fps)
            end_frame = round(event.end_time_ms / 1000 * sample_fps)
            positions_a = player_positions.get(event.primary_track_id, {})
            positions_b = player_positions.get(event.secondary_track_id, {})

            contact_frames = sum(
                1
                for frame_index in range(start_frame, end_frame + 1)
                if frame_index in positions_a
                and frame_index in positions_b
                and _iou(positions_a[frame_index], positions_b[frame_index]) >= FALTA_CONTACT_IOU
            )
            if contact_frames < MIN_FALTA_CONTACT_FRAMES:
                continue

            events.append(
                DetectedEvent(
                    event_type="falta",
                    start_time_ms=event.start_time_ms,
                    end_time_ms=event.end_time_ms,
                    primary_track_id=event.primary_track_id,
                    secondary_track_id=event.secondary_track_id,
                    confidence=round(min(FALTA_CONFIDENCE_CEILING, 1 - event.confidence), 2),
                    metadata={},
                )
            )

        return events
