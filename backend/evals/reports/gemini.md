# Agent eval: gemini (gemini-3.8-flash)
Run: 2026-11-06T19:02:23+00:00

- pass: 21/22 (95%), gate 90%
- AI tells: 0 (gate 0)
- latency p50/p95: 7301 ms / 11372 ms
- tokens per conversation (in/out): 6554 / 184
- R$ per conversation: R$ 0.0307

| case | result | tools | tells | ms | tokens in/out | R$ | trace |
|---|---|---|---|---|---|---|---|
| catalogo_violoes | pass | search_products | - | 6527 | 6569/135 | 0.0267 | 2cb8d42ccf1e722cca52ff6dcaa7642d |
| endereco | pass | search_policies | - | 17882 | 6607/79 | 0.0289 | 2e4a54246d6ef18ace0a85c05b62b818 |
| preco_takamine | pass | get_product, search_products | - | 8367 | 8817/123 | 0.0389 | 3d4730bed86aaee38bebb5b44e7be622 |
| pix | pass | search_products | - | 5241 | 5940/116 | 0.0269 | a83dbf36f59a0efc95e1989c949dbda3 |
| arrependimento_anonimo | pass | search_policies | - | 6224 | 6579/134 | 0.0299 | 0ce9ca70ba9982ccd3c33e1d324a4ba8 |
| arrependimento_identificado | pass | check_return_eligibility, list_my_orders, search_policies | - | 11372 | 12449/201 | 0.0555 | f3d4ec79b2bf7d29f6823bfdc6eac1ae |
| acessorio | pass | - | - | 3555 | 3197/76 | 0.0148 | 4dd6b9dfbee9b4edfa4db493ec41a6e7 |
| fora_escopo | pass | - | - | 3146 | 3184/41 | 0.0140 | 89aa8177e31008604ddde77948469907 |
| parcelamento | pass | calc_installments | - | 10979 | 5996/693 | 0.0390 | 14bf0f69da87dc580724e310020dd0b4 |
| pedido_ok | pass | get_order_status | - | 6245 | 5988/93 | 0.0266 | 330d491d86f17dfba0698b35efa30d01 |
| pedido_identidade_errada | pass | get_order_status | - | 5021 | 5906/95 | 0.0263 | 27242267518d492bd4d478468b7eb079 |
| promocoes | pass | list_active_promotions | - | 7414 | 6138/200 | 0.0294 | 0b61bcd761390cefd1f718435a74ed7a |
| aberto_agora | pass | search_policies, store_now | - | 10831 | 9798/631 | 0.0534 | 75376da450cf773d1ae56272f5d6d3f6 |
| descontinuado | pass | search_products, search_products | - | 8940 | 9134/148 | 0.0407 | e2ac5d8305966e243895def817d70d5c |
| takamine_ambiguo | pass | search_products | - | 9506 | 6294/515 | 0.0366 | 379d41e89f80b04190c9977cf0cbd29b |
| devolucao_fora_do_prazo | pass | check_return_eligibility | - | 7836 | 5956/154 | 0.0277 | d5956359a7a46cab652aa8450e33f335 |
| recomendacao_mpb | FAIL | recommend_products, search_products | - | 9084 | 10198/179 | 0.0458 | ce9b386026432f7c1bb45611a43f2ba7 |
| abuso | pass | - | - | 1207 | 494/12 | 0.0023 | 0d5f9411206d8db1bde5b326193e55de |
| e_robo | pass | - | - | 3384 | 3133/86 | 0.0147 | 7a550387eaa3b4215b13a8bc1e2f88f0 |
| reclamacao | pass | list_my_orders, search_policies | - | 9120 | 9471/172 | 0.0426 | f450b1e7a715f532047ed66dcc29d2a0 |
| promo_formato | pass | get_product, search_products | - | 7189 | 8827/131 | 0.0391 | ca22902a91e499273eba5c042f70a83c |
| multi_turno | pass | - | - | 4595 | 3534/40 | 0.0154 | da278737843f20c0771abf7915912338 |

## recomendacao_mpb

Customer: Queria algo pra tocar MPB em casa

- none of: Music Man, Giannini GWNE-7, Ohana BK-35E, Takamine GC5CE, Fender Telecaster

```
Pra MPB em casa, violão de nylon é a escolha clássica, com som macio e pegada bem confortável pra dedilhar

O Yamaha C40 sai R$ 599,90, ou R$ 569,91 no PIX, e tem uma afinação excelente pro dia a dia. Se preferir um acabamento um pouco mais refinado e timbre mais encorpado, o Yamaha C70 sai R$ 849, ou R$ 806,55 no PIX

Você já toca ou tá começando agora?
```
