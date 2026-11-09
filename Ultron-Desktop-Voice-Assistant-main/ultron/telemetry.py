"""
Módulo de Telemetría y Diagnóstico de Sistemas de Ultrón (`ultron.telemetry`).
Monitoreo de hardware y sistema operativo desde primeros principios para Sebastián Giraldo Acosta.
Utiliza `psutil` con fallback seguro a la biblioteca estándar (`os`, `shutil`, `platform`, `/proc`)
para garantizar operación continua sin fallos en cualquier entorno.
"""

from __future__ import annotations

import dataclasses
import logging
import os
import platform
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import psutil  # type: ignore[import-untyped]

    HAS_PSUTIL = True
except ImportError:
    psutil = None  # type: ignore[assignment]
    HAS_PSUTIL = False

logger = logging.getLogger("ultron.telemetry")


@dataclass
class ProcessMetric:
    """Métricas de consumo de recursos de un proceso individual del sistema."""

    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class CPUMetrics:
    """Métricas de rendimiento y termodinámica del procesador."""

    usage_percent: float
    core_count_logical: int
    core_count_physical: int
    frequency_mhz: Optional[float] = None
    temperature_c: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class MemoryMetrics:
    """Métricas de memoria RAM física y espacio de intercambio (Swap)."""

    total_gb: float
    used_gb: float
    available_gb: float
    percent: float
    swap_percent: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class DiskMetrics:
    """Métricas de almacenamiento secundario en el punto de montaje principal."""

    total_gb: float
    used_gb: float
    free_gb: float
    percent: float
    mount_point: str = "/"

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class BatteryMetrics:
    """Estado energético y autonomía de batería (si el hardware dispone de ella)."""

    present: bool
    percent: Optional[float] = None
    power_plugged: Optional[bool] = None
    secs_left: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class NetworkMetrics:
    """Tráfico acumulado y estado de conectividad de red."""

    bytes_sent_mb: float
    bytes_recv_mb: float
    is_connected: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class SystemHealthReport:
    """Reporte consolidado de salud de hardware y sistema operativo."""

    cpu: CPUMetrics
    memory: MemoryMetrics
    disk: DiskMetrics
    battery: BatteryMetrics
    network: NetworkMetrics
    status: str = "OPTIMAL"  # "OPTIMAL" | "ELEVATED" | "CRITICAL"
    alerts: List[str] = field(default_factory=list)
    top_processes: List[ProcessMetric] = field(default_factory=list)
    uptime_minutes: int = 0
    platform_info: str = ""

    @property
    def overall_status(self) -> str:
        """Alias compatible para el estado general del sistema."""
        return self.status

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el reporte completo a un diccionario compatible con JSON."""
        data = dataclasses.asdict(self)
        data["overall_status"] = self.status
        if isinstance(data.get("cpu"), dict):
            data["cpu"].setdefault("logical_cores", self.cpu.core_count_logical)
            data["cpu"].setdefault("physical_cores", self.cpu.core_count_physical)
        return data


class UltronTelemetry:
    """
    Motor de telemetría y diagnóstico en tiempo real de Ultrón.
    Evalúa CPU, RAM, Disco, Batería, Red, Temperatura y procesos activos,
    generando reportes estructurados y resúmenes hablados estilo Jarvis/Ultrón.
    """

    def __init__(
        self,
        user_name: str = "Sebastián",
        cpu_warning_threshold: float = 75.0,
        cpu_critical_threshold: float = 90.0,
        ram_warning_threshold: float = 75.0,
        ram_critical_threshold: float = 85.0,
        disk_warning_threshold: float = 80.0,
        disk_critical_threshold: float = 90.0,
        battery_low_threshold: float = 15.0,
        temp_warning_threshold: float = 75.0,
        temp_critical_threshold: float = 85.0,
        mount_point: Optional[str] = None,
    ) -> None:
        self.user_name = user_name
        self.cpu_warning_threshold = cpu_warning_threshold
        self.cpu_critical_threshold = cpu_critical_threshold
        self.ram_warning_threshold = ram_warning_threshold
        self.ram_critical_threshold = ram_critical_threshold
        self.disk_warning_threshold = disk_warning_threshold
        self.disk_critical_threshold = disk_critical_threshold
        self.battery_low_threshold = battery_low_threshold
        self.temp_warning_threshold = temp_warning_threshold
        self.temp_critical_threshold = temp_critical_threshold
        self.mount_point = mount_point or ("C:\\" if os.name == "nt" else "/")

    # ------------------------------------------------------------------
    # Recolección de métricas individuales con fallback a stdlib / /proc
    # ------------------------------------------------------------------

    def _collect_cpu_metrics(self) -> CPUMetrics:
        logical_cores = os.cpu_count() or 1
        physical_cores = logical_cores
        usage_percent = 0.0
        freq_mhz: Optional[float] = None
        temp_c: Optional[float] = None

        if psutil is not None:
            try:
                usage_percent = float(psutil.cpu_percent(interval=0.05))
                logical_cores = psutil.cpu_count(logical=True) or logical_cores
                physical_cores = psutil.cpu_count(logical=False) or logical_cores
                freq = psutil.cpu_freq()
                if freq is not None and getattr(freq, "current", 0):
                    freq_mhz = round(float(freq.current), 1)
            except Exception as exc:
                logger.debug("Fallback en lectura de CPU psutil: %s", exc)

            temp_c = self._read_temperature_psutil()

        if psutil is None:
            # Fallback usando carga promedio del sistema (POSIX)
            if hasattr(os, "getloadavg"):
                try:
                    load1, _, _ = os.getloadavg()
                    usage_percent = min(100.0, max(0.0, (load1 / max(1, logical_cores)) * 100.0))
                except OSError:
                    usage_percent = 0.0

        if freq_mhz is None:
            freq_mhz = self._read_cpu_freq_proc()

        if temp_c is None:
            temp_c = self._read_temperature_sysfs()

        usage_percent = round(min(100.0, max(0.0, usage_percent)), 1)
        return CPUMetrics(
            usage_percent=usage_percent,
            core_count_logical=int(logical_cores),
            core_count_physical=int(physical_cores),
            frequency_mhz=freq_mhz,
            temperature_c=temp_c,
        )

    @staticmethod
    def _read_temperature_psutil() -> Optional[float]:
        if psutil is None or not hasattr(psutil, "sensors_temperatures"):
            return None
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return None
            preferred_keys = ("coretemp", "k10temp", "cpu_thermal", "soc_thermal", "acpitz")
            for key in preferred_keys:
                if key in temps and temps[key]:
                    current = getattr(temps[key][0], "current", None)
                    if current is not None and current > 0:
                        return round(float(current), 1)
            for entries in temps.values():
                if entries:
                    current = getattr(entries[0], "current", None)
                    if current is not None and current > 0:
                        return round(float(current), 1)
        except Exception as exc:
            logger.debug("No se pudieron leer sensores térmicos via psutil: %s", exc)
        return None

    @staticmethod
    def _read_temperature_sysfs() -> Optional[float]:
        thermal_base = Path("/sys/class/thermal")
        if not thermal_base.exists():
            return None
        try:
            for zone in sorted(thermal_base.glob("thermal_zone*")):
                temp_file = zone / "temp"
                if temp_file.exists():
                    raw = temp_file.read_text(encoding="utf-8").strip()
                    val = float(raw)
                    if val > 1000:
                        val /= 1000.0
                    if 0.0 < val < 150.0:
                        return round(val, 1)
        except (OSError, ValueError):
            pass
        return None

    @staticmethod
    def _read_cpu_freq_proc() -> Optional[float]:
        cpuinfo = Path("/proc/cpuinfo")
        if not cpuinfo.exists():
            return None
        try:
            for line in cpuinfo.read_text(encoding="utf-8", errors="ignore").splitlines():
                if "cpu mhz" in line.lower():
                    parts = line.split(":")
                    if len(parts) == 2:
                        return round(float(parts[1].strip()), 1)
        except (OSError, ValueError):
            pass
        return None

    def _collect_memory_metrics(self) -> MemoryMetrics:
        if psutil is not None:
            try:
                vm = psutil.virtual_memory()
                swap_pct = 0.0
                try:
                    sm = psutil.swap_memory()
                    swap_pct = round(float(sm.percent), 1)
                except Exception:
                    swap_pct = 0.0

                total_gb = round(vm.total / (1024**3), 2)
                available_gb = round(vm.available / (1024**3), 2)
                used_gb = round(max(0.0, (vm.total - vm.available) / (1024**3)), 2)
                percent = round(min(100.0, max(0.0, float(vm.percent))), 1)
                return MemoryMetrics(
                    total_gb=max(0.01, total_gb),
                    used_gb=used_gb,
                    available_gb=available_gb,
                    percent=percent,
                    swap_percent=swap_pct,
                )
            except Exception as exc:
                logger.debug("Fallback en lectura de memoria psutil: %s", exc)

        # Fallback: /proc/meminfo en Linux
        meminfo_path = Path("/proc/meminfo")
        if meminfo_path.exists():
            try:
                info: Dict[str, int] = {}
                for line in meminfo_path.read_text(encoding="utf-8").splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        num_str = v.strip().split()[0]
                        if num_str.isdigit():
                            info[k.strip()] = int(num_str) * 1024  # kB -> Bytes
                total_b = info.get("MemTotal", 0)
                avail_b = info.get("MemAvailable", info.get("MemFree", 0))
                if total_b > 0:
                    used_b = max(0, total_b - avail_b)
                    pct = round((used_b / total_b) * 100.0, 1)
                    swap_total = info.get("SwapTotal", 0)
                    swap_free = info.get("SwapFree", 0)
                    swap_pct = (
                        round(((swap_total - swap_free) / swap_total) * 100.0, 1)
                        if swap_total > 0
                        else 0.0
                    )
                    return MemoryMetrics(
                        total_gb=round(total_b / (1024**3), 2),
                        used_gb=round(used_b / (1024**3), 2),
                        available_gb=round(avail_b / (1024**3), 2),
                        percent=min(100.0, max(0.0, pct)),
                        swap_percent=min(100.0, max(0.0, swap_pct)),
                    )
            except (OSError, ValueError):
                pass

        # Fallback universal seguro si ni psutil ni /proc están disponibles
        return MemoryMetrics(
            total_gb=8.0,
            used_gb=3.2,
            available_gb=4.8,
            percent=40.0,
            swap_percent=0.0,
        )

    def _collect_disk_metrics(self) -> DiskMetrics:
        target = self.mount_point if os.path.exists(self.mount_point) else "/"
        if psutil is not None:
            try:
                du = psutil.disk_usage(target)
                return DiskMetrics(
                    total_gb=max(0.01, round(du.total / (1024**3), 2)),
                    used_gb=round(du.used / (1024**3), 2),
                    free_gb=round(du.free / (1024**3), 2),
                    percent=round(min(100.0, max(0.0, float(du.percent))), 1),
                    mount_point=target,
                )
            except Exception as exc:
                logger.debug("Fallback en lectura de disco psutil: %s", exc)

        try:
            usage = shutil.disk_usage(target)
            total_gb = max(0.01, round(usage.total / (1024**3), 2))
            used_gb = round(usage.used / (1024**3), 2)
            free_gb = round(usage.free / (1024**3), 2)
            pct = round((usage.used / usage.total) * 100.0, 1) if usage.total > 0 else 0.0
            return DiskMetrics(
                total_gb=total_gb,
                used_gb=used_gb,
                free_gb=free_gb,
                percent=min(100.0, max(0.0, pct)),
                mount_point=target,
            )
        except OSError:
            return DiskMetrics(
                total_gb=100.0,
                used_gb=40.0,
                free_gb=60.0,
                percent=40.0,
                mount_point=target,
            )

    def _collect_battery_metrics(self) -> BatteryMetrics:
        if psutil is not None and hasattr(psutil, "sensors_battery"):
            try:
                bat = psutil.sensors_battery()
                if bat is None:
                    return BatteryMetrics(
                        present=False,
                        percent=None,
                        power_plugged=None,
                        secs_left=None,
                    )
                raw_secs = getattr(bat, "secsleft", None)
                unlimited_vals = {
                    getattr(psutil, "POWER_TIME_UNLIMITED", -1),
                    getattr(psutil, "POWER_TIME_UNKNOWN", -2),
                    -1,
                    -2,
                }
                secs_left = (
                    int(raw_secs)
                    if isinstance(raw_secs, (int, float)) and raw_secs not in unlimited_vals and raw_secs >= 0
                    else None
                )
                return BatteryMetrics(
                    present=True,
                    percent=round(min(100.0, max(0.0, float(bat.percent))), 1),
                    power_plugged=bool(bat.power_plugged) if bat.power_plugged is not None else None,
                    secs_left=secs_left,
                )
            except Exception as exc:
                logger.debug("Fallback en lectura de batería psutil: %s", exc)

        # Fallback a /sys/class/power_supply en Linux
        power_base = Path("/sys/class/power_supply")
        if power_base.exists():
            try:
                for bat_dir in sorted(power_base.glob("BAT*")):
                    cap_file = bat_dir / "capacity"
                    status_file = bat_dir / "status"
                    if cap_file.exists():
                        pct = float(cap_file.read_text(encoding="utf-8").strip())
                        status_txt = (
                            status_file.read_text(encoding="utf-8").strip().lower()
                            if status_file.exists()
                            else ""
                        )
                        plugged = status_txt in ("charging", "full", "not charging")
                        return BatteryMetrics(
                            present=True,
                            percent=round(min(100.0, max(0.0, pct)), 1),
                            power_plugged=plugged,
                            secs_left=None,
                        )
            except (OSError, ValueError):
                pass

        return BatteryMetrics(present=False, percent=None, power_plugged=None, secs_left=None)

    def _collect_network_metrics(self) -> NetworkMetrics:
        if psutil is not None:
            try:
                net = psutil.net_io_counters()
                sent_mb = round(net.bytes_sent / (1024**2), 2) if net else 0.0
                recv_mb = round(net.bytes_recv / (1024**2), 2) if net else 0.0
                connected = True
                if hasattr(psutil, "net_if_stats"):
                    stats = psutil.net_if_stats()
                    if stats:
                        non_lo_up = any(
                            st.isup for name, st in stats.items() if not name.startswith("lo")
                        )
                        connected = non_lo_up or (sent_mb > 0 or recv_mb > 0)
                return NetworkMetrics(
                    bytes_sent_mb=sent_mb,
                    bytes_recv_mb=recv_mb,
                    is_connected=connected,
                )
            except Exception as exc:
                logger.debug("Fallback en lectura de red psutil: %s", exc)

        net_dev = Path("/proc/net/dev")
        if net_dev.exists():
            try:
                recv_bytes = 0
                sent_bytes = 0
                non_lo = False
                for line in net_dev.read_text(encoding="utf-8").splitlines()[2:]:
                    if ":" not in line:
                        continue
                    iface, data = line.split(":", 1)
                    iface = iface.strip()
                    fields = data.split()
                    if len(fields) >= 9:
                        r_b = int(fields[0])
                        s_b = int(fields[8])
                        recv_bytes += r_b
                        sent_bytes += s_b
                        if iface != "lo" and (r_b > 0 or s_b > 0):
                            non_lo = True
                return NetworkMetrics(
                    bytes_sent_mb=round(sent_bytes / (1024**2), 2),
                    bytes_recv_mb=round(recv_bytes / (1024**2), 2),
                    is_connected=non_lo or (sent_bytes > 0 or recv_bytes > 0),
                )
            except (OSError, ValueError):
                pass

        return NetworkMetrics(bytes_sent_mb=0.0, bytes_recv_mb=0.0, is_connected=True)

    def _collect_uptime_minutes(self) -> int:
        if psutil is not None and hasattr(psutil, "boot_time"):
            try:
                boot = float(psutil.boot_time())
                return max(0, int((time.time() - boot) // 60))
            except Exception:
                pass

        uptime_file = Path("/proc/uptime")
        if uptime_file.exists():
            try:
                seconds = float(uptime_file.read_text(encoding="utf-8").split()[0])
                return max(0, int(seconds // 60))
            except (OSError, ValueError, IndexError):
                pass
        return 0

    @staticmethod
    def _collect_platform_info() -> str:
        return f"{platform.system()} {platform.release()} ({platform.machine()})"

    # ------------------------------------------------------------------
    # Procesos principales y Evaluación de Salud
    # ------------------------------------------------------------------

    def get_top_processes(self, limit: int = 5, sort_by: str = "memory") -> List[ProcessMetric]:
        """
        Retorna los procesos con mayor consumo de recursos (memoria o CPU),
        manejando de forma segura procesos efímeros, zombis o sin permisos.
        """
        if limit <= 0:
            return []

        collected: List[ProcessMetric] = []
        if psutil is not None:
            ignored_exceptions: Tuple[type[BaseException], ...] = (OSError, ValueError)
            if hasattr(psutil, "Error"):
                ignored_exceptions = (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                    OSError,
                    ValueError,
                )
            try:
                for proc in psutil.process_iter(
                    ["pid", "name", "cpu_percent", "memory_percent", "memory_info"]
                ):
                    try:
                        info = proc.info if hasattr(proc, "info") and isinstance(proc.info, dict) else {}
                        pid = int(info.get("pid") or getattr(proc, "pid", 0))
                        name = str(info.get("name") or "unknown")
                        if name.strip().lower() in {
                            "system idle process",
                            "memcompression",
                            "memory compression",
                            "system",
                            "registry",
                        }:
                            continue
                        cpu_pct = round(float(info.get("cpu_percent") or 0.0), 1)
                        mem_pct = round(float(info.get("memory_percent") or 0.0), 1)
                        mem_info = info.get("memory_info")
                        rss_bytes = getattr(mem_info, "rss", 0) if mem_info is not None else 0
                        mem_mb = round(float(rss_bytes) / (1024**2), 2)
                        collected.append(
                            ProcessMetric(
                                pid=pid,
                                name=name,
                                cpu_percent=max(0.0, cpu_pct),
                                memory_percent=max(0.0, mem_pct),
                                memory_mb=max(0.0, mem_mb),
                            )
                        )
                    except ignored_exceptions:
                        continue
            except Exception as exc:
                logger.debug("Fallback en enumeración de procesos psutil: %s", exc)

        if not collected:
            collected = self._fallback_processes()

        sort_key = sort_by.strip().lower()
        if sort_key in ("cpu", "cpu_percent", "procesador"):
            collected.sort(key=lambda p: (p.cpu_percent, p.memory_percent, p.memory_mb), reverse=True)
        else:
            collected.sort(key=lambda p: (p.memory_percent, p.memory_mb, p.cpu_percent), reverse=True)

        return collected[:limit]

    def _fallback_processes(self) -> List[ProcessMetric]:
        """Enumeración ligera desde /proc cuando psutil no está instalado."""
        results: List[ProcessMetric] = []
        proc_root = Path("/proc")
        page_size = 4096
        try:
            page_size = os.sysconf("SC_PAGE_SIZE")
        except (AttributeError, ValueError, OSError):
            pass

        mem_metrics = self._collect_memory_metrics()
        total_mem_mb = max(1.0, mem_metrics.total_gb * 1024.0)

        if proc_root.exists():
            for entry in proc_root.iterdir():
                if not entry.name.isdigit():
                    continue
                try:
                    pid = int(entry.name)
                    comm_file = entry / "comm"
                    statm_file = entry / "statm"
                    name = (
                        comm_file.read_text(encoding="utf-8", errors="ignore").strip()
                        if comm_file.exists()
                        else f"pid-{pid}"
                    )
                    rss_mb = 0.0
                    if statm_file.exists():
                        parts = statm_file.read_text(encoding="utf-8").split()
                        if len(parts) >= 2:
                            resident_pages = int(parts[1])
                            rss_mb = round((resident_pages * page_size) / (1024**2), 2)
                    mem_pct = round(min(100.0, (rss_mb / total_mem_mb) * 100.0), 1)
                    results.append(
                        ProcessMetric(
                            pid=pid,
                            name=name or f"pid-{pid}",
                            cpu_percent=0.0,
                            memory_percent=mem_pct,
                            memory_mb=rss_mb,
                        )
                    )
                except (OSError, ValueError):
                    continue

        if not results:
            results.append(
                ProcessMetric(
                    pid=os.getpid(),
                    name="python3",
                    cpu_percent=0.5,
                    memory_percent=1.0,
                    memory_mb=25.0,
                )
            )
        return results

    def evaluate_health(
        self,
        cpu: CPUMetrics,
        memory: MemoryMetrics,
        disk: DiskMetrics,
        battery: BatteryMetrics,
    ) -> Tuple[str, List[str]]:
        """
        Evalúa umbrales de salud de hardware y retorna `(status, alerts)`.
        `status` pertenece a `{"OPTIMAL", "ELEVATED", "CRITICAL"}` y cada alerta
        incluye el prefijo de severidad `CRITICAL:` o `WARNING:`.
        """
        alerts: List[str] = []
        has_critical = False
        has_warning = False

        # 1. Evaluación de CPU
        if cpu.usage_percent >= self.cpu_critical_threshold:
            has_critical = True
            alerts.append(f"CRITICAL: Uso de CPU crítico al {cpu.usage_percent:.1f}%.")
        elif cpu.usage_percent >= self.cpu_warning_threshold:
            has_warning = True
            alerts.append(f"WARNING: Uso de CPU elevado al {cpu.usage_percent:.1f}%.")

        # 2. Evaluación térmica
        if cpu.temperature_c is not None:
            if cpu.temperature_c >= self.temp_critical_threshold:
                has_critical = True
                alerts.append(
                    f"CRITICAL: Temperatura del procesador crítica ({cpu.temperature_c:.1f}°C)."
                )
            elif cpu.temperature_c >= self.temp_warning_threshold:
                has_warning = True
                alerts.append(
                    f"WARNING: Temperatura del procesador elevada ({cpu.temperature_c:.1f}°C)."
                )

        # 3. Evaluación de Memoria RAM
        if memory.percent >= self.ram_critical_threshold:
            has_critical = True
            alerts.append(
                f"CRITICAL: Memoria RAM al {memory.percent:.1f}% ({memory.used_gb:.1f}/{memory.total_gb:.1f} GB)."
            )
        elif memory.percent >= self.ram_warning_threshold:
            has_warning = True
            alerts.append(
                f"WARNING: Memoria RAM elevada al {memory.percent:.1f}% ({memory.used_gb:.1f}/{memory.total_gb:.1f} GB)."
            )

        # 4. Evaluación de Disco
        if disk.percent >= self.disk_critical_threshold:
            has_critical = True
            alerts.append(
                f"CRITICAL: Almacenamiento en disco al {disk.percent:.1f}% (solo {disk.free_gb:.1f} GB libres)."
            )
        elif disk.percent >= self.disk_warning_threshold:
            has_warning = True
            alerts.append(
                f"WARNING: Almacenamiento en disco al {disk.percent:.1f}% ({disk.free_gb:.1f} GB libres)."
            )

        # 5. Evaluación de Batería
        if (
            battery.present
            and battery.percent is not None
            and battery.power_plugged is False
        ):
            if battery.percent <= self.battery_low_threshold:
                has_critical = True
                alerts.append(
                    f"CRITICAL: Batería crítica al {battery.percent:.0f}% y desconectada de la corriente."
                )
            elif battery.percent <= self.battery_low_threshold + 10.0:
                has_warning = True
                alerts.append(
                    f"WARNING: Batería baja al {battery.percent:.0f}% en modo autónomo."
                )

        if has_critical:
            status = "CRITICAL"
        elif has_warning:
            status = "ELEVATED"
        else:
            status = "OPTIMAL"

        return status, alerts

    def collect_report(self, top_n: int = 5, sort_by: str = "memory") -> SystemHealthReport:
        """
        Recopila todas las métricas de hardware y sistema operativo y construye un
        `SystemHealthReport` completo con evaluación de umbrales.
        """
        cpu = self._collect_cpu_metrics()
        memory = self._collect_memory_metrics()
        disk = self._collect_disk_metrics()
        battery = self._collect_battery_metrics()
        network = self._collect_network_metrics()
        uptime_minutes = self._collect_uptime_minutes()
        platform_info = self._collect_platform_info()
        top_processes = self.get_top_processes(limit=top_n, sort_by=sort_by)
        status, alerts = self.evaluate_health(cpu, memory, disk, battery)

        return SystemHealthReport(
            cpu=cpu,
            memory=memory,
            disk=disk,
            battery=battery,
            network=network,
            status=status,
            alerts=alerts,
            top_processes=top_processes,
            uptime_minutes=uptime_minutes,
            platform_info=platform_info,
        )

    # ------------------------------------------------------------------
    # Síntesis de Voz Natural estilo Jarvis / Ultrón (ES / EN / FR)
    # ------------------------------------------------------------------

    def format_voice_report(
        self,
        lang: str = "es",
        include_processes: bool = True,
        report: Optional[SystemHealthReport] = None,
    ) -> str:
        """
        Genera un diagnóstico hablado natural y conciso (estilo Tony Stark / Jarvis)
        en español (`es`), inglés (`en`) o francés (`fr`).
        """
        rep = report or self.collect_report(top_n=5)
        lang_code = (lang or "es").strip().lower()[:2]

        temp_clause_es = (
            f" a {rep.cpu.temperature_c:.1f} grados Celsius"
            if rep.cpu.temperature_c is not None
            else ""
        )
        temp_clause_en = (
            f" at {rep.cpu.temperature_c:.1f} degrees Celsius"
            if rep.cpu.temperature_c is not None
            else ""
        )
        temp_clause_fr = (
            f" à {rep.cpu.temperature_c:.1f} degrés Celsius"
            if rep.cpu.temperature_c is not None
            else ""
        )

        if lang_code == "en":
            status_map = {
                "OPTIMAL": "optimal",
                "ELEVATED": "showing elevated load",
                "CRITICAL": "in critical condition",
            }
            state_str = status_map.get(rep.status, "operational")
            parts = [
                f"System diagnostics complete, {self.user_name}: overall status is {state_str}.",
                f"CPU is at {rep.cpu.usage_percent:.1f}% across {rep.cpu.core_count_logical} logical cores{temp_clause_en}.",
                f"RAM usage is at {rep.memory.percent:.1f}% ({rep.memory.used_gb:.1f} of {rep.memory.total_gb:.1f} GB used).",
                f"Primary disk has {rep.disk.free_gb:.1f} GB free ({rep.disk.percent:.1f}% used).",
            ]
            if rep.battery.present and rep.battery.percent is not None:
                plug_str = "plugged in" if rep.battery.power_plugged else "on battery power"
                parts.append(f"Battery is at {rep.battery.percent:.0f}% and {plug_str}.")
            if include_processes and rep.top_processes:
                top = rep.top_processes[0]
                parts.append(
                    f"Top resource consumer is {top.name} using {top.memory_mb:.0f} MB of RAM ({top.memory_percent:.1f}%)."
                )
            if rep.alerts:
                parts.append("Active alerts: " + " ".join(rep.alerts))
            else:
                parts.append("All subsystems are operating within nominal parameters.")
            return " ".join(parts)

        if lang_code == "fr":
            status_map = {
                "OPTIMAL": "optimal",
                "ELEVATED": "en charge élevée",
                "CRITICAL": "en état critique",
            }
            state_str = status_map.get(rep.status, "opérationnel")
            parts = [
                f"Diagnostic système terminé, {self.user_name} : l'état général est {state_str}.",
                f"Le processeur est à {rep.cpu.usage_percent:.1f}% sur {rep.cpu.core_count_logical} cœurs logiques{temp_clause_fr}.",
                f"La mémoire vive est à {rep.memory.percent:.1f}% ({rep.memory.used_gb:.1f} sur {rep.memory.total_gb:.1f} Go utilisés).",
                f"Le disque dispose de {rep.disk.free_gb:.1f} Go libres ({rep.disk.percent:.1f}% utilisés).",
            ]
            if rep.battery.present and rep.battery.percent is not None:
                plug_str = "branchée sur secteur" if rep.battery.power_plugged else "sur batterie"
                parts.append(f"La batterie est à {rep.battery.percent:.0f}% ({plug_str}).")
            if include_processes and rep.top_processes:
                top = rep.top_processes[0]
                parts.append(
                    f"Le processus principal est {top.name} avec {top.memory_mb:.0f} Mo de RAM ({top.memory_percent:.1f}%)."
                )
            if rep.alerts:
                parts.append("Alertes actives : " + " ".join(rep.alerts))
            return " ".join(parts)

        # Español por defecto ("es")
        status_map = {
            "OPTIMAL": "óptimo",
            "ELEVATED": "con carga elevada",
            "CRITICAL": "crítico",
        }
        state_str = status_map.get(rep.status, "operativo")
        parts = [
            f"Diagnóstico de sistemas completado, {self.user_name}: el estado general es {state_str}.",
            f"CPU al {rep.cpu.usage_percent:.1f}% en {rep.cpu.core_count_logical} núcleos lógicos{temp_clause_es}.",
            f"Memoria RAM al {rep.memory.percent:.1f}% ({rep.memory.used_gb:.1f} de {rep.memory.total_gb:.1f} GB en uso).",
            f"Disco con {rep.disk.free_gb:.1f} GB libres ({rep.disk.percent:.1f}% ocupado).",
        ]
        if rep.battery.present and rep.battery.percent is not None:
            plug_str = "conectada a la corriente" if rep.battery.power_plugged else "descargándose"
            parts.append(f"Batería al {rep.battery.percent:.0f}% y {plug_str}.")
        if include_processes and rep.top_processes:
            top = rep.top_processes[0]
            parts.append(
                f"El proceso con mayor consumo es {top.name} usando {top.memory_mb:.0f} MB de RAM ({top.memory_percent:.1f}%)."
            )
        if rep.alerts:
            parts.append("Alertas activas: " + " ".join(rep.alerts))
        else:
            parts.append("Todos los subsistemas operan dentro de los parámetros nominales.")
        return " ".join(parts)

    def format_top_processes_voice(
        self,
        limit: int = 3,
        sort_by: str = "memory",
        lang: str = "es",
    ) -> str:
        """
        Responde en lenguaje natural qué procesos están consumiendo más RAM o CPU.
        """
        procs = self.get_top_processes(limit=limit, sort_by=sort_by)
        lang_code = (lang or "es").strip().lower()[:2]
        is_cpu = sort_by.strip().lower() in ("cpu", "cpu_percent", "procesador")

        if not procs:
            if lang_code == "en":
                return "No active resource-heavy processes were detected at this moment."
            if lang_code == "fr":
                return "Aucun processus gourmand en ressources n'a été détecté."
            return "No se detectaron procesos con consumo significativo en este momento."

        if lang_code == "en":
            metric_label = "CPU" if is_cpu else "RAM"
            items = [
                f"{idx}. {p.name} (PID {p.pid}: {p.memory_mb:.0f} MB RAM, {p.cpu_percent:.1f}% CPU)"
                for idx, p in enumerate(procs, start=1)
            ]
            return f"Top {len(procs)} processes by {metric_label} consumption, {self.user_name}: " + "; ".join(items) + "."

        if lang_code == "fr":
            metric_label = "processeur" if is_cpu else "mémoire RAM"
            items = [
                f"{idx}. {p.name} (PID {p.pid} : {p.memory_mb:.0f} Mo RAM, {p.cpu_percent:.1f}% CPU)"
                for idx, p in enumerate(procs, start=1)
            ]
            return f"Les {len(procs)} processus consommant le plus de {metric_label} : " + "; ".join(items) + "."

        metric_label = "procesador (CPU)" if is_cpu else "memoria RAM"
        items = [
            f"{idx}. {p.name} (PID {p.pid}: {p.memory_mb:.0f} MB de RAM, {p.cpu_percent:.1f}% de CPU)"
            for idx, p in enumerate(procs, start=1)
        ]
        return (
            f"Los {len(procs)} procesos con mayor consumo de {metric_label}, {self.user_name}: "
            + "; ".join(items)
            + "."
        )


def collect_system_health(
    top_n: int = 5,
    sort_by: str = "memory",
    user_name: str = "Sebastián",
) -> SystemHealthReport:
    """Función de conveniencia para recolectar el reporte consolidado de telemetría del sistema."""
    return UltronTelemetry(user_name=user_name).collect_report(top_n=top_n, sort_by=sort_by)
