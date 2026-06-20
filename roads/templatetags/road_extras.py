from django import template

register = template.Library()


@register.filter(name='get_item')
def get_item(dictionary, key):
    if dictionary is None:
        return ''
    return dictionary.get(key, '')


@register.filter(name='get_hazard_level_color')
def get_hazard_level_color(level):
    colors = {
        'safe': '#28a745',
        'info': '#17a2b8',
        'warning': '#ffc107',
        'severe': '#fd7e14',
        'critical': '#dc3545',
    }
    return colors.get(level, '#6c757d')


@register.filter(name='get_passage_color')
def get_passage_color(status):
    colors = {
        'normal': '#28a745',
        'caution': '#ffc107',
        'restricted': '#fd7e14',
        'detour': '#6f42c1',
        'closed': '#dc3545',
    }
    return colors.get(status, '#6c757d')
