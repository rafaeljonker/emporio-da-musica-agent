# Model selection

## Goal
Choose the support agent's model with data, not opinion: which one calls the right tool, cites the right fact and writes like a store attendant, at an acceptable cost and latency.

## Method
- 14 scenarios from the case (catalog, price, PIX, installments, promotions, address, opening hours, order with and without identity, withdrawal (arrependimento), accessory, out of scope, discontinued product), running with the real tools over the store data.
- Metrics per model:
  - **right tool:** the agent called the expected tool;
  - **right fact:** the answer contains the expected fact (price, lead time, status);
  - **AI tells:** answers with em dashes, markdown or stock phrases;
  - **naturalness:** a 1 to 5 score given by an LLM judge;
  - **latency** and **tokens per conversation**.
- Caveats:
  - one run per model, no repetition;
  - the judge is a Gemini model and may favor its own family;
  - the latency measured on NVIDIA's free API includes queue time.

## Round 1: 9 models, prompt v1
| Model | Right tool | Right fact | Both | Human score (1-5) | Answers with AI tell | Errors | Tokens/conversation |
|---|---|---|---|---|---|---|---|
| gemini-3.8-flash | 14/14 | 14/14 | **14/14** | 4.2 | 0 | 0 | 2205 |
| gemini-3.5-flash-lite | 14/14 | 13/14 | **13/14** | 4.7 | 0 | 0 | 1671 |
| gemini-2.5-flash | 8/14 | 8/14 | **7/14** | 3.8 | 1 | 0 | 1161 |
| google/gemma-4-31b-it | 13/14 | 10/14 | **10/14** | 4.8 | 0 | 0 | 1449 |
| minimaxai/minimax-m3.1-flash | 5/14 | 5/14 | **5/14** | 2.6 | 0 | 9 | 2710 |
| nvidia/nemotron-3.5-lightning-30b-a3b | 14/14 | 13/14 | **13/14** | 3.1 | 3 | 0 | 2737 |
| nvidia/nemotron-3-ultra-550b-a55b | 14/14 | 13/14 | **13/14** | 3.9 | 4 | 0 | 2670 |
| mistralai/mistral-large-4-1t-a52b | 14/14 | 14/14 | **14/14** | 4.5 | 1 | 0 | 2129 |
| nvidia/nemotron-3.5-bolt-e4b | 3/14 | 3/14 | **2/14** | 3.3 | 0 | 0 | 748 |

MiniMax's 9 errors were 429 responses (rate limit), not a model failure. Gemma 4 31B had the most human voice, but it failed by not calling tools in some scenarios (for example, asking an already identified customer for the order number).

## Round 2: prompt v2 and tolerant search
Changes: explicit tool-use rules in the prompt (an identified customer queries `list_my_orders`; a promotion always comes with original price, % and final price) and product search tolerant to plural and accent. Run with Gemma 4 31B and Mistral Large 4 through NVIDIA's API.

| Model | Right tool | Right fact | Both | Human score | AI tell | Tokens/conversation |
|---|---|---|---|---|---|---|
| google/gemma-4-31b-it | 14/14 | 12/14 | 12/14 | 4.8 | 0 | 1986 |
| mistralai/mistral-large-4-1t-a52b | 14/14 | 14/14 | 14/14 | 4.6 | 1 | 2527 |

Gemma reached 14/14 on tool. The 2 remaining error marks are false negatives of the verifier, not model errors:
- **installments:** the model answered "9 parcelas de 100 reais" and the verifier expected the form "9x";
- **anonymous withdrawal (arrependimento):** the model asked for the order number and e-mail before answering, which is correct behavior, and the verifier expected the 7-day deadline to be cited.

With the verifier accepting paraphrases, Gemma stands at an effective 14/14.

## Round 3: Gemma 4 31B self-hosted on Modal
Gemma 4 31B on an H200 GPU with vLLM, serverless on Modal, same prompt v2.
- **Hits:** effective 14/14, voice 4.7, no AI tells.
- **Latency:** median of 2.2 s and maximum of 3.9 s, against 7.0 s and 44.4 s in the queue of NVIDIA's free API.
- **Cold start:** 175 s with the GPU off (to be optimized; see `docs/superpowers/specs/2026-11-05-emporio-agent-design.md`).

## Decision
- **Default:** Gemma 4 31B self-hosted on Modal. Best voice, accuracy equivalent to the larger models, low latency and no third-party per-token cost.
- **Alternatives:** Gemini, OpenAI and Anthropic, enabled by flag (`--provider`) and key defined together. Without the flag, it uses Gemma.

## Lessons
- Explicit tool-use rules in the prompt matter more than model size.
- Product search must be tolerant to plural and accent.
- The evals verifier must accept paraphrases ("9 parcelas" = "9x"; "não está mais disponível"), or it measures the text and not the behavior.
