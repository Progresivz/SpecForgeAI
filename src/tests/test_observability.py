from app.observability.metrics import Metrics


def test_metrics_prometheus_output():
    m = Metrics()
    m.observe_request("GET", "/health", 200, 0.01)
    m.observe_request("GET", "/health", 500, 0.02)
    text = m.prometheus()
    assert "specforge_http_requests_total" in text
    assert 'method="GET",path="/health",status="200"' in text
    assert 'status="500"' in text
