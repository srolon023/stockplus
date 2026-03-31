from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Case, When, Value, IntegerField
from django.db.models.functions import Coalesce
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils import timezone
from urllib.parse import quote

from .models import ProductoWeb, PromoWeb, PedidoWeb
from apps.inventario.models import Producto, StockActual, MovimientoStock
from apps.ventas.models import Venta, ItemVenta


# ── Backend de gestión ────────────────────────────────────────────────────────

@login_required
def index(request):
    tab = request.GET.get('tab', 'catalogo')
    ver_cancelados = request.GET.get('ver_cancelados') == '1'

    # Auto-ocultar en la tienda los productos publicados con stock 0
    ProductoWeb.objects.filter(
        visible=True,
        producto__stock__cantidad__lte=0
    ).update(visible=False)

    productos = (Producto.objects
                 .filter(activo=True)
                 .select_related('producto_web', 'categoria', 'stock')
                 .annotate(qty_stock=Coalesce('stock__cantidad', Value(0)))
                 .order_by(
                     Case(
                         When(qty_stock__lte=0, then=Value(1)),
                         default=Value(0),
                         output_field=IntegerField(),
                     ),
                     'nombre',
                 ))

    promos = PromoWeb.objects.prefetch_related('items__producto').order_by('-creado_en')

    pedidos_activos = (PedidoWeb.objects
                       .exclude(estado='cancelado')
                       .select_related('producto', 'promo')
                       .order_by('-fecha'))

    pedidos_cancelados = (PedidoWeb.objects
                          .filter(estado='cancelado')
                          .select_related('producto', 'promo')
                          .order_by('-fecha'))

    pendientes = pedidos_activos.filter(estado__in=('pendiente_contacto', 'pendiente_pago')).count()

    return render(request, 'ecommerce/index.html', {
        'tab': tab,
        'ver_cancelados': ver_cancelados,
        'productos': productos,
        'promos': promos,
        'pedidos': pedidos_activos,
        'pedidos_cancelados': pedidos_cancelados,
        'pendientes': pendientes,
    })


@login_required
@require_POST
def publicar_producto(request, pk):
    """Crea el registro ProductoWeb para un producto aún no publicado."""
    producto = get_object_or_404(Producto, pk=pk, activo=True)
    pw, created = ProductoWeb.objects.get_or_create(
        producto=producto,
        defaults={'precio_web': producto.precio_venta},
    )
    if created:
        messages.success(request, f'"{producto.nombre}" agregado al catálogo web.')
    return redirect(reverse('ecommerce:index') + '?tab=catalogo')


@login_required
@require_POST
def toggle_campo(request, pk):
    """Alterna visible o destacado de un ProductoWeb."""
    pw = get_object_or_404(ProductoWeb, pk=pk)
    campo = request.POST.get('campo')
    if campo in ('visible', 'destacado'):
        setattr(pw, campo, not getattr(pw, campo))
        pw.save(update_fields=[campo, 'actualizado_en'])
    return redirect(reverse('ecommerce:index') + '?tab=catalogo')


@login_required
@require_POST
def precio_web_editar(request, pk):
    """Actualiza el precio web de un ProductoWeb."""
    pw = get_object_or_404(ProductoWeb, pk=pk)
    try:
        nuevo = request.POST.get('precio_web', '').strip()
        if nuevo:
            pw.precio_web = nuevo
            pw.save(update_fields=['precio_web', 'actualizado_en'])
            messages.success(request, f'Precio web de "{pw.titulo_display}" actualizado.')
    except Exception as e:
        messages.error(request, f'Error al actualizar precio: {e}')
    return redirect(reverse('ecommerce:index') + '?tab=catalogo')


@login_required
@require_POST
def confirmar_pedido(request, pk):
    """Confirma un PedidoWeb: crea y confirma una Venta, descuenta stock."""
    pedido = get_object_or_404(PedidoWeb, pk=pk)

    if pedido.estado not in ('pendiente_contacto', 'pendiente_pago'):
        messages.error(request, 'Este pedido ya fue procesado.')
        return redirect(reverse('ecommerce:index') + '?tab=pedidos')

    try:
        with transaction.atomic():
            venta = Venta(
                cliente_nombre=pedido.cliente_nombre,
                cliente_telefono=pedido.cliente_telefono,
                fecha=pedido.fecha.date(),
                canal='ecommerce',
                observaciones=f'Pedido web {pedido.id_pedido}',
                estado='borrador',
                creado_por=request.user,
            )
            venta.save()

            if pedido.tipo_pedido == 'producto' and pedido.producto:
                ItemVenta.objects.create(
                    venta=venta,
                    producto=pedido.producto,
                    cantidad=pedido.cantidad,
                    precio_unitario=pedido.precio_unitario,
                )

            _confirmar_venta(venta, request.user)

            pedido.estado = 'confirmado'
            pedido.save(update_fields=['estado', 'actualizado_en'])

            messages.success(
                request,
                f'Pedido {pedido.id_pedido} confirmado. '
                f'Venta <strong>{venta.numero}</strong> creada y stock descontado.'
            )
    except Exception as e:
        messages.error(request, f'Error al confirmar pedido: {e}')

    return redirect(reverse('ecommerce:index') + '?tab=pedidos')


@login_required
@require_POST
def cancelar_pedido(request, pk):
    """Cancela un PedidoWeb pendiente."""
    pedido = get_object_or_404(PedidoWeb, pk=pk)
    if pedido.estado not in ('pendiente_contacto', 'pendiente_pago'):
        messages.error(request, 'Solo se pueden cancelar pedidos pendientes.')
    else:
        pedido.estado = 'cancelado'
        pedido.save(update_fields=['estado', 'actualizado_en'])
        messages.success(request, f'Pedido {pedido.id_pedido} cancelado.')
    return redirect(reverse('ecommerce:index') + '?tab=pedidos')


def _confirmar_venta(venta, usuario):
    for item in venta.items.all():
        stock, _ = StockActual.objects.get_or_create(producto=item.producto)
        anterior = stock.cantidad
        stock.cantidad -= item.cantidad
        stock.ultima_venta = timezone.now()
        stock.save()
        MovimientoStock.objects.create(
            producto=item.producto,
            tipo='salida_venta',
            cantidad=-item.cantidad,
            stock_anterior=anterior,
            stock_posterior=stock.cantidad,
            referencia_tipo='venta',
            referencia_id=venta.id,
            observacion=f'Venta {venta.numero} (tienda online)',
            creado_por=usuario,
        )
        item.costo_unitario = item.producto.precio_costo
        item.save(update_fields=['costo_unitario'])
    venta.estado = 'confirmada'
    venta.save(update_fields=['estado'])


# ── Tienda pública ────────────────────────────────────────────────────────────

def tienda_index(request):
    """Tienda online pública — no requiere login."""
    productos_web = (ProductoWeb.objects
                     .filter(visible=True)
                     .select_related('producto', 'producto__categoria', 'producto__stock')
                     .order_by('-destacado', 'orden', 'producto__nombre'))
    return render(request, 'tienda/index.html', {'productos_web': productos_web})


def tienda_pedido(request):
    """Recibe el formulario de pedido, guarda PedidoWeb y redirige a WhatsApp."""
    if request.method != 'POST':
        return redirect('tienda:index')

    try:
        pw = get_object_or_404(
            ProductoWeb,
            pk=request.POST.get('producto_web_id'),
            visible=True,
        )
        nombre = request.POST.get('nombre', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        try:
            cantidad = max(1, int(request.POST.get('cantidad', 1)))
        except (ValueError, TypeError):
            cantidad = 1
        observaciones = request.POST.get('observaciones', '').strip()

        precio = pw.precio_web
        total = precio * cantidad

        lineas = [
            '¡Hola! Quiero hacer un pedido:',
            f'Producto: {pw.titulo_display}',
            f'Cantidad: {cantidad}',
            f'Precio unitario: Gs. {int(precio):,}'.replace(',', '.'),
            f'Total: Gs. {int(total):,}'.replace(',', '.'),
            '',
            f'Nombre: {nombre}',
            f'Teléfono: {telefono}',
        ]
        if observaciones:
            lineas.append(f'Notas: {observaciones}')

        msg = '\n'.join(lineas)
        wa_url = f'https://wa.me/595984841242?text={quote(msg)}'

        pedido = PedidoWeb(
            cliente_nombre=nombre,
            cliente_telefono=telefono,
            tipo_pedido='producto',
            producto=pw.producto,
            cantidad=cantidad,
            precio_unitario=precio,
            total=total,
            observaciones=observaciones,
            whatsapp_url=wa_url,
        )
        pedido.save()

        return redirect(wa_url)

    except Exception:
        return redirect('tienda:index')
