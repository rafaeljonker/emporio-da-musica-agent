# Agent eval: gemini (gemini-3.8-flash)
Run: 2026-11-07T18:59:45+00:00

- pass: 22/22 (100%), gate 90%
- AI tells: 0 (gate 0)
- latency p50/p95: 5910 ms / 13578 ms
- tokens per conversation (in/out): 7224 / 111
- R$ per conversation: R$ 0.0299

| case | result | tools | tells | ms | tokens in/out | R$ | trace |
|---|---|---|---|---|---|---|---|
| catalogo_violoes | pass | search_products | - | 7536 | 6873/204 | 0.0310 | 7f9602fb3494d795f6429aeb340ade66 |
| endereco | pass | search_policies | - | 7194 | 6910/84 | 0.0288 | d36ae97e8cb407b872553e3abad74947 |
| preco_takamine | pass | get_product, search_products | - | 7670 | 9273/110 | 0.0390 | 192283027ac378b176682c899be01482 |
| pix | pass | search_products | - | 5394 | 6244/84 | 0.0260 | 3eab682a371cae6dd66737e97630a025 |
| arrependimento_anonimo | pass | search_policies | - | 5702 | 6804/131 | 0.0293 | 5b16282eef5bbbf310e60cb75765633e |
| arrependimento_identificado | pass | check_return_eligibility, list_my_orders, search_policies | - | 9108 | 13078/169 | 0.0560 | 6bfe134adac1b9f03f3b4f5d2b2e06d3 |
| acessorio | pass | - | - | 16234 | 3349/73 | 0.0139 | f3d7b728ae16ba4e19430cb43adea6ac |
| fora_escopo | pass | - | - | 2786 | 3336/66 | 0.0136 | d37bb3bb57b506266e7c1009199469ba |
| parcelamento | pass | calc_installments | - | 4862 | 6186/68 | 0.0254 | 80d12a272047052393fb7405cd823b89 |
| pedido_ok | pass | get_order_status | - | 5298 | 6292/114 | 0.0268 | 43f191d08b40d8e589cd99baff8a7a9e |
| pedido_identidade_errada | pass | get_order_status | - | 4431 | 6210/96 | 0.0261 | 63e099f52e7ab1b15d722a7bd772e613 |
| promocoes | pass | list_active_promotions | - | 5406 | 6442/199 | 0.0292 | 2d2b285bb556c0ec03c2684e8687f730 |
| aberto_agora | pass | store_now | - | 4412 | 6194/46 | 0.0250 | a8ac9f2d402f0e0e437cabd3cd574a08 |
| descontinuado | pass | search_products, search_products | - | 6119 | 9590/138 | 0.0409 | 2bc7ce21fdf0179e9f95f49b6cada2ec |
| takamine_ambiguo | pass | search_products | - | 7129 | 6489/81 | 0.0270 | f9806e7b677d6e461a75f19bae229208 |
| devolucao_fora_do_prazo | pass | check_return_eligibility, search_policies | - | 8630 | 9948/183 | 0.0433 | d1e68b130ac527932f63f294974210ea |
| recomendacao_mpb | pass | get_product, get_product, recommend_products, search_products | - | 13578 | 19099/185 | 0.0655 | fd0c0c5a61223cb6d50c278801b44ef6 |
| abuso | pass | - | - | 1102 | 494/12 | 0.0008 | 9ee99d2572f12478b6faf6d48f949aea |
| e_robo | pass | - | - | 3078 | 3285/87 | 0.0139 | 772323398984bf9705c45e7b76f54c3a |
| reclamacao | pass | get_order_status, search_policies | - | 7477 | 9885/177 | 0.0429 | 58f7c9c710c4242d9154c5140fcec042 |
| promo_formato | pass | get_product, search_products | - | 6803 | 9291/113 | 0.0391 | 93c9c7771900df9004e86041a9b4eb7d |
| multi_turno | pass | - | - | 2966 | 3669/36 | 0.0142 | 1673729431cbc0e0fa96aaea85489d59 |
