# ruff: noqa: E501
"""Localização PT-BR do CLI (fork).

O upstream não tem i18n. Em vez de editar dezenas de módulos de comandos,
este módulo:

* troca as mensagens embutidas do Click ("Usage:", "Options:", erros…);
* traduz a descrição curta dos comandos exibida em ``jarvis --help``.

Ativado por padrão. Defina ``OPENJARVIS_LANG=en`` para voltar ao inglês.
"""

from __future__ import annotations

import os
import sys

_CLICK = {
    "Usage:": "Uso:",
    "Options": "Opções",
    "Commands": "Comandos",
    "Positional arguments": "Argumentos posicionais",
    "Show this message and exit.": "Mostra esta mensagem e sai.",
    "Show the version and exit.": "Mostra a versão e sai.",
    "%(prog)s, version %(version)s": "%(prog)s, versão %(version)s",
    "Aborted!": "Abortado!",
    "Error: {message}": "Erro: {message}",
    "Try '{command} {option}' for help.": "Use '{command} {option}' para ajuda.",
    "No such command {name!r}.": "Comando inexistente: {name!r}.",
    "No such option {name!r}.": "Opção inexistente: {name!r}.",
    "Missing command.": "Comando ausente.",
    "Missing option": "Opção ausente",
    "Missing argument": "Argumento ausente",
    "Missing parameter": "Parâmetro ausente",
    "Missing {param_type}": "{param_type} ausente",
    "Invalid value: {message}": "Valor inválido: {message}",
    "Invalid value for {param_hint}: {message}": "Valor inválido para {param_hint}: {message}",
    "Option {name!r} does not take a value.": "A opção {name!r} não recebe valor.",
    "Choose from:\n\t{choices}": "Escolha entre:\n\t{choices}",
    "default: {default}": "padrão: {default}",
    "env var: {var}": "variável de ambiente: {var}",
    "(dynamic)": "(dinâmico)",
    "deprecated": "obsoleto",
    "Do you want to continue?": "Deseja continuar?",
    "Repeat for confirmation": "Repita para confirmar",
    "Press any key to continue...": "Pressione qualquer tecla para continuar...",
    "Confirm the action without prompting.": "Confirma a ação sem perguntar.",
    "{name} {filename!r} does not exist.": "{name} {filename!r} não existe.",
    "{name} {filename!r} is a directory.": "{name} {filename!r} é um diretório.",
    "{name} {filename!r} is a file.": "{name} {filename!r} é um arquivo.",
    "{value!r} is not a valid {number_type}.": "{value!r} não é {number_type} válido.",
    "{value} is not in the range {range}.": "{value} está fora do intervalo {range}.",
    "file": "arquivo",
    "directory": "diretório",
    "path": "caminho",
}

# Descrição curta de cada comando (usada na listagem de `jarvis --help`).
COMMANDS = {
    "add": "Adiciona a configuração de um servidor MCP.",
    "agents": "Gerencia agentes persistentes — criar, inspecionar, conversar, vincular canais.",
    "ask": "Faz uma pergunta ao Jarvis.",
    "auth": "Gerencia as chaves de autenticação da API.",
    "bench": "Executa benchmarks de inferência.",
    "channel": "Gerencia canais de mensagens.",
    "channels": "Gerencia canais de mensagens (iMessage/SMS via SendBlue, Slack).",
    "chat": "Inicia uma conversa interativa de vários turnos.",
    "compose": "Compõe, executa, mede e implanta configurações do OpenJarvis.",
    "config": "Inspeciona a configuração — mostra ajustes, hardware e arquivos de config.",
    "connect": "Gerencia conexões de fontes de dados (Gmail, Obsidian etc.).",
    "deep-research-setup": "Detecta fontes locais, indexa e abre o chat de Pesquisa Profunda.",
    "digest": "Exibe e reproduz o resumo matinal.",
    "doctor": "Executa diagnósticos da sua instalação do OpenJarvis.",
    "eval": "Framework de avaliação — mede modelos, agentes e aprendizado.",
    "feedback": "Gerencia o feedback dos rastros.",
    "gateway": "Gerencia o gateway multicanal do OpenJarvis.",
    "gui": "Abre a interface gráfica no navegador padrão.",
    "host": "Baixa (se preciso) e serve um modelo localmente.",
    "init": "Detecta o hardware e gera o config.toml.",
    "memory": "Gerencia o repositório de memória.",
    "mine": "Configura e executa a mineração Pearl.",
    "model": "Gerencia modelos de linguagem.",
    "operators": "Gerencia operadores — agentes autônomos persistentes e agendados.",
    "optimize": "Otimização de configuração guiada por LLM.",
    "pearl": "Acessa as ferramentas de nó, carteira e RPC do Pearl.",
    "quickstart": "Configuração guiada em 5 passos para novos usuários.",
    "registry": "Inspeciona componentes registrados — lista registros e entradas.",
    "research": "Detecta fontes locais, indexa e abre o chat de Pesquisa Profunda.",
    "restart": "Reinicia o daemon do servidor OpenJarvis.",
    "scan": "Audita seu ambiente em busca de riscos de privacidade e segurança.",
    "scheduler": "Gerencia tarefas agendadas.",
    "self-update": "Atualiza o OpenJarvis para a versão mais recente.",
    "serve": "Inicia o servidor de API compatível com OpenAI.",
    "skill": "Gerencia habilidades reutilizáveis.",
    "start": "Inicia o servidor OpenJarvis como daemon em segundo plano.",
    "status": "Mostra o status do daemon do servidor OpenJarvis.",
    "stop": "Para o daemon do servidor OpenJarvis em execução.",
    "telemetry": "Consulta e gerencia os dados de telemetria de inferência.",
    "tool": "Gerencia ferramentas — listar, inspecionar.",
    "tunnel": "Inicia um túnel Cloudflare ou gerencia a configuração.",
    "vault": "Gerencia credenciais criptografadas.",
    "workflow": "Gerencia fluxos de trabalho — listar, executar, status.",
}

_TOP_OPTIONS = {
    "version": "Mostra a versão e sai.",
    "verbose": "Ativa o log de depuração",
    "quiet": "Suprime a saída que não seja erro",
    "pick_model_bare": "Em `jarvis` sem argumentos: força a lista interativa de modelos.",
}


def enabled() -> bool:
    return os.environ.get("OPENJARVIS_LANG", "pt-BR").lower().startswith("pt")


def _patch_click() -> None:
    import gettext as _gt  # noqa: F401

    def tr(message: str) -> str:
        return _CLICK.get(message, message)

    for name, mod in list(sys.modules.items()):
        if (name == "click" or name.startswith("click.")) and mod is not None:
            if getattr(mod, "_", None) is not None and callable(mod._):
                mod._ = tr  # type: ignore[attr-defined]


def apply(cli) -> None:
    """Aplica a localização ao grupo raiz ``cli``. Idempotente."""
    if not enabled():
        return
    _patch_click()
    cli.help = "OpenJarvis — backend modular de assistente de IA"
    for param in cli.params:
        if param.name in _TOP_OPTIONS:
            param.help = _TOP_OPTIONS[param.name]
    for name, cmd in cli.commands.items():
        text = COMMANDS.get(name)
        if text:
            cmd.short_help = text
