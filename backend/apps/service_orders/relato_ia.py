"""Padronização do relato de uma OS via Claude (Anthropic).

Uma única chamada: texto bruto do técnico entra, relato no padrão da empresa
sai. Sem a chave configurada, `RelatoIAIndisponivel` é levantada e o app
continua funcionando normalmente (o relato bruto é o que vale).
"""

import logging

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

MAX_ENTRADA_CHARS = 6000

SYSTEM_PROMPT = """\
Você padroniza relatos de Ordem de Serviço da 3D Sistemas, uma empresa de \
infraestrutura predial (rede/TI, elétrica, eletrocalha, ar-condicionado, \
pneumática). O técnico escreve de forma corrida e informal o que fez; você \
reescreve no padrão da empresa.

REGRAS
- Não invente nada. Só use o que o técnico escreveu. Se algo está ambíguo, \
mantenha como está — não complete com suposições.
- Não remova serviços nem materiais. Pode reorganizar, agrupar itens iguais e \
somar quantidades.
- Corrija ortografia e gramática em português. Mantenha os termos técnicos do \
ramo (perfilado, eletrocalha, keystone, válvula pneumática, tomada steck, \
caixa Daisa, cabo PP, cabo singelo, lentilha/arruela/porca).
- Padronize unidades: "220v" -> "220V", "10 metros"/"10m" -> "10 m", \
"3x2,5mm" -> "3x2,5 mm².
- Não adicione comentários, saudações nem observações suas. Devolva só o relato.

FORMATO DE SAÍDA (use exatamente estes títulos; omita uma seção só se não \
houver nenhuma informação para ela):

Local: <local/área>

Serviços executados:
1. <serviço>
2. <serviço>

Materiais:
- <item> — <quantidade>
- <item> — <quantidade>

Equipe: <nomes separados por vírgula>

EXEMPLOS DE RELATOS JÁ NO PADRÃO DA EMPRESA

---
Local: Sala de químicos

Serviços executados:
1. Montagem de infraestrutura para instalação de forro

Equipe: Matheus, Fernando, Edison
---
Local: Gem BSUV

Serviços executados:
1. Instalação de infraestrutura para 3 pontos de rede TI
2. Instalação de infraestrutura para rede elétrica estabilizada 220V com 6 \
tomadas duplas vermelhas
3. Instalação de infraestrutura com 1 tomada steck 220V e válvula pneumática (x2)
4. Instalação de eletrocalha para iluminação das mesas
5. Passagem de cabo das luminárias

Materiais:
- Perfilado — 6
- Curva de perfilado — 4
- Emenda de perfilado — 10
- Pé de calha — 4
- Pé de perfilado — 3
- Tomada steck 220V — 2
- Lentilha, arruela e porca 11 — 20
- Lentilha, arruela e porca 13 — 40
- Cabo PP 3x2,5 mm² — 10 m
- Cabo singelo preto — 15 m
- Cabo singelo azul — 15 m
- Caixa Daisa — 10
- Tampa Daisa para tomada dupla — 10
- Tomada dupla vermelha — 10
- Keystone — 3

Equipe: William, Bryan, Matheus, Edison
---
Local: IP04

Serviços executados:
1. Instalação de infraestrutura (movimentação) com 1 tomada steck 220V e 1 \
válvula pneumática cada — 5 pontos
2. Instalação de infraestrutura (movimentação) com 2 tomadas steck 220V e 2 \
válvulas pneumáticas — 1 ponto

Materiais:
- Curva de perfilado — 2
- Emenda de perfilado — 2
- Válvula pneumática — 2
- Cabo PP 3x2,5 mm² — 35 m
- Mangueira pneumática — 15 m

Equipe: William, Bryan, Matheus, Gabriel, Fernando, Mário, Edison
---
"""

USER_TEMPLATE = "Padronize este relato:\n\n{texto}"


class RelatoIAIndisponivel(Exception):
    """IA não configurada ou o provedor falhou."""


def _cliente_e_modelo():
    """Monta o client conforme RELATO_IA_PROVEDOR: 'anthropic' (chave direta)
    ou 'bedrock' (AWS, cobrado na fatura da AWS)."""
    provedor = (settings.RELATO_IA_PROVEDOR or "anthropic").lower()

    if provedor == "bedrock":
        if not settings.AWS_BEDROCK_REGION:
            raise RelatoIAIndisponivel(
                "Bedrock não configurado (falta AWS_BEDROCK_REGION)."
            )
        # As credenciais AWS vêm do ambiente (AWS_ACCESS_KEY_ID /
        # AWS_SECRET_ACCESS_KEY no .env, ou a IAM role do servidor).
        client = anthropic.AnthropicBedrockMantle(aws_region=settings.AWS_BEDROCK_REGION)
        modelo = settings.RELATO_IA_MODELO or "anthropic.claude-haiku-4-5"
        return client, modelo

    if not settings.ANTHROPIC_API_KEY:
        raise RelatoIAIndisponivel(
            "Padronização por IA não está configurada (falta ANTHROPIC_API_KEY)."
        )
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    modelo = settings.RELATO_IA_MODELO or "claude-haiku-4-5"
    return client, modelo


def padronizar_relato(texto_bruto: str) -> str:
    texto_bruto = (texto_bruto or "").strip()
    if not texto_bruto:
        raise RelatoIAIndisponivel("Nada para padronizar.")

    client, modelo = _cliente_e_modelo()

    try:
        resposta = client.messages.create(
            model=modelo,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": USER_TEMPLATE.format(
                        texto=texto_bruto[:MAX_ENTRADA_CHARS]
                    ),
                }
            ],
        )
    except anthropic.APIError as exc:
        logger.error("Falha ao padronizar relato (provedor=%s): %s",
                     settings.RELATO_IA_PROVEDOR, exc)
        raise RelatoIAIndisponivel(
            "A padronização automática está indisponível no momento. "
            "Tente novamente mais tarde."
        ) from exc

    if resposta.stop_reason == "refusal":
        raise RelatoIAIndisponivel("A IA recusou processar este texto.")

    texto = "".join(
        bloco.text for bloco in resposta.content if bloco.type == "text"
    ).strip()

    if not texto:
        raise RelatoIAIndisponivel("A IA não retornou texto.")

    return texto
