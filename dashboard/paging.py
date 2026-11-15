from django.core.paginator import Paginator

PAGE_SIZE = 8


def paginate(request, items, key="page", per_page=PAGE_SIZE):
    paginator = Paginator(items, per_page)
    return paginator.get_page(request.GET.get(key) or 1)
