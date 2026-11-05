from datetime import date

# Sources: national = Lei 662/1949 + Lei 10.607/2002 (+ Lei 14.759/2023 for 20/11);
# Good Friday = Christian movable holiday (Easter 2025-04-20, 2026-04-05);
# MS state = state law for 11/10; Campo Grande = municipal.
# Carnaval and Corpus Christi are ponto facultativo (optional), so left out on purpose.
# Weekend entries are kept: they are real holidays and harmless.
STORE_HOLIDAYS: frozenset[date] = frozenset(
    {
        # 2025
        date(2025, 1, 1),  # Confraternização Universal (Lei 10.607/2002)
        date(2025, 4, 18),  # Sexta-feira Santa (Easter 2025-04-20)
        date(2025, 4, 21),  # Tiradentes (Lei 662/1949)
        date(2025, 5, 1),  # Dia do Trabalho (Lei 662/1949)
        date(2025, 8, 26),  # Campo Grande anniversary  # unconfirmed
        date(2025, 9, 7),  # Independência (Lei 662/1949)
        date(2025, 10, 11),  # Criação do Estado de MS (state law)
        date(2025, 10, 12),  # N. Sra. Aparecida (Lei 6.802/1980)
        date(2025, 11, 2),  # Finados (Lei 10.607/2002)
        date(2025, 11, 15),  # Proclamação da República (Lei 662/1949)
        date(2025, 11, 20),  # Consciência Negra (Lei 14.759/2023)
        date(2025, 12, 25),  # Natal (Lei 662/1949)
        # 2026
        date(2026, 1, 1),  # Confraternização Universal (Lei 10.607/2002)
        date(2026, 4, 3),  # Sexta-feira Santa (Easter 2026-04-05)
        date(2026, 4, 21),  # Tiradentes (Lei 662/1949)
        date(2026, 5, 1),  # Dia do Trabalho (Lei 662/1949)
        date(2026, 8, 26),  # Campo Grande anniversary  # unconfirmed
        date(2026, 9, 7),  # Independência (Lei 662/1949)
        date(2026, 10, 11),  # Criação do Estado de MS (state law)
        date(2026, 10, 12),  # N. Sra. Aparecida (Lei 6.802/1980)
        date(2026, 11, 2),  # Finados (Lei 10.607/2002)
        date(2026, 11, 15),  # Proclamação da República (Lei 662/1949)
        date(2026, 11, 20),  # Consciência Negra (Lei 14.759/2023)
        date(2026, 12, 25),  # Natal (Lei 662/1949)
    }
)
