"""
Suite de pruebas unitarias para `ultron.telemetry` (`UltronTelemetry` y dataclasses).
Valida recolección en vivo, ordenamiento de procesos, síntesis de voz multilingüe (ES/EN/FR),
evaluación de umbrales de alerta (WARNING / CRITICAL) y fallback seguro sin `psutil`.
"""

from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import ultron.telemetry as telemetry_mod
from ultron.telemetry import (
    BatteryMetrics,
    CPUMetrics,
    DiskMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessMetric,
    SystemHealthReport,
    UltronTelemetry,
)


class TestUltronTelemetry(unittest.TestCase):
    def setUp(self) -> None:
        self.telemetry = UltronTelemetry(user_name="Sebastián")

    def test_collect_report_returns_valid_metrics(self) -> None:
        report = self.telemetry.collect_report(top_n=5)
        self.assertIsInstance(report, SystemHealthReport)
        self.assertIn(report.status, ("OPTIMAL", "ELEVATED", "CRITICAL"))

        # Validaciones de CPU
        self.assertGreaterEqual(report.cpu.usage_percent, 0.0)
        self.assertLessEqual(report.cpu.usage_percent, 100.0)
        self.assertGreaterEqual(report.cpu.core_count_logical, 1)
        self.assertGreaterEqual(report.cpu.core_count_physical, 1)

        # Validaciones de Memoria
        self.assertGreater(report.memory.total_gb, 0.0)
        self.assertGreaterEqual(report.memory.used_gb, 0.0)
        self.assertGreaterEqual(report.memory.available_gb, 0.0)
        self.assertGreaterEqual(report.memory.percent, 0.0)
        self.assertLessEqual(report.memory.percent, 100.0)

        # Validaciones de Disco
        self.assertGreater(report.disk.total_gb, 0.0)
        self.assertGreaterEqual(report.disk.free_gb, 0.0)
        self.assertGreaterEqual(report.disk.percent, 0.0)
        self.assertLessEqual(report.disk.percent, 100.0)

        # Serialización a diccionario y JSON
        as_dict = report.to_dict()
        self.assertIn("cpu", as_dict)
        self.assertIn("memory", as_dict)
        self.assertIn("disk", as_dict)
        self.assertIn("top_processes", as_dict)
        json_str = json.dumps(as_dict)
        self.assertTrue(len(json_str) > 20)

    def test_get_top_processes_sorted_properly(self) -> None:
        fake_procs = [
            SimpleNamespace(
                info={
                    "pid": 101,
                    "name": "code",
                    "cpu_percent": 12.5,
                    "memory_percent": 18.4,
                    "memory_info": SimpleNamespace(rss=1500 * 1024 * 1024),
                }
            ),
            SimpleNamespace(
                info={
                    "pid": 202,
                    "name": "chrome",
                    "cpu_percent": 35.0,
                    "memory_percent": 28.9,
                    "memory_info": SimpleNamespace(rss=2400 * 1024 * 1024),
                }
            ),
            SimpleNamespace(
                info={
                    "pid": 303,
                    "name": "docker",
                    "cpu_percent": 55.2,
                    "memory_percent": 9.1,
                    "memory_info": SimpleNamespace(rss=750 * 1024 * 1024),
                }
            ),
        ]

        mock_psutil = SimpleNamespace(
            process_iter=lambda attrs=None: fake_procs,
            Error=Exception,
            NoSuchProcess=Exception,
            AccessDenied=Exception,
            ZombieProcess=Exception,
        )

        with patch.object(telemetry_mod, "psutil", mock_psutil):
            by_mem = self.telemetry.get_top_processes(limit=2, sort_by="memory")
            self.assertEqual(len(by_mem), 2)
            self.assertIsInstance(by_mem[0], ProcessMetric)
            self.assertEqual(by_mem[0].name, "chrome")
            self.assertEqual(by_mem[1].name, "code")
            self.assertGreaterEqual(by_mem[0].memory_percent, by_mem[1].memory_percent)

            by_cpu = self.telemetry.get_top_processes(limit=2, sort_by="cpu")
            self.assertEqual(len(by_cpu), 2)
            self.assertEqual(by_cpu[0].name, "docker")
            self.assertEqual(by_cpu[1].name, "chrome")
            self.assertGreaterEqual(by_cpu[0].cpu_percent, by_cpu[1].cpu_percent)

    def test_format_voice_report_es_en_fr(self) -> None:
        mock_report = SystemHealthReport(
            cpu=CPUMetrics(
                usage_percent=42.5,
                core_count_logical=8,
                core_count_physical=4,
                frequency_mhz=3200.0,
                temperature_c=58.0,
            ),
            memory=MemoryMetrics(
                total_gb=16.0,
                used_gb=8.4,
                available_gb=7.6,
                percent=52.5,
                swap_percent=5.0,
            ),
            disk=DiskMetrics(
                total_gb=512.0,
                used_gb=212.0,
                free_gb=300.0,
                percent=41.4,
                mount_point="/",
            ),
            battery=BatteryMetrics(
                present=True,
                percent=88.0,
                power_plugged=True,
                secs_left=None,
            ),
            network=NetworkMetrics(
                bytes_sent_mb=120.5,
                bytes_recv_mb=850.2,
                is_connected=True,
            ),
            status="OPTIMAL",
            alerts=[],
            top_processes=[
                ProcessMetric(
                    pid=444,
                    name="postgres",
                    cpu_percent=14.2,
                    memory_percent=12.5,
                    memory_mb=2048.0,
                )
            ],
            uptime_minutes=240,
            platform_info="Linux",
        )

        es_voice = self.telemetry.format_voice_report(lang="es", report=mock_report)
        self.assertIn("Sebastián", es_voice)
        self.assertIn("42.5%", es_voice)
        self.assertIn("52.5%", es_voice)
        self.assertIn("300.0 GB", es_voice)
        self.assertIn("88%", es_voice)
        self.assertIn("postgres", es_voice)

        en_voice = self.telemetry.format_voice_report(lang="en", report=mock_report)
        self.assertIn("System diagnostics complete", en_voice)
        self.assertIn("42.5%", en_voice)
        self.assertIn("52.5%", en_voice)
        self.assertIn("300.0 GB", en_voice)
        self.assertIn("postgres", en_voice)

        fr_voice = self.telemetry.format_voice_report(lang="fr", report=mock_report)
        self.assertIn("Diagnostic système terminé", fr_voice)
        self.assertIn("postgres", fr_voice)

    def test_threshold_alert_logic_triggers_warning_and_critical(self) -> None:
        # 1. Caso WARNING / ELEVATED (CPU 80%, RAM 78%, Disco 82%, Batería 20% desconectada)
        warn_cpu = CPUMetrics(usage_percent=80.0, core_count_logical=8, core_count_physical=4, temperature_c=78.0)
        warn_mem = MemoryMetrics(total_gb=16.0, used_gb=12.5, available_gb=3.5, percent=78.0)
        warn_disk = DiskMetrics(total_gb=500.0, used_gb=410.0, free_gb=90.0, percent=82.0)
        warn_bat = BatteryMetrics(present=True, percent=20.0, power_plugged=False, secs_left=1800)

        status_warn, alerts_warn = self.telemetry.evaluate_health(
            warn_cpu, warn_mem, warn_disk, warn_bat
        )
        self.assertEqual(status_warn, "ELEVATED")
        self.assertTrue(any("WARNING" in a for a in alerts_warn))
        self.assertEqual(len(alerts_warn), 5)

        # 2. Caso CRITICAL (CPU 95%, RAM 91%, Disco 94%, Batería 10% desconectada, Temp 90°C)
        crit_cpu = CPUMetrics(usage_percent=95.0, core_count_logical=8, core_count_physical=4, temperature_c=90.0)
        crit_mem = MemoryMetrics(total_gb=16.0, used_gb=14.6, available_gb=1.4, percent=91.0)
        crit_disk = DiskMetrics(total_gb=500.0, used_gb=470.0, free_gb=30.0, percent=94.0)
        crit_bat = BatteryMetrics(present=True, percent=10.0, power_plugged=False, secs_left=600)

        status_crit, alerts_crit = self.telemetry.evaluate_health(
            crit_cpu, crit_mem, crit_disk, crit_bat
        )
        self.assertEqual(status_crit, "CRITICAL")
        self.assertTrue(all("CRITICAL" in a for a in alerts_crit))
        self.assertEqual(len(alerts_crit), 5)

    def test_fallback_without_psutil_never_crashes(self) -> None:
        with patch.object(telemetry_mod, "psutil", None):
            report = self.telemetry.collect_report(top_n=3)
            self.assertIsInstance(report, SystemHealthReport)
            self.assertGreater(report.memory.total_gb, 0.0)
            self.assertGreater(report.disk.total_gb, 0.0)
            self.assertGreaterEqual(len(report.top_processes), 1)
            voice_procs = self.telemetry.format_top_processes_voice(limit=2, sort_by="memory", lang="es")
            self.assertIn("Sebastián", voice_procs)


if __name__ == "__main__":
    unittest.main()
