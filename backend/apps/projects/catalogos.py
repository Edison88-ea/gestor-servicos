"""Listas fixas usadas pelo módulo de Obras. Ficam em código (não no banco) de
propósito: são vocabulário da fábrica que muda muito raramente, e o formulário
do front busca tudo de uma vez em `GET /api/projetos/opcoes`."""

# Áreas afetadas do "Termo de Mudança de Layout" (os checkboxes do documento).
# (codigo, rotulo)
AREAS_AFETADAS = [
    ("DM", "DM"),
    ("CMI", "CMI"),
    ("VOLKS", "Volks"),
    ("ADM", "ADM"),
    ("MANUTENCAO", "Manutenção"),
    ("ONIX", "Onix"),
    ("VS30", "VS30"),
    ("PATIO", "Pátio"),
    ("LEAD_PREP", "Lead Prep"),
    ("FIAT", "Fiat"),
    ("GLM", "GLM"),
    ("BU", "BU"),
    ("LOGISTICA", "Logística"),
]

AREAS_AFETADAS_VALIDAS = {codigo for codigo, _ in AREAS_AFETADAS}
