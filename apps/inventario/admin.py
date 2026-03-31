from django.contrib import admin
from .models import CategoriaProducto, Producto, StockActual, MovimientoStock


@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo']
    list_editable = ['activo']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'modelo_celular', 'color',
                    'precio_venta', 'stock_disponible', 'activo']
    list_filter = ['activo', 'categoria']
    search_fields = ['codigo', 'nombre', 'modelo_celular', 'color']
    list_editable = ['activo']
    readonly_fields = ['creado_en', 'actualizado_en']


@admin.register(StockActual)
class StockActualAdmin(admin.ModelAdmin):
    list_display = ['producto', 'cantidad', 'ultima_compra', 'ultima_venta']
    search_fields = ['producto__codigo', 'producto__nombre']


@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ['producto', 'tipo', 'cantidad', 'stock_anterior',
                    'stock_posterior', 'creado_en']
    list_filter = ['tipo']
    search_fields = ['producto__codigo']
    readonly_fields = ['creado_en']
