# Personas

> Phase: design | Project: emporio-chat | Generated: 2026-11-05 | Source: [BRIEF.md](../../BRIEF.md) audience

## 1. Camila, the Artefact evaluator (primary)

| | |
|---|---|
| Demographics | 30s, senior AI/ML engineer on the hiring panel, São Paulo; desktop browser, sometimes opens the link on a phone first |
| Goals | reach a real conversation fast; test the 4 statement scenarios (price, order, return, accessory); see tool accuracy and cost per turn; judge "lógica, clareza e iniciativa" |
| Pain points | unexplained waits (175 s cold start reads as "broken"); demos that hide the model behind canned replies; UI noise that makes the agent look like a template |
| Context | reviewing several cases in one sitting; will try edge cases (anonymous order question, "tá aberto agora?"); reads the README before or after |
| Design response | honest warm-up with real stages and an expected time; type-while-waiting queue; metrics one click away (session totals visible in the collapsed summary, per-turn history inside); "Conversar como…" to test identity without logging in as a customer |

## 2. Luísa, the store's customer (secondary, simulated)

| | |
|---|---|
| Demographics | 22–28, self-taught guitarist, Campo Grande; lives on WhatsApp, phone only |
| Goals | know the real price and whether the cheaper instrument is enough; check her order without hunting for a number |
| Pain points | pushy sellers; bots that sound like bots; being upsold |
| Context | arrives from a WhatsApp link; one hand, short messages |
| Design response | plain WhatsApp-like bubbles, walnut/spruce speaker contrast, honest ProductCard ("Na medida pro seu nível"), handoff bubble instead of guesses |

## 3. Caio, the developer running it locally (tertiary)

| | |
|---|---|
| Context | `make up PROVIDER=local` on a laptop without GPU, or a provider API key |
| Need | know that slow replies are expected, not a bug |
| Design response | local-CPU warm-up variant + persistent quiet notice; provider mode skips the warm-up entirely |

## Related
- [information-architecture.md](./information-architecture.md)
