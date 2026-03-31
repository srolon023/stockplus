from datetime import timedelta
from collections import defaultdict

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from .models import Venta, ItemVenta, AdicionalVenta
from apps.inventario.models import Producto, StockActual, MovimientoStock
from apps.gastos.models import ConceptoAdicional
from django.utils import timezone


@login_required
def index(request):
    ventas = Venta.objects.prefetch_related('items__producto').all().order_by('-fecha', '-creado_en')
    return render(request, 'ventas/index.html', {'ventas': ventas})


@login_required
def api_buscar_productos(request):
    q = request.GET.get('q', '').strip()
    qs = Producto.objects.filter(activo=True)
    if q:
        qs = qs.filter(
            Q(codigo__icontains=q) | Q(nombre__icontains=q) |
            Q(modelo_celular__icontains=q) | Q(color__icontains=q)
        )
    qs = qs.order_by('codigo')[:30]
    data = [
        {
            'id': p.pk,
            'codigo': p.codigo,
            'nombre': str(p),
            'stock': p.stock_disponible,
            'precio_venta': int(p.precio_venta),
            'precio_costo': int(p.precio_costo),
        }
        for p in qs
    ]
    return JsonResponse({'productos': data})


@login_required
def venta_nueva(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                venta = Venta(
                    cliente_nombre   = request.POST.get('cliente_nombre', ''),
                    cliente_telefono = request.POST.get('cliente_telefono', ''),
                    fecha            = request.POST['fecha'],
                    canal            = request.POST.get('canal', 'presencial'),
                    observaciones    = request.POST.get('observaciones', ''),
                    estado           = 'borrador',
                    creado_por       = request.user,
                )
                venta.save()
                _guardar_items(venta, request.POST)
                if request.POST.get('accion') == 'confirmar':
                    _confirmar_venta(venta, request.user)
                    messages.success(request, f'Venta {venta.numero} confirmada. Stock descontado.')
                else:
                    messages.success(request, f'Venta {venta.numero} guardada como borrador.')
                return redirect('ventas:index')
        except Exception as e:
            messages.error(request, f'Error al guardar la venta: {e}')

    productos  = Producto.objects.filter(activo=True).order_by('nombre')
    conceptos  = ConceptoAdicional.objects.filter(activo=True, aplica_a__in=['venta', 'todos'])
    return render(request, 'ventas/venta_form.html', {
        'productos': productos,
        'conceptos': conceptos,
        'hoy':       timezone.now().date(),
        'canales':   Venta.CANAL_CHOICES if hasattr(Venta, 'CANAL_CHOICES') else [],
    })


@login_required
def venta_detalle(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    if request.method == 'POST' and venta.estado == 'borrador':
        try:
            with transaction.atomic():
                _confirmar_venta(venta, request.user)
            messages.success(request, f'Venta {venta.numero} confirmada. Stock descontado.')
        except Exception as e:
            messages.error(request, f'Error: {e}')
        return redirect('ventas:detalle', pk=pk)
    return render(request, 'ventas/venta_detalle.html', {'venta': venta})


@login_required
def venta_editar(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    if venta.estado != 'borrador':
        messages.error(request, 'Solo se pueden editar ventas en estado borrador.')
        return redirect('ventas:detalle', pk=pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                venta.cliente_nombre   = request.POST.get('cliente_nombre', '')
                venta.cliente_telefono = request.POST.get('cliente_telefono', '')
                venta.fecha            = request.POST['fecha']
                venta.canal            = request.POST.get('canal', 'presencial')
                venta.observaciones    = request.POST.get('observaciones', '')
                venta.save()
                venta.items.all().delete()
                venta.adicionales.all().delete()
                _guardar_items(venta, request.POST)
                if request.POST.get('accion') == 'confirmar':
                    _confirmar_venta(venta, request.user)
                    messages.success(request, f'Venta {venta.numero} confirmada. Stock descontado.')
                    return redirect('ventas:index')
                else:
                    messages.success(request, f'Venta {venta.numero} actualizada.')
                    return redirect('ventas:detalle', pk=pk)
        except Exception as e:
            messages.error(request, f'Error al guardar la venta: {e}')

    productos = Producto.objects.filter(activo=True).order_by('nombre')
    conceptos = ConceptoAdicional.objects.filter(activo=True, aplica_a__in=['venta', 'todos'])
    return render(request, 'ventas/venta_form.html', {
        'venta':     venta,
        'productos': productos,
        'conceptos': conceptos,
    })


@login_required
def venta_eliminar(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    if request.method == 'POST':
        numero = venta.numero
        venta.delete()
        messages.success(request, f'Venta {numero} eliminada.')
        return redirect('ventas:index')
    tiene_stock = venta.estado not in ('borrador',)
    return render(request, 'ventas/venta_confirmar_eliminar.html', {
        'object': venta,
        'tiene_stock': tiene_stock,
    })


# ── helpers ──────────────────────────────────────────────────────────────────

@login_required
def dashboard_vendedor(request):
    """Dashboard personal para vendedores: stats del día, semana, mes y ranking."""
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    last_30_start = today - timedelta(days=29)

    # Cargar ventas confirmadas desde el inicio del rango mayor
    desde = min(month_start, last_30_start)
    todas = list(
        Venta.objects
        .filter(
            creado_por=request.user,
            estado__in=['confirmada', 'preparando', 'enviada', 'entregada'],
            fecha__gte=desde,
        )
        .prefetch_related('items', 'adicionales')
        .order_by('-fecha', '-creado_en')
    )

    def _filtrar(ventas, desde_d=None, hasta_d=None):
        r = ventas
        if desde_d:
            r = [v for v in r if v.fecha >= desde_d]
        if hasta_d:
            r = [v for v in r if v.fecha <= hasta_d]
        return r

    ventas_hoy    = _filtrar(todas, desde_d=today, hasta_d=today)
    ventas_semana = _filtrar(todas, desde_d=week_start)
    ventas_mes    = _filtrar(todas, desde_d=month_start)
    ventas_30     = _filtrar(todas, desde_d=last_30_start)

    total_hoy    = sum(v.total for v in ventas_hoy)
    total_semana = sum(v.total for v in ventas_semana)
    total_mes    = sum(v.total for v in ventas_mes)

    # Ranking de días (últimos 30 días)
    dias = defaultdict(lambda: {'count': 0, 'total': 0})
    for v in ventas_30:
        dias[v.fecha]['count'] += 1
        dias[v.fecha]['total'] += v.total
    ranking_dias = sorted(
        [{'fecha': f, 'count': d['count'], 'total': d['total']} for f, d in dias.items()],
        key=lambda x: -x['total'],
    )[:10]

    return render(request, 'vendedores/dashboard.html', {
        'ventas_hoy':    ventas_hoy,
        'total_hoy':     total_hoy,
        'ventas_semana': ventas_semana,
        'total_semana':  total_semana,
        'ventas_mes':    ventas_mes,
        'total_mes':     total_mes,
        'ranking_dias':  ranking_dias,
        'ultimas':       todas[:10],
        'hoy':           today,
    })


def _guardar_items(venta, post):
    productos_ids = post.getlist('producto_id[]')
    cantidades    = post.getlist('cantidad[]')
    precios       = post.getlist('precio_unitario[]')
    descuentos    = post.getlist('descuento[]')
    for pid, cant, precio, desc in zip(productos_ids, cantidades, precios, descuentos):
        if pid and cant and precio:
            ItemVenta.objects.create(
                venta=venta,
                producto_id=pid,
                cantidad=int(cant),
                precio_unitario=precio,
                descuento=desc or 0,
            )
    conceptos_ids = post.getlist('concepto_id[]')
    descripciones = post.getlist('adicional_desc[]')
    montos        = post.getlist('adicional_monto[]')
    a_cargo_de    = post.getlist('a_cargo_de[]')
    for cid, desc, monto, cargo in zip(conceptos_ids, descripciones, montos, a_cargo_de):
        if cid and monto:
            AdicionalVenta.objects.create(
                venta=venta,
                concepto_id=cid,
                descripcion=desc,
                monto=monto,
                a_cargo_de=cargo or 'negocio',
            )


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
            observacion=f'Venta {venta.numero}',
            creado_por=usuario,
        )
        item.costo_unitario = item.producto.precio_costo
        item.save(update_fields=['costo_unitario'])
    venta.estado = 'confirmada'
    venta.save(update_fields=['estado'])
