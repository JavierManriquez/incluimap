from django import template

register = template.Library()

@register.simple_tag
def star_row(value, max_stars=5):
    """Devuelve max_stars estrellas, rellenas según 'value'."""
    try:
        v = int(value)
    except Exception:
        v = 0
    v = max(0, min(v, max_stars))
    filled = "★" * v
    empty = "☆" * (max_stars - v)
    return f"{filled}{empty}"

@register.filter
def split_tags(s):
    """Converte 'rampa,bano' -> ['rampa','bano']"""
    if not s:
        return []
    return [x.strip() for x in str(s).split(',') if x.strip()]
