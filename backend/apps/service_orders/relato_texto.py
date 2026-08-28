"""Renderiza o relato estruturado da OS no formato padrão da empresa."""


def _linha_material(item):
    descricao = (item.get("descricao") or "").strip()
    if not descricao:
        return None
    quantidade = str(item.get("quantidade") or "").strip()
    unidade = (item.get("unidade") or "").strip()
    qtd = " ".join(p for p in (quantidade, unidade) if p)
    return f"- {descricao} — {qtd}" if qtd else f"- {descricao}"


def montar_relato_texto(relato: dict) -> str:
    relato = relato or {}
    blocos = []

    local = (relato.get("local") or "").strip()
    if local:
        blocos.append(f"Local: {local}")

    servicos = [s.strip() for s in relato.get("servicos", []) if s and s.strip()]
    if servicos:
        linhas = "\n".join(f"{i}. {s}" for i, s in enumerate(servicos, 1))
        blocos.append(f"Serviços executados:\n{linhas}")

    materiais = [
        linha
        for linha in (_linha_material(m) for m in relato.get("materiais", []))
        if linha
    ]
    if materiais:
        blocos.append("Materiais:\n" + "\n".join(materiais))

    equipe = [p.strip() for p in relato.get("equipe", []) if p and p.strip()]
    if equipe:
        blocos.append("Equipe: " + ", ".join(equipe))

    observacoes = (relato.get("observacoes") or "").strip()
    if observacoes:
        blocos.append(f"Observações: {observacoes}")

    return "\n\n".join(blocos)
