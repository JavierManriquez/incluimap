from django import template
register = template.Library()

@register.simple_tag(takes_context=True)
def active(context, url_name):
    try:
        current = context['request'].resolver_match.url_name
    except Exception:
        return ''
    return 'is-active' if current == url_name else ''