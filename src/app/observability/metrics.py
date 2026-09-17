import threading
import time
from collections import Counter


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.started_at = time.time()
        self.requests = Counter()
        self.request_seconds = 0.0
        self.errors = Counter()

    def observe_request(self, method: str, path: str, status: int, seconds: float):
        key = (method, path, status)
        with self._lock:
            self.requests[key] += 1
            self.request_seconds += seconds
            if status >= 500:
                self.errors[(method, path)] += 1

    def prometheus(self) -> str:
        with self._lock:
            lines = [
                "# HELP specforge_uptime_seconds Process uptime in seconds",
                "# TYPE specforge_uptime_seconds gauge",
                f"specforge_uptime_seconds {time.time() - self.started_at:.3f}",
                "# HELP specforge_http_requests_total HTTP requests",
                "# TYPE specforge_http_requests_total counter",
            ]

            for (method, path, status), count in sorted(self.requests.items()):
                labels = f'method="{method}",path="{path}",status="{status}"'
                lines.append(
                    f"specforge_http_requests_total{{{labels}}} {count}"
                )

            lines += [
                "# HELP specforge_http_request_duration_seconds_total Total observed request duration",
                "# TYPE specforge_http_request_duration_seconds_total counter",
                f"specforge_http_request_duration_seconds_total {self.request_seconds:.6f}",
                "# HELP specforge_http_errors_total HTTP 5xx errors",
                "# TYPE specforge_http_errors_total counter",
            ]

            for (method, path), count in sorted(self.errors.items()):
                labels = f'method="{method}",path="{path}"'
                lines.append(
                    f"specforge_http_errors_total{{{labels}}} {count}"
                )

            return "\n".join(lines) + "\n"


metrics = Metrics()
