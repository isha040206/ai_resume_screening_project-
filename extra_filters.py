from django import template
register = template.Library()

@register.filter
def trim(value):
    return value.strip() if isinstance(value, str) else value

@register.filter
def split(value, arg=','):
    return [v.strip() for v in value.split(arg)]
