"""Real telegraf MQTT payload samples, captured via
`mosquitto_sub -t 'systems/#' -v` against a live broker. Used to build
and test parsers.py against actual payload shapes rather than guesses.

Each value is a list of one or more raw telegraf JSON payloads (already
json.loads'd) for a given measurement/host/tag combination.
"""

PAYLOADS = {
    "cpu_tower": [
        {
            "fields": {
                "usage_guest": 0,
                "usage_guest_nice": 0,
                "usage_idle": 73.84097154747792,
                "usage_iowait": 0.8465561560044863,
                "usage_irq": 0,
                "usage_nice": 2.3579469903908903,
                "usage_softirq": 0.3146884141245198,
                "usage_steal": 0,
                "usage_system": 16.88680081500853,
                "usage_user": 5.753036078438396
            },
            "name": "cpu",
            "tags": {
                "cpu": "cpu-total",
                "host": "Tower"
            },
            "timestamp": 1787941820
        }
    ],
    "cpu_openwrt": [
        {
            "fields": {
                "usage_guest": 0,
                "usage_guest_nice": 0,
                "usage_idle": 95.08141398792922,
                "usage_iowait": 0,
                "usage_irq": 0.8858516831133878,
                "usage_nice": 0,
                "usage_softirq": 2.2357209145195873,
                "usage_steal": 0,
                "usage_system": 1.5860963469292941,
                "usage_user": 0.21091706741028796
            },
            "name": "cpu",
            "tags": {
                "cpu": "cpu-total",
                "host": "openwrt"
            },
            "timestamp": 1787941800
        }
    ],
    "mem_framework": [
        {
            "fields": {
                "active": 8052920320,
                "available": 26232811520,
                "available_percent": 79.71158435687718,
                "buffered": 851968,
                "cached": 19650228224,
                "commit_limit": 85577195520,
                "committed_as": 22769053696,
                "dirty": 258048,
                "free": 7384702976,
                "high_free": 0,
                "high_total": 0,
                "huge_page_size": 2097152,
                "huge_pages_free": 0,
                "huge_pages_total": 0,
                "inactive": 11806543872,
                "low_free": 0,
                "low_total": 0,
                "mapped": 1194168320,
                "page_tables": 53866496,
                "shared": 255107072,
                "slab": 2985951232,
                "sreclaimable": 2624266240,
                "sunreclaim": 361684992,
                "swap_cached": 0,
                "swap_free": 69122007040,
                "swap_total": 69122367488,
                "total": 32909660160,
                "used": 6676848640,
                "used_percent": 20.288415643122825,
                "vmalloc_chunk": 0,
                "vmalloc_total": 35184372087808,
                "vmalloc_used": 259641344,
                "write_back": 0,
                "write_back_tmp": 0
            },
            "name": "mem",
            "tags": {
                "host": "Framework_13"
            },
            "timestamp": 1787941830
        }
    ],
    "disk_root_tower": [
        {
            "fields": {
                "free": 30062682112,
                "inodes_free": 8147960,
                "inodes_total": 8204669,
                "inodes_used": 56709,
                "inodes_used_percent": 0.6911796197994093,
                "total": 33606324224,
                "used": 3543642112,
                "used_percent": 10.544569195905405
            },
            "name": "disk",
            "tags": {
                "device": "rootfs",
                "fstype": "rootfs",
                "host": "Tower",
                "mode": "rw",
                "path": "/"
            },
            "timestamp": 1787941820
        }
    ],
    "disk_root_framework": [
        {
            "fields": {
                "free": 1587975618560,
                "inodes_free": 0,
                "inodes_total": 0,
                "inodes_used": 0,
                "inodes_used_percent": 0,
                "total": 1963866832896,
                "used": 373555429376,
                "used_percent": 19.04407425868021
            },
            "name": "disk",
            "tags": {
                "device": "nvme0n1p2",
                "fstype": "btrfs",
                "host": "Framework_13",
                "mode": "rw",
                "path": "/"
            },
            "timestamp": 1787941830
        }
    ],
    "system_load_tower": [
        {
            "fields": {
                "load1": 5.95,
                "load15": 7.66,
                "load5": 6.54,
                "n_cpus": 24,
                "n_physical_cpus": 12,
                "n_unique_users": 0,
                "n_users": 0
            },
            "name": "system",
            "tags": {
                "host": "Tower"
            },
            "timestamp": 1787941820
        }
    ],
    "system_uptime_tower": [
        {
            "fields": {
                "uptime": 3966433
            },
            "name": "system",
            "tags": {
                "host": "Tower"
            },
            "timestamp": 1787941820
        }
    ],
    "system_uptime_format_tower": [
        {
            "fields": {
                "uptime_format": "45 days, 21:47"
            },
            "name": "system",
            "tags": {
                "host": "Tower"
            },
            "timestamp": 1787941820
        }
    ],
    "docker_tower": [
        {
            "fields": {
                "n_containers": 97,
                "n_containers_paused": 0,
                "n_containers_running": 79,
                "n_containers_stopped": 18,
                "n_cpus": 24,
                "n_goroutines": 634,
                "n_images": 104,
                "n_listener_events": 0,
                "n_used_file_descriptors": 724
            },
            "name": "docker",
            "tags": {
                "engine_host": "Tower",
                "host": "Tower",
                "server_version": "29.5.3"
            },
            "timestamp": 1787941820
        }
    ],
    "nvidia_smi_tower": [
        {
            "fields": {
                "clocks_current_graphics": 139,
                "clocks_current_memory": 405,
                "clocks_current_sm": 139,
                "clocks_current_video": 544,
                "cuda_version": "13.0",
                "display_active": "Disabled",
                "display_mode": "Requested",
                "driver_version": "580.173.02",
                "encoder_stats_average_fps": 0,
                "encoder_stats_average_latency": 0,
                "encoder_stats_session_count": 0,
                "fan_speed": 45,
                "fbc_stats_average_fps": 0,
                "fbc_stats_average_latency": 0,
                "fbc_stats_session_count": 0,
                "memory_free": 4027,
                "memory_reserved": 68,
                "memory_total": 4096,
                "memory_used": 3,
                "pcie_link_gen_current": 1,
                "pcie_link_width_current": 4,
                "power_limit": 75,
                "temperature_gpu": 29,
                "utilization_decoder": 0,
                "utilization_encoder": 0,
                "utilization_gpu": 0,
                "utilization_memory": 2,
                "vbios_version": "86.07.39.40.23"
            },
            "name": "nvidia_smi",
            "tags": {
                "arch": "Pascal",
                "compute_mode": "Default",
                "host": "Tower",
                "index": "0",
                "name": "NVIDIA GeForce GTX 1050 Ti",
                "pstate": "P8",
                "uuid": "GPU-9eeb3835-c5bd-dac6-c0df-ce151c8fe48c"
            },
            "timestamp": 1787941820
        },
        {
            "fields": {
                "clocks_current_graphics": 139,
                "clocks_current_memory": 405,
                "clocks_current_sm": 139,
                "clocks_current_video": 544,
                "cuda_version": "13.0",
                "display_active": "Disabled",
                "display_mode": "Requested",
                "driver_version": "580.173.02",
                "encoder_stats_average_fps": 0,
                "encoder_stats_average_latency": 0,
                "encoder_stats_session_count": 0,
                "fan_speed": 0,
                "fbc_stats_average_fps": 0,
                "fbc_stats_average_latency": 0,
                "fbc_stats_session_count": 0,
                "memory_free": 8105,
                "memory_reserved": 85,
                "memory_total": 8192,
                "memory_used": 3,
                "pcie_link_gen_current": 1,
                "pcie_link_width_current": 16,
                "power_draw": 8.99,
                "power_limit": 185,
                "temperature_gpu": 34,
                "utilization_decoder": 0,
                "utilization_encoder": 0,
                "utilization_gpu": 0,
                "utilization_memory": 0,
                "vbios_version": "86.04.50.00.70"
            },
            "name": "nvidia_smi",
            "tags": {
                "arch": "Pascal",
                "compute_mode": "Default",
                "host": "Tower",
                "index": "1",
                "name": "NVIDIA GeForce GTX 1070",
                "pstate": "P8",
                "uuid": "GPU-a3032886-0acb-0232-bc54-3d5ecad66035"
            },
            "timestamp": 1787941820
        }
    ],
    "nvidia_smi_desktop": [
        {
            "fields": {
                "clocks_current_graphics": 210,
                "clocks_current_memory": 405,
                "clocks_current_sm": 210,
                "clocks_current_video": 555,
                "cuda_version": "13.0",
                "display_active": "Enabled",
                "display_mode": "Requested",
                "driver_version": "580.95.05",
                "ecc_errors_channel_repair_pending": "No",
                "ecc_errors_tpc_repair_pending": "No",
                "encoder_stats_average_fps": 0,
                "encoder_stats_average_latency": 0,
                "encoder_stats_session_count": 0,
                "fan_speed": 0,
                "fbc_stats_average_fps": 0,
                "fbc_stats_average_latency": 0,
                "fbc_stats_session_count": 0,
                "memory_free": 6067,
                "memory_reserved": 353,
                "memory_total": 8192,
                "memory_used": 1773,
                "pcie_link_gen_current": 1,
                "pcie_link_width_current": 16,
                "power_draw": 21.4,
                "power_limit": 310,
                "temperature_gpu": 49,
                "utilization_decoder": 0,
                "utilization_encoder": 0,
                "utilization_gpu": 38,
                "utilization_jpeg": 0,
                "utilization_memory": 23,
                "utilization_ofa": 0,
                "vbios_version": "94.04.5A.00.F0"
            },
            "name": "nvidia_smi",
            "tags": {
                "arch": "Ampere",
                "compute_mode": "Default",
                "host": "Desktop-STRIX",
                "index": "0",
                "name": "NVIDIA GeForce RTX 3070 Ti",
                "pstate": "P8",
                "uuid": "GPU-6dd87557-13a0-1dcb-eb56-2804e0d56ffd"
            },
            "timestamp": 1787941820
        }
    ],
    "sensors_desktop_tctl": [
        {
            "fields": {
                "temp_input": 44.5
            },
            "name": "sensors",
            "tags": {
                "chip": "k10temp-pci-00c3",
                "feature": "tctl",
                "host": "Desktop-STRIX"
            },
            "timestamp": 1787941820
        }
    ],
    "sensors_framework": [
        {
            "fields": {
                "in_input": 0.75
            },
            "name": "sensors",
            "tags": {
                "chip": "amdgpu-pci-c100",
                "feature": "vddgfx",
                "host": "Framework_13"
            },
            "timestamp": 1787941830
        },
        {
            "fields": {
                "in_input": 0.854
            },
            "name": "sensors",
            "tags": {
                "chip": "amdgpu-pci-c100",
                "feature": "vddnb",
                "host": "Framework_13"
            },
            "timestamp": 1787941830
        },
        {
            "fields": {
                "temp_input": 42
            },
            "name": "sensors",
            "tags": {
                "chip": "amdgpu-pci-c100",
                "feature": "edge",
                "host": "Framework_13"
            },
            "timestamp": 1787941830
        }
    ],
    "temp_ha_pi": [
        {
            "fields": {
                "temp": 54.55
            },
            "name": "temp",
            "tags": {
                "host": "ha-pi",
                "sensor": "cpu_thermal"
            },
            "timestamp": 1787941830
        },
        {
            "fields": {
                "temp": 60.701
            },
            "name": "temp",
            "tags": {
                "host": "ha-pi",
                "sensor": "rp1_adc"
            },
            "timestamp": 1787941830
        }
    ],
    "temp_pihole": [
        {
            "fields": {
                "temp": 49.05
            },
            "name": "temp",
            "tags": {
                "host": "pihole",
                "sensor": "cpu_thermal"
            },
            "timestamp": 1787941800
        },
        {
            "fields": {
                "temp": 50.242
            },
            "name": "temp",
            "tags": {
                "host": "pihole",
                "sensor": "rp1_adc"
            },
            "timestamp": 1787941800
        }
    ],
    "temp_tower": [
        {
            "fields": {
                "temp": 37.85
            },
            "name": "temp",
            "tags": {
                "host": "Tower",
                "sensor": "nvme_composite"
            },
            "timestamp": 1787941820
        },
        {
            "fields": {
                "temp": 37.85
            },
            "name": "temp",
            "tags": {
                "host": "Tower",
                "sensor": "nvme_sensor_1"
            },
            "timestamp": 1787941820
        },
        {
            "fields": {
                "temp": 43.85
            },
            "name": "temp",
            "tags": {
                "host": "Tower",
                "sensor": "nvme_sensor_2"
            },
            "timestamp": 1787941820
        }
    ],
    "battery_framework": [
        {
            "fields": {
                "value": 79
            },
            "name": "battery",
            "tags": {
                "host": "Framework_13"
            },
            "timestamp": 1787941680
        }
    ],
    "net_openwrt": [
        {
            "fields": {
                "bytes_recv": 6453366687186,
                "bytes_sent": 24762742786103,
                "drop_in": 10788869,
                "drop_out": 9,
                "err_in": 968,
                "err_out": 0,
                "packets_recv": 12331183274,
                "packets_sent": 23748372927,
                "speed": 2500
            },
            "name": "net",
            "tags": {
                "host": "openwrt",
                "interface": "eth0"
            },
            "timestamp": 1787941800
        }
    ],
    "dns_query_openwrt": [
        {
            "fields": {
                "name": "google.com.",
                "query_time_ms": 10.035126,
                "rcode_value": 0,
                "result_code": 0
            },
            "name": "dns_query",
            "tags": {
                "domain": "google.com",
                "host": "openwrt",
                "rcode": "NOERROR",
                "record_type": "A",
                "result": "success",
                "server": "1.1.1.1"
            },
            "timestamp": 1787941800
        },
        {
            "fields": {
                "name": "google.com.",
                "query_time_ms": 16.415799,
                "rcode_value": 0,
                "result_code": 0
            },
            "name": "dns_query",
            "tags": {
                "domain": "google.com",
                "host": "openwrt",
                "rcode": "NOERROR",
                "record_type": "A",
                "result": "success",
                "server": "8.8.8.8"
            },
            "timestamp": 1787941800
        }
    ],
    "cpu_desktop": [
        {
            "fields": {
                "usage_guest": 0,
                "usage_guest_nice": 0,
                "usage_idle": 94.72687085592226,
                "usage_iowait": 0.08841174613240087,
                "usage_irq": 0,
                "usage_nice": 0.006315124729609568,
                "usage_softirq": 0.012630249447444813,
                "usage_steal": 0,
                "usage_system": 1.6356173034433854,
                "usage_user": 3.53015472056183
            },
            "name": "cpu",
            "tags": {
                "cpu": "cpu-total",
                "host": "Desktop-STRIX"
            },
            "timestamp": 1787941820
        }
    ]
}
