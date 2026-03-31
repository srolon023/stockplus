from django.contrib import admin
from .models import Movimiento


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'tipo', 'descripcion', 'monto', 'creado_por']
    list_filter = ['tipo', 'fecha']
    search_fields = ['descripcion']
    date_hierarchy = 'fecha'
