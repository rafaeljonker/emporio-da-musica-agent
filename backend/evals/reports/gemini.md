# Agent eval: gemini (gemini-3.8-flash)
Run: 2026-11-06T20:59:33+00:00

- pass: 22/22 (100%), gate 90%
- AI tells: 0 (gate 0)
- latency p50/p95: 6105 ms / 8029 ms
- tokens per conversation (in/out): 6530 / 114
- R$ per conversation: R$ 0.0277

| case | result | tools | tells | ms | tokens in/out | R$ | trace |
|---|---|---|---|---|---|---|---|
| catalogo_violoes | pass | search_products | - | 7194 | 6873/198 | 0.0310 | fc7f8792dc2c56b379ed6da8b08ba330 |
| endereco | pass | search_policies | - | 5618 | 6912/106 | 0.0292 | fbe41ccce5e92328fb98abafa3e58e2b |
| preco_takamine | pass | get_product, search_products | - | 7347 | 9273/121 | 0.0363 | 57a5abb6ff631b81fabfd398ad969e0b |
| pix | pass | search_products | - | 7577 | 6244/113 | 0.0266 | 032b324efdefb04c83b8be26a312d24c |
| arrependimento_anonimo | pass | search_policies | - | 6626 | 6882/130 | 0.0296 | 987b8285572b85f2069506efb9cc686b |
| arrependimento_identificado | pass | check_return_eligibility, list_my_orders | - | 7457 | 9306/116 | 0.0393 | f924fbe7a914c62d498dd9171a9247ef |
| acessorio | pass | - | - | 3397 | 3349/75 | 0.0139 | 15154ce0d3e1d3cea44f33d94e094c70 |
| fora_escopo | pass | - | - | 2873 | 3336/60 | 0.0135 | cdf02d397239e3ca80481eac495a031d |
| parcelamento | pass | calc_installments | - | 4595 | 6186/68 | 0.0254 | 369033dabbc9d49459b6929409f2655e |
| pedido_ok | pass | get_order_status | - | 6482 | 6292/112 | 0.0268 | 40cf157bddc5e5f21c9930ab9810c299 |
| pedido_identidade_errada | pass | get_order_status | - | 5729 | 6210/130 | 0.0268 | 57e84ee7ab90bed48f4147ebf7280af2 |
| promocoes | pass | list_active_promotions | - | 8825 | 6442/202 | 0.0293 | 12942a4f42776ab4507ead4a618cfb4b |
| aberto_agora | pass | search_policies, store_now | - | 7681 | 9937/106 | 0.0417 | 62c94603c197cd0c89778e40c253ddb9 |
| descontinuado | pass | search_products, search_products | - | 6990 | 9590/169 | 0.0415 | 08765f1e7e9f01b3a1ff2079c7ea5bf4 |
| takamine_ambiguo | pass | search_products | - | 5442 | 6489/86 | 0.0271 | a80ae04f80657cdf62729f2a7af62a8b |
| devolucao_fora_do_prazo | pass | check_return_eligibility | - | 4686 | 6260/130 | 0.0270 | d9b0fcd16e62a207019f56eda52ac850 |
| recomendacao_mpb | pass | get_product, get_product, recommend_products | - | 7243 | 10133/199 | 0.0444 | 43a037e037dcca60ba4265a81a21df4b |
| abuso | pass | - | - | 1222 | 494/12 | 0.0008 | 7a5fb47bc1ea10991c85f79391e982dc |
| e_robo | pass | - | - | 5006 | 3285/84 | 0.0139 | 6554d19e03aa51d131f769c460d61480 |
| reclamacao | pass | get_order_status, list_my_orders, search_policies | - | 8029 | 10246/186 | 0.0446 | be4c5fe29d2142b03a16c57f45d844b8 |
| promo_formato | pass | search_products | - | 4559 | 6244/90 | 0.0262 | 857006d185c2efa194a3672a1e89b509 |
| multi_turno | pass | - | - | 2702 | 3683/27 | 0.0141 | dcbbc1c150286a19767edbd8d7f37b26 |
