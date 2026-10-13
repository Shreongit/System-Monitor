import time
from typing import Dict, Any


class Aggregator:
    def __init__(self):
        self.prev_network = None  # (timestamp, counters dict)
        self.prev_disk_io = None  # (timestamp, counters dict)

    def update_and_aggregate(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        ts = sample.get("timestamp", time.time())
        result = dict(sample)  # shallow copy

        # network rates
        net = sample.get("network", {})
        if self.prev_network is None:
            net_rates = self._zero_net_rates(net)
        else:
            net_rates = self._compute_net_rates(self.prev_network, (ts, net))
        self.prev_network = (ts, net)
        result["network_rates"] = net_rates

        # disk io rates (use counters in disks.counters)
        disk_counters = sample.get("disks", {}).get("counters", {})
        if self.prev_disk_io is None:
            disk_rates = {"read_bytes_per_sec": 0.0, "write_bytes_per_sec": 0.0}
        else:
            disk_rates = self._compute_disk_rates(self.prev_disk_io, (ts, disk_counters))
        self.prev_disk_io = (ts, disk_counters)
        result["disk_io_rates"] = disk_rates

        return result

    def _zero_net_rates(self, net):
        return {iface: {"bytes_sent_per_sec": 0.0, "bytes_recv_per_sec": 0.0} for iface in net.keys()}

    def _compute_net_rates(self, prev, current):
        prev_ts, prev_net = prev
        cur_ts, cur_net = current
        delta_t = max(cur_ts - prev_ts, 1e-6)
        out = {}
        for iface, cur_stats in cur_net.items():
            prev_stats = prev_net.get(iface)
            if prev_stats:
                out[iface] = {
                    "bytes_sent_per_sec": (cur_stats.get("bytes_sent", 0) - prev_stats.get("bytes_sent", 0)) / delta_t,
                    "bytes_recv_per_sec": (cur_stats.get("bytes_recv", 0) - prev_stats.get("bytes_recv", 0)) / delta_t,
                }
            else:
                out[iface] = {"bytes_sent_per_sec": 0.0, "bytes_recv_per_sec": 0.0}
        return out

    def _compute_disk_rates(self, prev, current):
        prev_ts, prev_c = prev
        cur_ts, cur_c = current
        delta_t = max(cur_ts - prev_ts, 1e-6)
        read_delta = (cur_c.get("io_read_bytes", 0) - prev_c.get("io_read_bytes", 0)) / delta_t
        write_delta = (cur_c.get("io_write_bytes", 0) - prev_c.get("io_write_bytes", 0)) / delta_t
        return {"read_bytes_per_sec": max(read_delta, 0.0), "write_bytes_per_sec": max(write_delta, 0.0)}