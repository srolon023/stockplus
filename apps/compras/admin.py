from django.contrib import admin
from .models import Proveedor, Compra, ItemCompra, AdicionalCompra


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ruc', 'telefono', 'activo']
    list_editable = ['activo']
    search_fields = ['nombre', 'ruc']


class ItemCompraInline(admin.TabularInline):
    model = ItemCompra
    extra = 1
    fields = ['producto', 'cantidad', 'precio_unitario', 'observacion']


class AdicionalCompraInline(admin.TabularInline):
    model = AdicionalCompra
    extra = 1
    fields = ['concepto', 'descripcion', 'monto', 'comprobante']


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ['numero', 'fecha', 'proveedor', 'estado', 'total']
    list_filter = ['estado', 'moneda']
    search_fields = ['numero', 'nro_factura']
    readonly_fields = ['creado_en', 'actualizado_en']
    inlines = [ItemCompraInline, AdicionalCompraInline]
