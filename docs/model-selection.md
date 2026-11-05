# Seleção de modelo

## Objetivo
Escolher o modelo do agente de atendimento com dados, não com opinião: qual acerta a ferramenta certa, cita o fato certo e escreve como um atendente de loja, a um custo e latência aceitáveis.

## Método
- 14 cenários do case (catálogo, preço, PIX, parcelamento, promoções, endereço, horário, pedido com e sem identidade, arrependimento, acessório, fora de escopo, produto descontinuado), rodando com as tools reais sobre os dados da loja.
- Métricas por modelo:
  - **tool certa:** o agente chamou a ferramenta esperada;
  - **fato certo:** a resposta contém o fato esperado (preço, prazo, status);
  - **sinais de IA:** respostas com travessão, markdown ou frases feitas;
  - **naturalidade:** nota de 1 a 5 dada por um juiz LLM;
  - **latência** e **tokens por conversa**.
- Ressalvas:
  - uma rodada por modelo, sem repetição;
  - o juiz é um modelo Gemini e pode favorecer a própria família;
  - a latência medida na API gratuita da NVIDIA inclui tempo de fila.

## Rodada 1: 9 modelos, prompt v1
| Modelo | Tool certa | Fato certo | Ambos | Nota humana (1-5) | Respostas c/ sinal de IA | Erros | Tokens/conversa |
|---|---|---|---|---|---|---|---|
| gemini-3.8-flash | 14/14 | 14/14 | **14/14** | 4,2 | 0 | 0 | 2205 |
| gemini-3.5-flash-lite | 14/14 | 13/14 | **13/14** | 4,7 | 0 | 0 | 1671 |
| gemini-2.5-flash | 8/14 | 8/14 | **7/14** | 3,8 | 1 | 0 | 1161 |
| google/gemma-4-31b-it | 13/14 | 10/14 | **10/14** | 4,8 | 0 | 0 | 1449 |
| minimaxai/minimax-m3.1-flash | 5/14 | 5/14 | **5/14** | 2,6 | 0 | 9 | 2710 |
| nvidia/nemotron-3.5-lightning-30b-a3b | 14/14 | 13/14 | **13/14** | 3,1 | 3 | 0 | 2737 |
| nvidia/nemotron-3-ultra-550b-a55b | 14/14 | 13/14 | **13/14** | 3,9 | 4 | 0 | 2670 |
| mistralai/mistral-large-4-1t-a52b | 14/14 | 14/14 | **14/14** | 4,5 | 1 | 0 | 2129 |
| nvidia/nemotron-3.5-bolt-e4b | 3/14 | 3/14 | **2/14** | 3,3 | 0 | 0 | 748 |

Os 9 erros do MiniMax foram respostas 429 (limite de requisições), não falha do modelo. O Gemma 4 31B teve a voz mais humana, mas errou ao não chamar tools em alguns cenários (por exemplo, pedir o número do pedido a um cliente já identificado).

## Rodada 2: prompt v2 e busca tolerante
Mudanças: regras explícitas de uso de tool no prompt (cliente identificado consulta `list_my_orders`; promoção sempre com preço original, % e preço final) e busca de produtos tolerante a plural e acento. Rodado com Gemma 4 31B e Mistral Large 4 pela API da NVIDIA.

| Modelo | Tool certa | Fato certo | Ambos | Nota humana | Sinal de IA | Tokens/conversa |
|---|---|---|---|---|---|---|
| google/gemma-4-31b-it | 14/14 | 12/14 | 12/14 | 4,8 | 0 | 1986 |
| mistralai/mistral-large-4-1t-a52b | 14/14 | 14/14 | 14/14 | 4,6 | 1 | 2527 |

O Gemma chegou a 14/14 em tool. As 2 marcações de erro restantes são falsos negativos do verificador, não erros do modelo:
- **parcelamento:** o modelo respondeu "9 parcelas de 100 reais" e o verificador esperava a forma "9x";
- **arrependimento anônimo:** o modelo pediu número do pedido e e-mail antes de responder, comportamento correto, e o verificador esperava a citação do prazo de 7 dias.

Com o verificador aceitando paráfrases, o Gemma fica em 14/14 efetivos.

## Rodada 3: Gemma 4 31B self-hosted no Modal
Gemma 4 31B em GPU H200 com vLLM, serverless no Modal, mesmo prompt v2.
- **Acertos:** 14/14 efetivos, voz 4,7, sem sinais de IA.
- **Latência:** mediana de 2,2 s e máxima de 3,9 s, contra 7,0 s e 44,4 s na fila da API gratuita da NVIDIA.
- **Cold start:** 175 s com a GPU desligada (a otimizar; ver `docs/superpowers/specs/2026-11-05-emporio-agent-design.md`).

## Decisão
- **Padrão:** Gemma 4 31B self-hosted no Modal. Melhor voz, acerto equivalente aos modelos maiores, latência baixa e sem custo por token de terceiros.
- **Alternativas:** Gemini, OpenAI e Anthropic, ativados por flag (`--provider`) e chave definidas juntas. Sem flag, usa o Gemma.

## Lições
- Regras explícitas de uso de tool no prompt pesam mais que o tamanho do modelo.
- A busca de produtos precisa ser tolerante a plural e acento.
- O verificador das evals precisa aceitar paráfrases ("9 parcelas" = "9x"; "não está mais disponível"), ou mede o texto e não o comportamento.
