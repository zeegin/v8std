from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class McpCapacityConfigurationTests(unittest.TestCase):
    def test_nginx_http_fragment_has_capacity_and_reusable_upstream_limits(self):
        text = (ROOT / "deploy/nginx/http-v8std-mcp.conf").read_text(encoding="utf-8")

        self.assertIn("worker_rlimit_nofile 131072;", text)
        self.assertIn("rate=100r/s", text)
        self.assertIn("limit_conn_zone $server_name zone=v8std_mcp_connections:10m;", text)
        self.assertIn("server 127.0.0.1:8765 max_conns=2048;", text)
        self.assertIn("keepalive 256;", text)
        self.assertIn("429 2;", text)
        self.assertIn("503 5;", text)
        self.assertIn('map "$request_method:$http_accept" $v8std_reject_event_stream_get', text)

    def test_nginx_capacity_fragment_bounds_workers_and_client_keepalive(self):
        text = (ROOT / "deploy/nginx/nginx.conf.capacity-example").read_text(encoding="utf-8")

        self.assertIn("worker_processes auto;", text)
        self.assertIn("worker_shutdown_timeout 30s;", text)
        self.assertIn("worker_connections 65536;", text)
        self.assertIn("keepalive_timeout 30s;", text)

    def test_mcp_server_route_is_request_scoped(self):
        text = (ROOT / "deploy/nginx/server-v8std-mcp.conf").read_text(encoding="utf-8")

        self.assertIn("proxy_read_timeout 35s;", text)
        self.assertIn("proxy_next_upstream off;", text)
        self.assertIn("limit_req_status 429;", text)
        self.assertIn("limit_conn v8std_mcp_connections 40000;", text)
        self.assertIn("limit_conn_status 503;", text)
        self.assertIn("add_header Retry-After $v8std_retry_after always;", text)
        self.assertIn("proxy_intercept_errors on;", text)
        self.assertIn("error_page 502 504 =503 @v8std_mcp_backend_unavailable;", text)
        self.assertIn("proxy_set_header Connection \"\";", text)
        self.assertIn("if ($v8std_reject_event_stream_get)", text)
        self.assertIn('add_header Allow "POST, HEAD" always;', text)

    def test_systemd_limits_match_nginx_capacity_contract(self):
        text = (ROOT / "deploy/systemd/v8std-mcp.service").read_text(encoding="utf-8")

        self.assertIn("LimitNOFILE=131072", text)
        self.assertIn("TimeoutStopSec=45s", text)
        self.assertIn("KillMode=mixed", text)

    def test_capacity_document_does_not_claim_connection_count_is_rps(self):
        text = (ROOT / "spec/designs/2026-09-03-mcp-100k-agent-capacity-design.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("not an", text)
        self.assertIn("100,000 simultaneously connected coding agents", text)
        self.assertIn("measured per-replica capacity", text)


if __name__ == "__main__":
    unittest.main()
