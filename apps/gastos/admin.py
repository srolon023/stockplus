from django.contrib import admin
from .models import ConceptoAdicional, GastoGeneral


@admin.register(ConceptoAdicional)
class ConceptoAdicionalAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'aplica_a', 'activo']
    list_filter = ['tipo', 'aplica_a', 'activo']
    list_editable = ['activo']


@admin.register(GastoGeneral)
class GastoGeneralAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'concepto', 'descripcion', 'monto', 'comprobante']
    list_filter = ['concepto']
    search_fields = ['descripcion', 'comprobante']
    readonly_fields = ['creado_en']
