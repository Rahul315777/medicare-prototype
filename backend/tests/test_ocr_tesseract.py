"""Regression test for the cross-platform Tesseract path fix.

Previously `extract_ocr_text` hard-coded a Windows-only path
(`C:\\Program Files\\Tesseract-OCR\\tesseract.exe`), which broke OCR on
Linux/WSL/Docker. `_configure_tesseract_cmd` now resolves the binary via
(1) an explicit TESSERACT_CMD setting, (2) PATH, (3) the Windows default
as a last resort on Windows only.
"""

from types import SimpleNamespace

import app.ai.services as services


def _reset_cache():
    services._tesseract_cmd_configured = False


def test_uses_path_resolution_when_tesseract_on_path(monkeypatch):
    _reset_cache()
    monkeypatch.setattr(services.settings, "TESSERACT_CMD", None)
    monkeypatch.setattr(services.shutil, "which", lambda name: "/usr/bin/tesseract", raising=False)

    fake_pytesseract = SimpleNamespace(pytesseract=SimpleNamespace(tesseract_cmd="tesseract"))
    services._configure_tesseract_cmd(fake_pytesseract)

    assert fake_pytesseract.pytesseract.tesseract_cmd == "/usr/bin/tesseract"


def test_explicit_setting_takes_priority(monkeypatch):
    _reset_cache()
    monkeypatch.setattr(services.settings, "TESSERACT_CMD", "/opt/custom/tesseract")

    fake_pytesseract = SimpleNamespace(pytesseract=SimpleNamespace(tesseract_cmd="tesseract"))
    services._configure_tesseract_cmd(fake_pytesseract)

    assert fake_pytesseract.pytesseract.tesseract_cmd == "/opt/custom/tesseract"


def test_no_hardcoded_windows_path_on_linux_when_not_found(monkeypatch):
    """On non-Windows with tesseract missing from PATH, we must NOT silently
    fall back to a Windows path — leave pytesseract's default so the existing
    FileNotFoundError handling in extract_ocr_text can report it clearly."""
    _reset_cache()
    monkeypatch.setattr(services.settings, "TESSERACT_CMD", None)
    monkeypatch.setattr(services.shutil, "which", lambda name: None, raising=False)
    monkeypatch.setattr(services.platform, "system", lambda: "Linux", raising=False)

    fake_pytesseract = SimpleNamespace(pytesseract=SimpleNamespace(tesseract_cmd="tesseract"))
    services._configure_tesseract_cmd(fake_pytesseract)

    assert fake_pytesseract.pytesseract.tesseract_cmd == "tesseract"
