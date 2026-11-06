"""Load test for the chat API: each virtual user is a shopper taking SSE turns.

Plain HttpUser (not FastHttpUser) so the reported time includes the whole SSE body.
Reads DEMO_EMAIL and DEMO_PASSWORD from the environment.
"""

import os
import random
import sys

from locust import HttpUser, between, task

try:
    DEMO_EMAIL = os.environ["DEMO_EMAIL"]
    DEMO_PASSWORD = os.environ["DEMO_PASSWORD"]
except KeyError as missing:
    sys.exit(f"loadtest: set DEMO_EMAIL and DEMO_PASSWORD ({missing} is missing)")

MESSAGES = [
    "Oi, tudo bem?",
    "Quais violões vocês têm até R$ 2.000?",
    "Quero saber o prazo de troca de um produto.",
    "Tem alguma promoção de teclados hoje?",
    "Em quantas vezes posso parcelar uma guitarra de R$ 3.500?",
]


class Shopper(HttpUser):
    wait_time = between(3, 8)

    def _step(self, name: str, method: str, path: str, **kwargs: object) -> object | None:
        """Runs one setup request; on a non-200 it records a named failure and stops the user."""
        with self.client.request(method, path, catch_response=True, **kwargs) as response:
            if response.status_code != 200:
                response.failure(f"{name} http {response.status_code}")
                self.stop()
                return None
            return response.json()

    def on_start(self) -> None:
        creds = {"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        if self._step("login", "POST", "/api/auth/login", json=creds) is None:
            return
        customers = self._step("customers", "GET", "/api/customers")
        if not isinstance(customers, list) or not customers:
            return
        self._step(
            "identity", "PUT", "/api/identity", json={"customer_id": random.choice(customers)["id"]}
        )

    @task
    def chat(self) -> None:
        with self.client.post(
            "/api/chat", json={"text": random.choice(MESSAGES)}, catch_response=True
        ) as response:
            body = response.text
            if response.status_code != 200:
                response.failure(f"http {response.status_code}")
            elif "event: error" in body:
                response.failure("error event")
            elif "event: done" not in body:
                response.failure("missing done")
