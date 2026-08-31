"""Importa os dados do gestor_obras legado (PythonAnywhere) para o app projects.

Uso:
    python manage.py importar_obras_legado obras_legado.json \
        [--media CAMINHO_DA_PASTA_MEDIA] [--usuario USERNAME] [--limpar]

- `obras_legado.json` é a saída de `python manage.py dumpdata core` no sistema
  antigo (models core.projeto / core.etapa / core.historicoetapa).
- `--media` aponta para a pasta `media/` do sistema antigo; sem ela, as fotos
  das etapas são puladas (o comando lista quais).
- `--usuario` atribui todo o histórico a esse usuário (o dump legado não traz os
  usuários); sem ela, o histórico fica sem autor.
- `--limpar` apaga todos os Projeto existentes antes de importar.
"""

import json
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime

from apps.accounts.models import Usuario
from apps.projects.models import Etapa, FotoEtapa, HistoricoEtapa, Projeto


class Command(BaseCommand):
    help = "Importa projetos/etapas/histórico do gestor_obras legado."

    def add_arguments(self, parser):
        parser.add_argument("arquivo", type=str)
        parser.add_argument("--media", type=str, default="")
        parser.add_argument("--usuario", type=str, default="")
        parser.add_argument("--limpar", action="store_true")

    def handle(self, *args, **opts):
        caminho = Path(opts["arquivo"])
        if not caminho.exists():
            raise CommandError(f"Arquivo não encontrado: {caminho}")

        registros = json.loads(caminho.read_text(encoding="utf-8"))
        por_modelo = {"core.projeto": [], "core.etapa": [], "core.historicoetapa": []}
        for r in registros:
            if r["model"] in por_modelo:
                por_modelo[r["model"]].append(r)

        media_dir = Path(opts["media"]) if opts["media"] else None
        if media_dir and not media_dir.is_dir():
            raise CommandError(f"Pasta de mídia inválida: {media_dir}")

        autor = None
        if opts["usuario"]:
            try:
                autor = Usuario.objects.get(username=opts["usuario"])
            except Usuario.DoesNotExist:
                raise CommandError(f"Usuário '{opts['usuario']}' não existe.")

        with transaction.atomic():
            if opts["limpar"]:
                apagados, _ = Projeto.objects.all().delete()
                self.stdout.write(f"Removidos {apagados} registros antigos.")

            mapa_projeto = self._importar_projetos(por_modelo["core.projeto"])
            mapa_etapa, fotos_puladas = self._importar_etapas(
                por_modelo["core.etapa"], mapa_projeto, media_dir
            )
            n_hist = self._importar_historico(
                por_modelo["core.historicoetapa"], mapa_etapa, autor
            )
            self._ajustar_status(mapa_projeto.values())

        self.stdout.write(
            self.style.SUCCESS(
                f"OK: {len(mapa_projeto)} projetos, {len(mapa_etapa)} etapas, {n_hist} históricos."
            )
        )
        if fotos_puladas:
            self.stdout.write(
                self.style.WARNING(
                    "Fotos não importadas (arquivo ausente):\n  - "
                    + "\n  - ".join(fotos_puladas)
                )
            )

    def _importar_projetos(self, registros):
        mapa = {}
        for r in registros:
            f = r["fields"]
            projeto = Projeto.objects.create(
                nome=f["nome"],
                descricao=f.get("descricao", ""),
                tipo=Projeto.Tipo.MUDANCA_LAYOUT,
                data_mudanca=f.get("data_inicio") or None,
            )
            mapa[r["pk"]] = projeto
        return mapa

    def _importar_etapas(self, registros, mapa_projeto, media_dir):
        mapa = {}
        fotos_puladas = []
        for ordem, r in enumerate(registros):
            f = r["fields"]
            projeto = mapa_projeto.get(f["projeto"])
            if projeto is None:
                continue
            etapa = Etapa.objects.create(
                projeto=projeto,
                nome=f["nome"],
                meta=f.get("meta") or 1,
                realizado=f.get("realizado") or 0,
                ordem=ordem,
            )
            mapa[r["pk"]] = etapa

            foto = (f.get("foto") or "").strip()
            if foto:
                if media_dir and (media_dir / foto).is_file():
                    caminho = media_dir / foto
                    with caminho.open("rb") as fh:
                        FotoEtapa.objects.create(
                            etapa=etapa,
                            imagem=File(fh, name=caminho.name),
                            legenda="Importado do sistema anterior",
                        )
                else:
                    fotos_puladas.append(f"etapa {r['pk']} -> {foto}")
        return mapa, fotos_puladas

    def _importar_historico(self, registros, mapa_etapa, autor):
        n = 0
        for r in registros:
            f = r["fields"]
            etapa = mapa_etapa.get(f["etapa"])
            if etapa is None:
                continue
            hist = HistoricoEtapa.objects.create(
                etapa=etapa,
                usuario=autor,
                quantidade_anterior=f["quantidade_anterior"],
                quantidade_nova=f["quantidade_nova"],
                observacao="Importado do sistema anterior",
            )
            # 'data' é auto_now_add; .update() ignora isso e preserva a data real.
            quando = parse_datetime(f["data"]) if f.get("data") else None
            if quando:
                HistoricoEtapa.objects.filter(pk=hist.pk).update(data=quando)
            n += 1
        return n

    def _ajustar_status(self, projetos):
        for projeto in projetos:
            pct = projeto.progresso
            if pct >= 100 and projeto.total_meta:
                projeto.status = Projeto.Status.CONCLUIDO
            elif pct > 0:
                projeto.status = Projeto.Status.EM_ANDAMENTO
            else:
                projeto.status = Projeto.Status.PLANEJADO
            projeto.save(update_fields=["status"])
