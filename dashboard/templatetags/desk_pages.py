from django import template

register = template.Library()


@register.inclusion_tag("dashboard/_pager.html", takes_context=True)
def pager(context, page_obj, param="page"):
    request = context["request"]

    def link(number):
        query = request.GET.copy()
        query[param] = number
        return query.urlencode()

    return {
        "page_obj": page_obj,
        "previous": link(page_obj.previous_page_number) if page_obj.has_previous else "",
        "next": link(page_obj.next_page_number) if page_obj.has_next else "",
    }
