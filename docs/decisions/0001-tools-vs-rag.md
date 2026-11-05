# 0001. Dado estruturado via tools, texto de política via RAG

## Contexto

A loja tem dados estruturados (preço, estoque, pedidos, promoções, em CSVs) e um manual de políticas em texto livre (PDF, cerca de 20 seções). A própria política diz: "nunca fornecer informações sobre preços, estoque ou prazos sem consultar o sistema". Consultas exatas não podem ser busca semântica aproximada.

## Decisão

Dados estruturados são respondidos por tools determinísticas que consultam os CSVs. Apenas o manual de políticas passa por RAG (pgvector).

## Consequências

- As tools são tipadas e testadas.
- O escopo do RAG fica pequeno.
- A porta `PolicyIndex` permite trocar o vector store no futuro.
