import pytest
import yaml

from config import load, require, sha256, sha256_file


def test_load_default_config_exists():
    cfg = load()
    assert isinstance(cfg, dict)
    assert "_sha256" in cfg
    assert len(cfg["_sha256"]) == 64
    assert cfg["dataset"]["scale_exponent"] == 6


def test_sha256_deterministic():
    cfg = load()
    assert sha256(cfg) == cfg["_sha256"]
    cfg2 = load()
    assert cfg["_sha256"] == cfg2["_sha256"]


def test_load_custom_path(tmp_path):
    data = {
        "dataset": {"scale_exponent": 6},
        "audit": {},
        "period": {},
        "proposal": {"path": "PROPOSAL.md"},
    }
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(data))
    cfg = load(p)
    assert cfg["dataset"]["scale_exponent"] == 6


def test_load_non_mapping_raises(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("just a string")
    with pytest.raises(ValueError):
        load(p)


def test_load_missing_section_raises(tmp_path):
    data = {"dataset": {"scale_exponent": 6}, "audit": {}}
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError):
        load(p)


def test_sha256_file(tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("hello")
    h = sha256_file(f)
    import hashlib

    assert h == hashlib.sha256(b"hello").hexdigest()


def test_sha256_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        sha256_file(tmp_path / "no.txt")


def test_require_nested():
    d = {"a": {"b": 1}}
    assert require(d, "a", "b") == 1
    with pytest.raises(ValueError):
        require(d, "a", "c")
