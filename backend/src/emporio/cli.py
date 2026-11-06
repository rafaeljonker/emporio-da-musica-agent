"""`emporio chat`: a terminal REPL over the agent."""

import argparse
import logging
import sys
import time
from collections.abc import Callable, Sequence
from uuid import uuid4

from emporio.bootstrap import build_agent
from emporio.config import ConfigError, Provider, load_settings
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
    chat = parser.add_subparsers(dest="command", required=True).add_parser("chat")
    chat.add_argument("--as-customer", type=int, metavar="ID", help="log in as this customer id")
    chat.add_argument("--provider", type=Provider, choices=list(Provider))
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    read: Callable[[str], str] = input,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    args = _parser().parse_args(argv)
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
