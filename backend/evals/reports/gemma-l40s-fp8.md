# Agent eval: gemma (google/gemma-4-31B-it)
Run: 2026-11-06T17:19:47+00:00

- pass: 21/22 (95%), gate 90%
- AI tells: 0 (gate 0)
- latency p50/p95: 4934 ms / 9981 ms
- tokens per conversation (in/out): 5224 / 91
- R$ per conversation: n/a (no price configured)

| case | result | tools | tells | ms | tokens in/out | R$ | trace |
|---|---|---|---|---|---|---|---|
| catalogo_violoes | pass | search_products | - | 12349 | 6152/167 | n/a | 8478686cdc7b21a8d2c853f2127e56ba |
| endereco | pass | search_policies | - | 4976 | 6137/67 | n/a | a500d88900459efecad1e55110da66d2 |
| preco_takamine | pass | search_products | - | 5840 | 5449/98 | n/a | 322cfd952dd323fae137b6a3a0a5acd2 |
| pix | pass | search_products | - | 4794 | 5467/80 | n/a | e66f825dc8b80a259b24264bf75310c6 |
| arrependimento_anonimo | pass | search_policies | - | 6916 | 5844/117 | n/a | 5a5c1b01739f38b9680740066ca621ab |
| arrependimento_identificado | pass | check_return_eligibility, list_my_orders, search_policies | - | 9981 | 9178/160 | n/a | b6339a18b8e0d3d0a706b1c2d4ac9bba |
| acessorio | pass | - | - | 3782 | 2966/63 | n/a | fd27497ada415c9a59dbb7623d244a69 |
| fora_escopo | pass | - | - | 2683 | 2953/42 | n/a | d5fb46d7cf00fb32cf1bdb7033690e35 |
| parcelamento | pass | calc_installments | - | 4732 | 5396/79 | n/a | ebea5e4b21d79bc919736de75199b2f4 |
| pedido_ok | pass | get_order_status | - | 4539 | 5513/72 | n/a | 06797bbab00f964426451bb2d23cf7dc |
| pedido_identidade_errada | pass | get_order_status | - | 4892 | 5420/82 | n/a | 5b0ac2cf732a8617ebd67bd16684862a |
| promocoes | pass | list_active_promotions | - | 7772 | 5691/134 | n/a | 638e2286f370fdf76c56c7b3caaac60b |
| aberto_agora | pass | store_now | - | 2779 | 5417/41 | n/a | ce9cc33b7e8ebf991ab6e21231f370a4 |
| descontinuado | pass | recommend_products, search_products | - | 7075 | 8575/116 | n/a | e3b176fdfc4560a8fca0f67a05f3ffa1 |
| takamine_ambiguo | pass | search_products | - | 4587 | 5736/74 | n/a | e3f16464c6f7cfa733395b448ed3cafa |
| devolucao_fora_do_prazo | FAIL | check_return_eligibility, list_my_orders | - | 6385 | 5620/108 | n/a | d573151d5dde461ea3c061ad118c8521 |
| recomendacao_mpb | pass | recommend_products | - | 9434 | 5858/164 | n/a | d27c81d4a1ee3eaa992dd1d54c7b25cf |
| abuso | pass | - | - | 608 | 512/8 | n/a | 982affb39c2a8c5f4a111dbe5b1d6a9f |
| e_robo | pass | - | - | 4005 | 2902/69 | n/a | 2a10f32165545e7e991cffd5da5d26d0 |
| reclamacao | pass | list_my_orders | - | 7277 | 5473/125 | n/a | 0c179fd96f7f461dff69c16fda3fbb19 |
| promo_formato | pass | search_products | - | 6517 | 5469/113 | n/a | 5183a3123d90d3244cf86af7c069bdd6 |
| multi_turno | pass | - | - | 2384 | 3200/38 | n/a | 8c575604291f0b2b2f2ab7671af611bf |

## devolucao_fora_do_prazo

Customer: Quero devolver o pedido 5, me arrependi da compra.

- missing: @return_no

```
Oi, Rafael.
O prazo de 7 dias pra devolução por arrependimento e o de 30 dias pra troca por defeito já passaram.

Mas a garantia legal de 90 dias ainda pode valer pro seu instrumento.

Quer que eu passe o contato da equipe pra você resolver isso?
```
