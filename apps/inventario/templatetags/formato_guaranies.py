from django import template

register = template.Library()


@register.filter
def gs(value):
    """Formats a monetary value as Paraguayan Guaranies: Gs. 1.250.000
    Handles negative values as: −Gs. 1.250.000
    """
    try:
        n = int(value)
        abs_n = abs(n)
        formatted = f'{abs_n:,}'.replace(',', '.')
        if n < 0:
            return f'\u2212Gs. {formatted}'
        return f'Gs. {formatted}'
    except (ValueError, TypeError):
        return value
