from django.contrib import admin
from .models import ProductoWeb, PromoWeb, ItemPromoWeb, PedidoWeb


@admin.register(ProductoWeb)
class ProductoWebAdmin(admin.ModelAdmin):
    list_display = ['producto', 'titulo_display', 'precio_web', 'visible', 'destacado', 'orden']
    list_filter = ['visible', 'destacado']
    list_editable = ['visible', 'destacado', 'orden']
    search_fields = ['producto__codigo', 'producto__nombre', 'titulo_web']


class ItemPromoWebInline(admin.TabularInline):
    model = ItemPromoWeb
    extra = 1
    fields = ['producto', 'cantidad']


@admin.register(PromoWeb)
class PromoWebAdmin(admin.ModelAdmin):
    list_display = ['id_promo', 'nombre', 'precio', 'visible', 'destacada']
    list_editable = ['visible', 'destacada']
    inlines = [ItemPromoWebInline]


@admin.register(PedidoWeb)
class PedidoWebAdmin(admin.ModelAdmin):
    list_display = ['id_pedido', 'fecha', 'cliente_nombre', 'cliente_telefono',
                    'estado', 'total']
    list_filter = ['estado', 'tipo_pedido']
    search_fields = ['id_pedido', 'cliente_nombre', 'cliente_telefono']
    readonly_fields = ['id_pedido', 'fecha', 'whatsapp_url']
