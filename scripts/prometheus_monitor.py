from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

@dataclass
class PrometheusConfig:
    base_url: str
    bearer_token: Optional[str] = None
    timeout: int = 15
    verify_ssl: bool = True

class PrometheusClient:
    def __init__(self, config: PrometheusConfig) -> None:
        self.config = config

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.bearer_token:
            headers["Authorization"] = f"Bearer {self.config.bearer_token}"
        return headers

    def query(self, promql: str) -> List[Dict[str, Any]]:
        url = f"{self.config.base_url.rstrip('/')}/api/v1/query"
        resp = requests.get(
            url,
            headers=self._headers(),
            params={"query": promql},
            timeout=self.config.timeout,
            verify=self.config.verify_ssl,
        )
        resp.raise_for_status()

        payload = resp.json()
        if payload.get("status") != "success":
            raise RuntimeError(f"Prometheus query failed: {payload}")

        return payload["data"]["result"]

class BookinfoMonitor:
    def __init__(self, prometheus: PrometheusClient, namespace: str = "bookinfo") -> None:
        self.prometheus = prometheus
        self.namespace = namespace

    def get_pod_cpu_usage(self) -> List[Dict[str, Any]]:
        promql = f'''
        sum by (pod) (
          rate(container_cpu_usage_seconds_total{{
            namespace="{self.namespace}",
            container!="",
            container!="POD",
            image!=""
          }}[5m])
        )
        '''
        results = self.prometheus.query(promql)
        data = []
        for item in results:
            data.append({
                "pod": item["metric"].get("pod", "unknown"),
                "cpu_cores": float(item["value"][1]),
            })
        return sorted(data, key=lambda x: x["pod"])

    def get_pod_memory_usage(self) -> List[Dict[str, Any]]:
        promql = f'''
        sum by (pod) (
          container_memory_working_set_bytes{{
            namespace="{self.namespace}",
            container!="",
            container!="POD",
            image!=""
          }}
        )
        '''
        results = self.prometheus.query(promql)
        data = []
        for item in results:
            data.append({
                "pod": item["metric"].get("pod", "unknown"),
                "memory_bytes": float(item["value"][1]),
            })
        return sorted(data, key=lambda x: x["pod"])

    def get_pod_restart_count(self) -> List[Dict[str, Any]]:
        promql = f'''
        sum by (pod) (
          kube_pod_container_status_restarts_total{{
            namespace="{self.namespace}"
          }}
        )
        '''
        results = self.prometheus.query(promql)
        data = []
        for item in results:
            data.append({
                "pod": item["metric"].get("pod", "unknown"),
                "restart_count": int(float(item["value"][1])),
            })
        return sorted(data, key=lambda x: x["pod"])

def bytes_to_mib(num_bytes: float) -> float:
    return num_bytes / 1024 / 1024

if __name__ == "__main__":
    client = PrometheusClient(
        PrometheusConfig(
            base_url="http://localhost:9090",
            bearer_token=None,
            verify_ssl=False,
        )
    )

    monitor = BookinfoMonitor(client, namespace="bookinfo")

    print("=== Pod CPU Usage ===")
    for item in monitor.get_pod_cpu_usage():
        print(f"{item['pod']}: {item['cpu_cores']:.4f} cores")

    print("\n=== Pod Memory Usage ===")
    for item in monitor.get_pod_memory_usage():
        print(f"{item['pod']}: {bytes_to_mib(item['memory_bytes']):.2f} MiB")

    print("\n=== Pod Restart Count ===")
    for item in monitor.get_pod_restart_count():
        print(f"{item['pod']}: {item['restart_count']}")
