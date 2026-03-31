from django.contrib import admin
from .models import Cliente, Venta, ItemVenta, AdicionalVenta


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'telefono', 'email']
    search_fields = ['nombre', 'telefono']


class ItemVentaInline(admin.TabularInline):
    model = ItemVenta
    extra = 1
    fields = ['producto', 'cantidad', 'precio_unitario', 'descuento', 'observacion']


class AdicionalVentaInline(admin.TabularInline):
    model = AdicionalVenta
    extra = 1
    fields = ['concepto', 'descripcion', 'monto', 'a_cargo_de', 'comprobante']


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'fecha', 'cliente_nombre', 'canal', 'estado', 'total']
    list_filter = ['estado', 'canal']
    search_fields = ['numero', 'cliente_nombre', 'cliente_telefono']
    readonly_fields = ['creado_en', 'actualizado_en']
    inlines = [ItemVentaInline, AdicionalVentaInline]
