"""``jarvis doctor`` — run diagnostic checks on the OpenJarvis installation."""
# ruff: noqa: E501

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import click
from rich.console import Console
from rich.table import Table

from openjarvis.core.config import DEFAULT_CONFIG_PATH, load_config


@dataclass
class CheckResult:
    """Result of a single diagnostic check."""

    name: str
    status: str  # "ok", "warn", "fail"
    message: str
    details: Optional[str] = None


@dataclass
class _EngineProbe:
    """One engine instance and the result of its single health probe."""

    engine: Any | None
    healthy: bool
    error: str | None = None


# -- Individual checks -------------------------------------------------------


def _check_python_version() -> CheckResult:
    """Check that Python version is >= 3.10."""
    ver = sys.version_info
    version_str = f"{ver.major}.{ver.minor}.{ver.micro}"
    if (ver.major, ver.minor) >= (3, 10):
        return CheckResult("Python version", "ok", version_str)
    return CheckResult("Python version", "fail", f"{version_str} (requires >= 3.10)")


def _check_config_exists() -> CheckResult:
    """Check that the config file exists."""
    if DEFAULT_CONFIG_PATH.exists():
        return CheckResult("Config file", "ok", str(DEFAULT_CONFIG_PATH))
    return CheckResult(
        "Config file",
        "warn",
        f"Not found at {DEFAULT_CONFIG_PATH}",
        details="Run `jarvis init` to generate a config file.",
    )


def _check_config_parses() -> CheckResult:
    """Check that the config file parses successfully."""
    if not DEFAULT_CONFIG_PATH.exists():
        return CheckResult("Config parsing", "warn", "Skipped (no config file)")
    try:
        load_config()
        return CheckResult("Config parsing", "ok", "Config loaded successfully")
    except Exception as exc:
        return CheckResult("Config parsing", "fail", f"Parse error: {exc}")


def _ensure_engines_imported() -> None:
    """Import engine modules to trigger registration decorators."""
    try:
        import openjarvis.engine  # noqa: F401
    except Exception:
        pass


def _get_config() -> Any:
    """Load config or return a default if parsing fails."""
    try:
        return load_config()
    except Exception:
        from openjarvis.core.config import JarvisConfig

        return JarvisConfig()


def _probe_engines(config: Any | None = None) -> Dict[str, _EngineProbe]:
    """Instantiate and health-check every engine once, concurrently."""
    _ensure_engines_imported()

    from openjarvis.core.registry import EngineRegistry
    from openjarvis.engine import _discovery

    resolved_config = config or _get_config()
    keys = sorted(EngineRegistry.keys())

    def probe(key: str) -> tuple[str, _EngineProbe]:
        try:
            engine = _discovery._make_engine(key, resolved_config)
            return key, _EngineProbe(engine=engine, healthy=bool(engine.health()))
        except Exception as exc:
            return key, _EngineProbe(engine=None, healthy=False, error=str(exc))

    if not keys:
        return {}
    with ThreadPoolExecutor(max_workers=len(keys)) as pool:
        return dict(pool.map(probe, keys))


def _check_engines(
    probes: Optional[Dict[str, _EngineProbe]] = None,
) -> List[CheckResult]:
    """Probe each registered engine for health."""
    results: List[CheckResult] = []

    resolved_probes = probes if probes is not None else _probe_engines()

    for key, probe in resolved_probes.items():
        if probe.healthy:
            results.append(CheckResult(f"Engine: {key}", "ok", "Reachable"))
        elif probe.error:
            results.append(
                CheckResult(f"Engine: {key}", "warn", f"Unreachable ({probe.error})")
            )
        else:
            results.append(CheckResult(f"Engine: {key}", "warn", "Unreachable"))

    if not results:
        results.append(CheckResult("Engines", "warn", "No engines registered"))

    return results


def _check_models(
    probes: Optional[Dict[str, _EngineProbe]] = None,
) -> List[CheckResult]:
    """List models from healthy engines."""
    results: List[CheckResult] = []

    resolved_probes = probes if probes is not None else _probe_engines()

    for key, probe in resolved_probes.items():
        try:
            if probe.healthy and probe.engine is not None:
                models = probe.engine.list_models()
                if models:
                    model_list = ", ".join(models[:5])
                    suffix = f" (+{len(models) - 5} more)" if len(models) > 5 else ""
                    results.append(
                        CheckResult(
                            f"Models: {key}",
                            "ok",
                            f"{model_list}{suffix}",
                        )
                    )
                else:
                    results.append(
                        CheckResult(
                            f"Models: {key}",
                            "warn",
                            "No models available",
                            details="Pull a model (e.g. `ollama pull qwen3.5:2b`).",
                        )
                    )
        except Exception:
            continue

    return results


def _check_default_model(
    probes: Optional[Dict[str, _EngineProbe]] = None,
) -> CheckResult:
    """Check whether the configured default model is available."""
    try:
        config = load_config()
    except Exception:
        return CheckResult("Default model", "warn", "Skipped (config unavailable)")

    default_model = config.intelligence.default_model
    if not default_model:
        return CheckResult(
            "Default model",
            "ok",
            "Not configured (auto-routing enabled)",
            details="Router will select a model dynamically.",
        )

    from openjarvis.intelligence.model_catalog import resolve_model_id_for_engine

    preferred = config.intelligence.preferred_engine or config.engine.default
    resolved_probes = probes if probes is not None else _probe_engines(config)
    check_order = []
    if preferred:
        check_order.append(preferred)
    check_order += [k for k in resolved_probes if k != preferred]

    for key in check_order:
        try:
            probe = resolved_probes.get(key)
            if probe is not None and probe.healthy and probe.engine is not None:
                models = probe.engine.list_models()
                resolved_model = resolve_model_id_for_engine(default_model, key)
                if resolved_model in models:
                    return CheckResult(
                        "Default model",
                        "ok",
                        f"{default_model} (on {key})",
                    )
        except Exception:
            continue

    return CheckResult(
        "Default model",
        "warn",
        f"{default_model} not found on any engine",
    )


def _check_optional_deps() -> List[CheckResult]:
    """Check availability of optional dependency packages."""
    results: List[CheckResult] = []
    optional_packages = [
        ("fastapi", "openjarvis[server]", "REST API server"),
        ("torch", "pip install torch", "SFT/GRPO training"),
        ("pynvml", "openjarvis[gpu-metrics]", "NVIDIA energy monitoring"),
        ("amdsmi", "openjarvis[energy-amd]", "AMD energy monitoring"),
        ("colbert", "openjarvis[memory-colbert]", "ColBERT memory backend"),
        (
            "zeus_apple_silicon",
            "openjarvis[energy-apple]",
            "Apple Silicon energy monitoring",
        ),
        ("apple_fm_sdk", "openjarvis[afm]", "Apple Foundation Models (AFM 3)"),
    ]
    for pkg, install_hint, description in optional_packages:
        try:
            __import__(pkg)
            results.append(CheckResult(f"Optional: {description}", "ok", "Installed"))
        except Exception:
            results.append(
                CheckResult(
                    f"Optional: {description}",
                    "warn",
                    f"Not installed ({install_hint})",
                )
            )
    return results


def _check_speech_backend() -> CheckResult:
    """Check whether the configured speech backend can load."""
    try:
        from openjarvis.speech._discovery import get_speech_backend

        config = _get_config()
        backend = get_speech_backend(config)
        if backend is None:
            return CheckResult(
                "Speech backend",
                "warn",
                "Not configured",
                details="Install desktop dependencies with `uv sync --extra desktop`.",
            )

        if backend.health():
            return CheckResult(
                "Speech backend",
                "ok",
                f"{backend.backend_id} ready",
            )

        details = None
        last_error = getattr(backend, "last_error", None)
        if callable(last_error):
            details = last_error()
        return CheckResult(
            "Speech backend",
            "warn",
            f"{backend.backend_id} unavailable",
            details=details
            or "Install desktop dependencies with `uv sync --extra desktop`.",
        )
    except Exception as exc:
        return CheckResult(
            "Speech backend",
            "warn",
            f"Could not check: {exc}",
        )


def _check_security_profile() -> CheckResult:
    """Check if a security profile is configured."""
    try:
        from openjarvis.core.config import load_config

        config = load_config()
        if config.security.profile:
            return CheckResult(
                name="Security profile",
                status="ok",
                message=f"Profile '{config.security.profile}' active",
            )
        return CheckResult(
            name="Security profile",
            status="warn",
            message="No security profile set",
            details="Recommended: add security.profile = 'personal' to config.toml",
        )
    except Exception as exc:
        return CheckResult(
            name="Security profile",
            status="fail",
            message=f"Could not check: {exc}",
        )


def _check_nodejs() -> CheckResult:
    """Check Node.js version for Node-backed integrations."""
    node_path = shutil.which("node")
    if not node_path:
        return CheckResult(
            "Node.js",
            "warn",
            "Not found",
            details=(
                "Node.js 22+ is required for ClaudeCodeAgent and the "
                "WhatsApp Baileys channel bridge."
            ),
        )
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version_str = result.stdout.strip()
        # Parse "v22.1.0" -> (22, 1, 0)
        parts = version_str.lstrip("v").split(".")
        major = int(parts[0])
        if major >= 22:
            return CheckResult("Node.js", "ok", version_str)
        return CheckResult(
            "Node.js",
            "warn",
            f"{version_str} (requires >= v22)",
            details=(
                "Upgrade Node.js for ClaudeCodeAgent and WhatsApp Baileys support."
            ),
        )
    except Exception as exc:
        return CheckResult("Node.js", "warn", f"Error checking version: {exc}")


# -- Main command -------------------------------------------------------------


# --- Fork PT-BR: tradução apenas na exibição (o JSON/testes seguem em inglês) ---
_PT_EXACT = {
    "Python version": "Versão do Python",
    "Config file": "Arquivo de configuração",
    "Config parsing": "Leitura da configuração",
    "Default model": "Modelo padrão",
    "Speech backend": "Backend de fala",
    "Security profile": "Perfil de segurança",
    "Engines": "Motores",
    "Reachable": "Acessível",
    "Unreachable": "Inacessível",
    "Installed": "Instalado",
    "Not found": "Não encontrado",
    "Not configured": "Não configurado",
    "Skipped (no config file)": "Ignorado (sem arquivo de configuração)",
    "Config loaded successfully": "Configuração carregada com sucesso",
    "Skipped (config unavailable)": "Ignorado (configuração indisponível)",
    "Not configured (auto-routing enabled)": "Não configurado (roteamento automático ativo)",
    "Router will select a model dynamically.": "O roteador escolherá um modelo dinamicamente.",
    "No models available": "Nenhum modelo disponível",
    "No engines registered": "Nenhum motor registrado",
    "No security profile set": "Nenhum perfil de segurança definido",
    "Run `jarvis init` to generate a config file.": "Execute `jarvis init` para gerar o arquivo de configuração.",
    "Pull a model (e.g. `ollama pull qwen3.5:2b`).": "Baixe um modelo (ex.: `ollama pull qwen3.5:2b`).",
    "Install desktop dependencies with `uv sync --extra desktop`.": "Instale as dependências desktop com `uv sync --extra desktop`.",
    "Recommended: add security.profile = 'personal' to config.toml": "Recomendado: adicione security.profile = 'personal' ao config.toml",
    "Node.js 22+ is required for ClaudeCodeAgent and the WhatsApp Baileys channel bridge.": "Node.js 22+ é necessário para o ClaudeCodeAgent e a ponte de canal WhatsApp Baileys.",
    "Upgrade Node.js for ClaudeCodeAgent and WhatsApp Baileys support.": "Atualize o Node.js para ter suporte ao ClaudeCodeAgent e ao WhatsApp Baileys.",
    "REST API server": "Servidor de API REST",
    "SFT/GRPO training": "Treinamento SFT/GRPO",
    "NVIDIA energy monitoring": "Monitoramento de energia NVIDIA",
    "AMD energy monitoring": "Monitoramento de energia AMD",
    "ColBERT memory backend": "Backend de memória ColBERT",
    "Apple Silicon energy monitoring": "Monitoramento de energia Apple Silicon",
    "Apple Foundation Models (AFM 3)": "Apple Foundation Models (AFM 3)",
}
_PT_PREFIX = [
    ("Engine: ", "Motor: "),
    ("Models: ", "Modelos: "),
    ("Optional: ", "Opcional: "),
    ("Not found at ", "Não encontrado em "),
    ("Parse error: ", "Erro de leitura: "),
    ("Not installed (", "Não instalado ("),
    ("Unreachable (", "Inacessível ("),
    ("Could not check: ", "Não foi possível verificar: "),
    ("Error checking version: ", "Erro ao verificar a versão: "),
]
_PT_SUFFIX = [
    (" (requires >= 3.10)", " (requer >= 3.10)"),
    (" (requires >= v22)", " (requer >= v22)"),
    (" not found on any engine", " não encontrado em nenhum motor"),
    (" ready", " pronto"),
    (" unavailable", " indisponível"),
    (" more)", " a mais)"),
]


def _L(en: str, pt: str) -> str:
    """Escolhe o texto conforme OPENJARVIS_LANG (padrão pt-BR)."""
    import os

    return (
        pt
        if os.environ.get("OPENJARVIS_LANG", "pt-BR").lower().startswith("pt")
        else en
    )


def _pt(text: str) -> str:
    """Traduz um texto de verificação para exibição (PT-BR)."""
    import os
    import re

    if not os.environ.get("OPENJARVIS_LANG", "pt-BR").lower().startswith("pt"):
        return text
    if text in _PT_EXACT:
        return _PT_EXACT[text]
    for en, pt in _PT_PREFIX:
        if text.startswith(en):
            text = pt + text[len(en) :]
            break
    for en, pt in _PT_SUFFIX:
        if text.endswith(en) or en in text:
            text = text.replace(en, pt)
    text = re.sub(r"\(\+(\d+) a mais\)", r"(+\1 a mais)", text)
    # traduz o restante de "Optional: <descrição>" / "Motor: x"
    m = re.match(r"^(Opcional: )(.+)$", text)
    if m and m.group(2) in _PT_EXACT:
        text = m.group(1) + _PT_EXACT[m.group(2)]
    return text


_STATUS_ICONS = {
    "ok": "[green]\u2713[/green]",
    "warn": "[yellow]![/yellow]",
    "fail": "[red]\u2717[/red]",
}


def _run_all_checks() -> List[CheckResult]:
    """Run all diagnostic checks and return results."""
    checks: List[CheckResult] = []
    checks.append(_check_python_version())
    checks.append(_check_config_exists())
    checks.append(_check_config_parses())
    engine_probes = _probe_engines()
    checks.extend(_check_engines(engine_probes))
    checks.extend(_check_models(engine_probes))
    checks.append(_check_default_model(engine_probes))
    checks.extend(_check_optional_deps())
    checks.append(_check_speech_backend())
    checks.append(_check_nodejs())
    checks.append(_check_security_profile())
    return checks


def _results_to_dicts(checks: List[CheckResult]) -> List[Dict[str, Any]]:
    """Convert CheckResult list to JSON-serializable dicts."""
    return [asdict(c) for c in checks]


@click.command()
@click.option("--json", "as_json", is_flag=True, help="Output results as JSON.")
def doctor(as_json: bool) -> None:
    """Run diagnostic checks on your OpenJarvis installation."""
    checks = _run_all_checks()

    if as_json:
        click.echo(json.dumps(_results_to_dicts(checks), indent=2))
        return

    console = Console()
    console.print()
    console.print(
        _L(
            "[bold]OpenJarvis Doctor[/bold]",
            "[bold]OpenJarvis Doctor — diagnóstico[/bold]",
        )
    )
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column(_L("Status", "Est."), width=4, justify="center")
    table.add_column(_L("Check", "Verificação"))
    table.add_column(_L("Result", "Resultado"))

    for check in checks:
        icon = _STATUS_ICONS.get(check.status, "?")
        message = _pt(check.message)
        if check.details:
            message += f"\n  [dim]{_pt(check.details)}[/dim]"
        table.add_row(icon, _pt(check.name), message)

    console.print(table)

    ok_count = sum(1 for c in checks if c.status == "ok")
    warn_count = sum(1 for c in checks if c.status == "warn")
    fail_count = sum(1 for c in checks if c.status == "fail")
    console.print()
    console.print(
        _L(
            f"  {ok_count} passed, {warn_count} warnings, {fail_count} failures",
            f"  {ok_count} aprovadas, {warn_count} avisos, {fail_count} falhas",
        )
    )
    console.print()

    # Background tasks section
    from openjarvis.cli._bg_state import get_status
    from openjarvis.core.paths import get_config_dir

    scripts_dir = get_config_dir() / ".scripts"
    console.print(
        _L("[bold]Background tasks[/bold]", "[bold]Tarefas em segundo plano[/bold]")
    )
    bg = get_status()
    bg_failed = False

    if bg.rust_extension == "ready":
        console.print(
            _L(
                "  [green]✓[/green] Rust extension: ready",
                "  [green]✓[/green] Extensão Rust: pronta",
            )
        )
    elif bg.rust_extension == "failed":
        console.print(
            _L(
                f"  [red]✗[/red] Rust extension: failed — {bg.rust_error[:80]}",
                f"  [red]✗[/red] Extensão Rust: falhou — {bg.rust_error[:80]}",
            )
        )
        console.print(
            f"    {_L('retry', 'tentar de novo')}: {scripts_dir}/install-rust.sh && "
            f"{scripts_dir}/build-extension.sh"
        )
        bg_failed = True
    else:
        console.print(
            _L(
                "  [yellow]…[/yellow] Rust extension: building (run in background)",
                "  [yellow]…[/yellow] Extensão Rust: compilando (em segundo plano)",
            )
        )

    if not bg.models:
        console.print(
            _L(
                "  [dim]no model downloads tracked[/dim]",
                "  [dim]nenhum download de modelo em andamento[/dim]",
            )
        )
    for model_id, state in bg.models.items():
        if state == "ready":
            console.print(
                _L(
                    f"  [green]✓[/green] {model_id}: ready",
                    f"  [green]✓[/green] {model_id}: pronto",
                )
            )
        elif state == "failed":
            console.print(
                _L(
                    f"  [red]✗[/red] {model_id}: failed",
                    f"  [red]✗[/red] {model_id}: falhou",
                )
            )
            console.print(
                f"    {_L('retry', 'tentar de novo')}: {scripts_dir}/pull-model.sh {model_id}"
            )
            bg_failed = True
        else:
            console.print(
                _L(
                    f"  [yellow]…[/yellow] {model_id}: downloading",
                    f"  [yellow]…[/yellow] {model_id}: baixando",
                )
            )

    if bg_failed:
        raise click.exceptions.Exit(code=1)
