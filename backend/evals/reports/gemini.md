# Agent eval: gemini (gemini-3.8-flash)
Run: 2026-11-07T19:34:17+00:00

- pass: 22/22 (100%), gate 90%
- AI tells: 0 (gate 0)
- latency p50/p95: 5518 ms / 9736 ms
- tokens per conversation (in/out): 6878 / 109
- R$ per conversation: R$ 0.0292

| case | result | tools | tells | ms | tokens in/out | R$ | trace |
|---|---|---|---|---|---|---|---|
| catalogo_violoes | pass | search_products | - | 6788 | 6965/205 | 0.0314 | b0b2ddb3c6c36db99936402fcba51a9b |
| endereco | pass | search_policies | - | 5615 | 7002/104 | 0.0295 | 01be662ae62ba369d638bb32feb3e176 |
| preco_takamine | pass | calc_installments, get_product, search_products | - | 11807 | 12550/145 | 0.0533 | f30ca9a68d74b687bc008766c97a5a7e |
| pix | pass | get_product, search_products | - | 6862 | 9435/104 | 0.0396 | f24538c9aeefa0f09ce0a77e6cb9fbb1 |
| arrependimento_anonimo | pass | search_policies | - | 5422 | 6952/133 | 0.0299 | 6bd77e71124ec92aaa873e5cc7daa339 |
| arrependimento_identificado | pass | check_return_eligibility, list_my_orders, search_policies | - | 9736 | 13247/163 | 0.0565 | 991c95c9add4713204efa4a5145c4e59 |
| acessorio | pass | - | - | 3531 | 3395/69 | 0.0140 | 95203edc84c10acbc62e5568baa64fe4 |
| fora_escopo | pass | - | - | 2928 | 3382/57 | 0.0136 | 89c87281929ad3910956b7abccf69ceb |
| parcelamento | pass | calc_installments | - | 5701 | 6278/68 | 0.0258 | 71369ea2b7ff0fa254fccc4e6960b3ca |
| pedido_ok | pass | get_order_status | - | 6142 | 6384/99 | 0.0269 | 45b29cb3f7ff18a1faf89484246267f7 |
| pedido_identidade_errada | pass | get_order_status | - | 5258 | 6302/129 | 0.0271 | 7c3603c489bb88db32d9ec9128be10ba |
| promocoes | pass | list_active_promotions | - | 5341 | 6534/203 | 0.0297 | 3555c10faa9da3af1f20b9a15b6dfd8b |
| aberto_agora | pass | store_now | - | 4506 | 6286/50 | 0.0255 | 68fe8b6b9aa6e90dba4f6ad6f0919aff |
| descontinuado | pass | search_products, search_products | - | 6398 | 9728/130 | 0.0413 | 35e4e8b99ce45e8ca02e1b7af2afd1f0 |
| takamine_ambiguo | pass | search_products | - | 4996 | 6581/66 | 0.0270 | af955349c454911910b1a3cf8c8d206d |
| devolucao_fora_do_prazo | pass | check_return_eligibility | - | 4915 | 6352/127 | 0.0273 | 37f30f1ca9159d6eec4357e820c25e55 |
| recomendacao_mpb | pass | recommend_products, search_products | - | 7532 | 10783/183 | 0.0468 | 566984631342f8ae4c649a3a53084b62 |
| abuso | pass | - | - | 1239 | 494/12 | 0.0008 | d22a1ee78faaaeff486f9cf94d15b069 |
| e_robo | pass | - | - | 3407 | 3331/79 | 0.0140 | 3493c34eed8cc9a330f3dab849340246 |
| reclamacao | pass | list_my_orders | - | 5697 | 6345/156 | 0.0279 | f29448a1ad6e2b055522bbc2379571a6 |
| promo_formato | pass | get_product, search_products | - | 7629 | 9421/111 | 0.0397 | 10fc41f7d1b443a994a19ee0e029ddf1 |
| multi_turno | pass | - | - | 2846 | 3586/26 | 0.0137 | a95011a682f1e27a3485b0154deba5a2 |
