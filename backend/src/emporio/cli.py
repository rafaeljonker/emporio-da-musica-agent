"""`emporio chat`: a terminal REPL over the agent."""

import argparse
import logging
import os
import sys
import time
from collections.abc import Callable, Sequence
from uuid import uuid4

from emporio.bootstrap import build_agent, run_mcp
from emporio.config import (
    ConfigError,
    Provider,
    load_mcp_settings,
    load_provider_settings,
    load_settings,
)
from emporio.db import DatabaseNotConfigured
from emporio.support.domain.channel_identity import ChannelIdentity

logger = logging.getLogger("emporio.cli")
_DIM = "\033[2m"
_RESET = "\033[0m"
_EXIT_WORDS = {"sair", "exit", "quit"}


def bubble_pause(bubble: str) -> float:
    """Typing pause in seconds: 400 ms plus 15 ms per character, capped at 1500 ms."""
    return min(1500, 400 + 15 * len(bubble)) / 1000


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="emporio")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("mcp", help="serve the tools over MCP (stdio)")
    chat_options = argparse.ArgumentParser(add_help=False)
    chat_options.add_argument(
        "--as-customer", type=int, metavar="ID", help="log in as this customer id"
    )
    chat_options.add_argument("--provider", type=Provider, choices=list(Provider))
    commands.add_parser("chat", parents=[chat_options])
    commands.add_parser(
        "check-config",
        parents=[chat_options],
        help="check the provider settings and exit (no Langfuse, no database)",
    )
    return parser


def _serve_mcp() -> None:
    raw = os.environ.get("EMPORIO_MCP_CUSTOMER_ID", "")
    try:
        customer_id = int(raw) if raw else None
    except ValueError:
        print("EMPORIO_MCP_CUSTOMER_ID precisa ser um número inteiro", file=sys.stderr)
        raise SystemExit(2) from None
    try:
        run_mcp(load_mcp_settings(), customer_id)
    except (ConfigError, DatabaseNotConfigured) as err:
        print(err, file=sys.stderr)
        raise SystemExit(2) from err


def main(
    argv: Sequence[str] | None = None,
    *,
    read: Callable[[str], str] = input,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    args = _parser().parse_args(argv)
    if args.command == "mcp":
        _serve_mcp()
        return
    if args.command == "check-config":
        try:
            load_provider_settings(args.provider)
        except ConfigError as err:
            print(err, file=sys.stderr)
            raise SystemExit(2) from err
        return
    try:
        agent = build_agent(load_settings(provider=args.provider))
    except (ConfigError, DatabaseNotConfigured) as err:
        print(err, file=sys.stderr)
        raise SystemExit(2) from err
    identity = ChannelIdentity("cli", args.as_customer, uuid4().hex)
    try:
        if args.as_customer is not None and not agent.customer_exists(args.as_customer):
            print(f"cliente {args.as_customer} não encontrado", file=sys.stderr)
            raise SystemExit(2)
        while True:
            try:
                text = read("você> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if text.lower() in _EXIT_WORDS:
                break
            if not text:
                continue
            try:
                reply = agent.handle(identity, text)
            except Exception:
                logger.exception("turn failed")
                print("erro nesta mensagem, tente de novo", file=sys.stderr)
                continue
            for bubble in reply.bubbles:
                sleep(bubble_pause(bubble))
                print(bubble)
            print(f"{_DIM}[{reply.scope.value} · trace {reply.trace_id}]{_RESET}")
    finally:
        agent.close()


if __name__ == "__main__":
    main()
