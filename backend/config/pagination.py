from rest_framework.pagination import PageNumberPagination


class PadraoPagination(PageNumberPagination):
    """Paginação padrão do projeto: 20 por página, mas o cliente pode pedir mais
    com ?page_size= (até 500) — usado, por exemplo, pelo Painel do Gestor para
    listar todas as OS concluídas de um mês de uma vez."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 500
