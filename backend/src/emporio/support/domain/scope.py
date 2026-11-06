from enum import StrEnum


class Scope(StrEnum):
    LOJA = "loja"
    ACESSORIO = "acessorio"
    FORA_DE_ESCOPO = "fora_de_escopo"
    ABUSO = "abuso"
