"""Analytics tracking utilities for Phase 3 insights."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

DEFAULT_ANALYTICS_PATH = "data/analytics.json"
DEFAULT_MAX_RUN_LOGS = 200


@dataclass(slots=True)
class AlgorithmRun:
    """A single algorithm execution snapshot."""

    timestamp: str
    algorithm: str
    time_us: float
    nodes_visited: int
    cost: float
    found: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "algorithm": self.algorithm,
            "time_us": self.time_us,
            "nodes_visited": self.nodes_visited,
            "cost": self.cost,
            "found": self.found,
        }


class AnalyticsStore:
    """File-backed analytics aggregation for search and routing events."""

    def __init__(
        self,
        storage_path: str = DEFAULT_ANALYTICS_PATH,
        *,
        max_run_logs: int = DEFAULT_MAX_RUN_LOGS,
    ) -> None:
        self.storage_path = Path(storage_path)
        self.max_run_logs = max_run_logs

    def _default_payload(self) -> dict[str, Any]:
        return {
            "search_terms": {},
            "route_counts": {},
            "node_visit_counts": {},
            "algorithm_runs": [],
        }

    def _load(self) -> dict[str, Any]:
        if not self.storage_path.exists():
            return self._default_payload()

        try:
            loaded = json.loads(self.storage_path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                return self._default_payload()
        except (OSError, json.JSONDecodeError):
            return self._default_payload()

        payload = self._default_payload()
        payload.update(loaded)
        return payload

    def _save(self, payload: dict[str, Any]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def track_search(self, query: str) -> None:
        clean = query.strip().lower()
        if not clean:
            return

        payload = self._load()
        terms = dict(payload.get("search_terms", {}))
        terms[clean] = int(terms.get(clean, 0)) + 1
        payload["search_terms"] = terms
        self._save(payload)

    def track_route(self, path: list[str]) -> None:
        if len(path) < 2:
            return

        payload = self._load()

        route_key = f"{path[0]}->{path[-1]}"
        routes = dict(payload.get("route_counts", {}))
        routes[route_key] = int(routes.get(route_key, 0)) + 1
        payload["route_counts"] = routes

        visits = dict(payload.get("node_visit_counts", {}))
        for node_id in path:
            visits[node_id] = int(visits.get(node_id, 0)) + 1
        payload["node_visit_counts"] = visits

        self._save(payload)

    def track_algorithm_result(self, algorithm: str, result: dict[str, Any]) -> None:
        payload = self._load()
        runs = list(payload.get("algorithm_runs", []))

        run = AlgorithmRun(
            timestamp=datetime.now(timezone.utc).isoformat(),
            algorithm=algorithm,
            time_us=float(result.get("time_us", 0.0)),
            nodes_visited=int(result.get("nodes_visited", 0)),
            cost=float(result.get("cost", 0.0)) if result.get("found") else float("inf"),
            found=bool(result.get("found", False)),
        )
        runs.append(run.to_dict())
        if len(runs) > self.max_run_logs:
            runs = runs[-self.max_run_logs :]

        payload["algorithm_runs"] = runs
        self._save(payload)

    def top_search_terms(self, limit: int = 5) -> list[tuple[str, int]]:
        payload = self._load()
        terms = payload.get("search_terms", {})
        return sorted(terms.items(), key=lambda x: x[1], reverse=True)[:limit]

    def top_routes(self, limit: int = 5) -> list[tuple[str, int]]:
        payload = self._load()
        routes = payload.get("route_counts", {})
        return sorted(routes.items(), key=lambda x: x[1], reverse=True)[:limit]

    def slow_areas(self, limit: int = 5) -> list[tuple[str, int]]:
        payload = self._load()
        visits = payload.get("node_visit_counts", {})
        return sorted(visits.items(), key=lambda x: x[1], reverse=True)[:limit]

    def algorithm_summary(self) -> dict[str, dict[str, float]]:
        payload = self._load()
        runs = payload.get("algorithm_runs", [])

        grouped: dict[str, list[dict[str, Any]]] = {}
        for run in runs:
            grouped.setdefault(str(run.get("algorithm", "unknown")), []).append(run)

        summary: dict[str, dict[str, float]] = {}
        for algorithm, items in grouped.items():
            if not items:
                continue
            total = float(len(items))
            avg_time = sum(float(i.get("time_us", 0.0)) for i in items) / total
            avg_nodes = sum(float(i.get("nodes_visited", 0.0)) for i in items) / total
            success_rate = sum(1 for i in items if i.get("found")) / total
            summary[algorithm] = {
                "runs": total,
                "avg_time_us": avg_time,
                "avg_nodes_visited": avg_nodes,
                "success_rate": success_rate,
            }

        return summary
