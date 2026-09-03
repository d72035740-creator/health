from copy import deepcopy
from threading import RLock

from app.simulation.engine import simulation_engine
from app.timeline.models import (
    AequorTimelineEvent,
    ReplaySession,
    TimelineEventSource,
    TimelineEventType,
    TimelineReplaySnapshot,
)


class TimelineService:
    """Stores recorded facts. Projection never invokes intelligence algorithms."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._session_counter = 0
        self._sessions: list[dict[str, object]] = []
        self._last_temporal_state: str | None = None
        self._last_decision_state: str = "CALIBRATING"
        self._new_session("INITIAL_SESSION")
        simulation_engine.register_reset_hook(self.on_full_reset)

    def _new_session(self, boundary: str) -> None:
        self._session_counter += 1
        self._sessions.append({
            "session_id": f"replay-session-{self._session_counter}",
            "started": simulation_engine.snapshot().simulated_time,
            "boundary": boundary,
            "events": [],
        })
        self._last_temporal_state = None
        self._last_decision_state = "CALIBRATING"

    def on_full_reset(self) -> None:
        with self._lock:
            self._new_session("FULL_RESET")
            self.append(
                TimelineEventType.SYSTEM_RESET,
                TimelineEventSource.SIMULATION_CONTROL,
                "System reset",
                "A new replay session began at the full-reset boundary.",
            )

    def append(
        self,
        event_type: TimelineEventType,
        source: TimelineEventSource,
        title: str,
        summary: str,
        *,
        simulated_time=None,
        runtime_cycle_id: str | None = None,
        scenario_ground_truth: dict[str, object] | None = None,
        measurement_summary: dict[str, object] | None = None,
        ml_summary: dict[str, object] | None = None,
        temporal_summary: dict[str, object] | None = None,
        confounder_summary: dict[str, object] | None = None,
        decision_summary: dict[str, object] | None = None,
    ) -> AequorTimelineEvent:
        with self._lock:
            events = self._sessions[-1]["events"]
            sequence = len(events) + 1
            event = AequorTimelineEvent(
                event_id=f"{self._sessions[-1]['session_id']}:event:{sequence}",
                sequence_index=sequence,
                simulated_time=simulated_time or simulation_engine.snapshot().simulated_time,
                event_type=event_type,
                source=source,
                title=title,
                summary=summary,
                runtime_cycle_id=runtime_cycle_id,
                scenario_ground_truth=deepcopy(scenario_ground_truth),
                measurement_summary=deepcopy(measurement_summary),
                ml_summary=deepcopy(ml_summary),
                temporal_summary=deepcopy(temporal_summary),
                confounder_summary=deepcopy(confounder_summary),
                decision_summary=deepcopy(decision_summary),
            )
            events.append(event)
            return event.model_copy(deep=True)

    def record_runtime_cycle(self, runtime_snapshot, scenario_truth: dict[str, object]) -> None:
        attempt = runtime_snapshot.attempt
        cycle_id = runtime_snapshot.cycle_id
        time = runtime_snapshot.simulated_time
        self.append(TimelineEventType.MEASUREMENT_CYCLE_STARTED, TimelineEventSource.RUNTIME, "Measurement cycle started", f"Runtime cycle {runtime_snapshot.cycle_index} started.", simulated_time=time, runtime_cycle_id=cycle_id, scenario_ground_truth=scenario_truth)
        quality = attempt.quality_assessment
        measurement = {
            "technical_quality": quality.qualification.value,
            "quality_score": quality.overall_score,
            "rejection_reasons": [x.value for x in quality.rejection_reasons],
            "left_relative_pattern": None,
            "right_relative_pattern": None,
        }
        if attempt.baseline_comparison:
            values = {x.name: x.signed_normalized_delta for x in attempt.baseline_comparison.values}
            left = [v for k, v in values.items() if k.startswith("left_")]
            right = [v for k, v in values.items() if k.startswith("right_")]
            measurement["left_relative_pattern"] = 100 + (sum(left) / len(left) if left else 0)
            measurement["right_relative_pattern"] = 100 + (sum(right) / len(right) if right else 0)
        if quality.qualification.value == "REJECTED":
            self.append(TimelineEventType.MEASUREMENT_REJECTED, TimelineEventSource.QUALITY_ENGINE, "Measurement rejected", f"{', '.join(measurement['rejection_reasons']) or 'Technical quality rejected'}; measurement not used and decision state unchanged.", simulated_time=time, runtime_cycle_id=cycle_id, scenario_ground_truth=scenario_truth, measurement_summary=measurement)
            return
        temporal = attempt.temporal_assessment.model_dump(mode="json") if attempt.temporal_assessment else None
        confounder = attempt.confounder_assessment.model_dump(mode="json") if attempt.confounder_assessment else None
        decision = attempt.decision_snapshot.model_dump(mode="json") if attempt.decision_snapshot else None
        ml = attempt.ml_inference.model_dump(mode="json") if attempt.ml_inference else None
        self.append(TimelineEventType.MEASUREMENT_QUALIFIED, TimelineEventSource.QUALITY_ENGINE, "Qualified measurement", "Technical quality passed; recorded downstream evidence is attached when available.", simulated_time=time, runtime_cycle_id=cycle_id, scenario_ground_truth=scenario_truth, measurement_summary=measurement, ml_summary=ml, temporal_summary=temporal, confounder_summary=confounder, decision_summary=decision)
        if attempt.ml_inference:
            self.append(TimelineEventType.ML_INFERENCE_COMPLETED, TimelineEventSource.ML_ENGINE, "ML inference completed", "Recorded local TinyML novelty evidence.", simulated_time=time, runtime_cycle_id=cycle_id, ml_summary=ml)
        elif runtime_snapshot.pipeline_status.value == "ML_UNAVAILABLE":
            self.append(TimelineEventType.MODEL_UNAVAILABLE, TimelineEventSource.ML_ENGINE, "ML inference unavailable", "No model inference or downstream AI result was produced.", simulated_time=time, runtime_cycle_id=cycle_id)
        if temporal:
            state = temporal["temporal_state"]
            if state != self._last_temporal_state:
                self.append(TimelineEventType.TEMPORAL_STATE_CHANGED, TimelineEventSource.TEMPORAL_ENGINE, "Temporal state changed", f"Temporal evidence entered {state}.", simulated_time=time, runtime_cycle_id=cycle_id, temporal_summary=temporal)
                self._last_temporal_state = state
                if state == "RECOVERING_PATTERN":
                    self.append(TimelineEventType.RECOVERY_OBSERVED, TimelineEventSource.TEMPORAL_ENGINE, "Recovery observed", "A subsequent qualified observation created recorded recovery evidence.", simulated_time=time, runtime_cycle_id=cycle_id, temporal_summary=temporal)
        if decision:
            state = decision["surveillance_state"]
            if state != self._last_decision_state:
                self.append(TimelineEventType.SURVEILLANCE_STATE_CHANGED, TimelineEventSource.DECISION_ENGINE, "Surveillance state changed", f"Recorded state changed from {self._last_decision_state} to {state}.", simulated_time=time, runtime_cycle_id=cycle_id, decision_summary=decision)
                self._last_decision_state = state

    def events(self) -> list[AequorTimelineEvent]:
        with self._lock:
            return [event.model_copy(deep=True) for event in self._sessions[-1]["events"]]

    def session_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def projection(self, *, include_ground_truth: bool, baseline_status: str, current_state: str) -> TimelineReplaySnapshot:
        with self._lock:
            stored = [event.model_copy(deep=True) for event in self._sessions[-1]["events"]]
            session_data = self._sessions[-1].copy()
        if not include_ground_truth:
            stored = [event.model_copy(update={"scenario_ground_truth": None}, deep=True) for event in stored if event.source is not TimelineEventSource.SCENARIO_ENGINE]
        measurements = [x for x in stored if x.event_type in (TimelineEventType.MEASUREMENT_QUALIFIED, TimelineEventType.MEASUREMENT_REJECTED)]
        qualified = [x for x in measurements if x.event_type is TimelineEventType.MEASUREMENT_QUALIFIED]
        rejected = [x for x in measurements if x.event_type is TimelineEventType.MEASUREMENT_REJECTED]
        duration = (stored[-1].simulated_time - session_data["started"]).total_seconds() if stored else 0.0
        trend = {"bilateral": [], "novelty": [], "adi": []}
        for event in qualified:
            if event.measurement_summary:
                trend["bilateral"].append({"simulated_time": event.simulated_time, "left": event.measurement_summary.get("left_relative_pattern"), "right": event.measurement_summary.get("right_relative_pattern")})
            if event.ml_summary or event.temporal_summary:
                trend["novelty"].append({"simulated_time": event.simulated_time, "novelty_z": (event.ml_summary or {}).get("novelty_z"), "ewma": (event.temporal_summary or {}).get("ewma_novelty")})
            if event.decision_summary:
                trend["adi"].append({"simulated_time": event.simulated_time, "adi": event.decision_summary.get("adi")})
        state_points = [x for x in stored if x.event_type is TimelineEventType.SURVEILLANCE_STATE_CHANGED and x.decision_summary]
        bands = []
        for index, event in enumerate(state_points):
            bands.append({"state": event.decision_summary["surveillance_state"], "start_time": event.simulated_time, "end_time": state_points[index + 1].simulated_time if index + 1 < len(state_points) else (stored[-1].simulated_time if stored else event.simulated_time)})
        return TimelineReplaySnapshot(
            title="AEQUOR LONGITUDINAL REPLAY", observer_only=not include_ground_truth,
            ground_truth_disclosure="Ground truth is for engineering comparison and was not provided to Aequor intelligence.",
            session=ReplaySession(session_id=session_data["session_id"],started_at_simulated_time=session_data["started"],event_count=len(stored),baseline_status=baseline_status,starting_state="CALIBRATING",current_state=current_state,reset_boundary=session_data["boundary"]),
            duration_seconds=max(0.0,duration),measurement_count=len(measurements),qualified_measurements=len(qualified),rejected_measurements=len(rejected),events=stored,trend_series=trend,state_bands=bands)


timeline_service = TimelineService()
