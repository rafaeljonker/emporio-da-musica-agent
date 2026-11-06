"""Load test for the chat API: each virtual user is a shopper taking SSE turns.

Plain HttpUser (not FastHttpUser) so the reported time includes the whole SSE body.
Reads DEMO_EMAIL and DEMO_PASSWORD from the environment.
"""

import os
import random

from locust import HttpUser, between, task

MESSAGES = [
    "Oi, tudo bem?",
    "Quais violões vocês têm até R$ 2.000?",
    "Quero saber o prazo de troca de um produto.",
    "Tem alguma promoção de teclados hoje?",
    "Em quantas vezes posso parcelar uma guitarra de R$ 3.500?",
]


class Shopper(HttpUser):
    wait_time = between(3, 8)

    def on_start(self) -> None:
        self.client.post(
            "/api/auth/login",
            json={"email": os.environ["DEMO_EMAIL"], "password": os.environ["DEMO_PASSWORD"]},
        )
        customers = self.client.get("/api/customers").json()
        self.client.put("/api/identity", json={"customer_id": random.choice(customers)["id"]})

    @task
    def chat(self) -> None:
        with self.client.post(
            "/api/chat", json={"text": random.choice(MESSAGES)}, catch_response=True
        ) as response:
            body = response.text
            if "event: error" in body:
                response.failure("error event")
            elif "event: done" not in body:
                response.failure("missing done")
