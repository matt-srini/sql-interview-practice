"""effective_cpu_count() respects the cgroup CPU quota over the host os.cpu_count()."""
import config


def test_uses_cgroup_quota_when_present(monkeypatch):
    monkeypatch.setattr(config, "_cgroup_cpu_quota", lambda: 2)
    assert config.effective_cpu_count() == 2


def test_falls_back_to_os_cpu_count_when_unlimited(monkeypatch):
    monkeypatch.setattr(config, "_cgroup_cpu_quota", lambda: None)
    monkeypatch.setattr(config.os, "cpu_count", lambda: 16)
    assert config.effective_cpu_count() == 16


def test_quota_floor_is_at_least_one(monkeypatch):
    monkeypatch.setattr(config, "_cgroup_cpu_quota", lambda: 1)
    assert config.effective_cpu_count() == 1


def test_cgroup_v2_quota_parsing(monkeypatch):
    from pathlib import Path
    def fake_read_text(self, *a, **k):
        if str(self) == "/sys/fs/cgroup/cpu.max":
            return "200000 100000"   # 200ms / 100ms period == 2 vCPU
        raise FileNotFoundError(str(self))
    monkeypatch.setattr(Path, "read_text", fake_read_text)
    assert config._cgroup_cpu_quota() == 2


def test_cgroup_v2_unlimited_returns_none(monkeypatch):
    from pathlib import Path
    def fake_read_text(self, *a, **k):
        if str(self) == "/sys/fs/cgroup/cpu.max":
            return "max 100000"
        raise FileNotFoundError(str(self))
    monkeypatch.setattr(Path, "read_text", fake_read_text)
    assert config._cgroup_cpu_quota() is None
