import os
import shutil
import subprocess
import uuid
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string


def _candidatos_chrome():
    env_path = str(os.getenv("DASHBOARD_PDF_BROWSER") or "").strip()
    if env_path:
        yield Path(env_path)

    for caminho in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ):
        yield Path(caminho)


def _resolver_executavel_browser():
    for candidato in _candidatos_chrome():
        if candidato.exists() and candidato.is_file():
            return str(candidato)
    raise RuntimeError(
        "Nao foi encontrado navegador para gerar PDF. "
        "Configure DASHBOARD_PDF_BROWSER com o caminho do executavel."
    )


def render_template_to_pdf_bytes(template_name, context, request=None):
    html = render_to_string(template_name, context=context, request=request)
    browser = _resolver_executavel_browser()

    base_tmp = Path(getattr(settings, "BASE_DIR", Path.cwd())) / "tmp_pdf_renderer"
    base_tmp.mkdir(parents=True, exist_ok=True)
    job_dir = base_tmp / f"job_{uuid.uuid4().hex}"
    job_dir.mkdir(parents=True, exist_ok=True)

    html_path = job_dir / "dashboard.html"
    pdf_path = job_dir / "dashboard.pdf"
    profile_path = job_dir / "profile"
    profile_path.mkdir(parents=True, exist_ok=True)

    try:
        html_path.write_text(html, encoding="utf-8")
        args = [
            browser,
            "--headless",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-crash-reporter",
            "--no-sandbox",
            f"--user-data-dir={profile_path}",
            "--print-to-pdf-no-header",
            f"--print-to-pdf={pdf_path}",
            html_path.resolve().as_uri(),
        ]

        exec_result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if not pdf_path.exists() or pdf_path.stat().st_size <= 0:
            stderr = (exec_result.stderr or "").strip()
            stdout = (exec_result.stdout or "").strip()
            detalhes = stderr or stdout or "Sem detalhes do navegador."
            raise RuntimeError(f"Falha ao gerar PDF via navegador headless. {detalhes}")

        return pdf_path.read_bytes()
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
