from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from .models import Compra, ItemCompra, AdicionalCompra, Proveedor
from apps.inventario.models import Producto, StockActual, MovimientoStock
from apps.gastos.models import ConceptoAdicional
from django.utils import timezone


@login_required
def index(request):
    compras = Compra.objects.select_related('proveedor').all()
    return render(request, 'compras/index.html', {'compras': compras})


@login_required
def compra_nueva(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                compra = Compra(
                    proveedor_id  = request.POST.get('proveedor') or None,
                    fecha         = request.POST['fecha'],
                    moneda        = request.POST.get('moneda', 'PYG'),
                    tipo_cambio   = request.POST.get('tipo_cambio') or 1,
                    nro_factura   = request.POST.get('nro_factura', ''),
                    observaciones = request.POST.get('observaciones', ''),
                    estado        = 'borrador',
                    creado_por    = request.user,
                )
                compra.save()
                productos_ids = request.POST.getlist('producto_id[]')
                cantidades    = request.POST.getlist('cantidad[]')
                precios       = request.POST.getlist('precio_unitario[]')
                for pid, cant, precio in zip(productos_ids, cantidades, precios):
                    if pid and cant and precio:
                        ItemCompra.objects.create(
                            compra=compra,
                            producto_id=pid,
                            cantidad=int(cant),
                            precio_unitario=precio,
                        )
                conceptos_ids = request.POST.getlist('concepto_id[]')
                descripciones = request.POST.getlist('adicional_desc[]')
                montos        = request.POST.getlist('adicional_monto[]')
                for cid, desc, monto in zip(conceptos_ids, descripciones, montos):
                    if cid and monto:
                        AdicionalCompra.objects.create(
                            compra=compra,
                            concepto_id=cid,
                            descripcion=desc,
                            monto=monto,
                        )
                if request.POST.get('accion') == 'confirmar':
                    _confirmar_compra(compra, request.user)
                    messages.success(request, f'Compra {compra.numero} confirmada. Stock actualizado.')
                else:
                    messages.success(request, f'Compra {compra.numero} guardada como borrador.')
                return redirect('compras:index')
        except Exception as e:
            messages.error(request, f'Error al guardar la compra: {e}')

    productos   = Producto.objects.filter(activo=True).order_by('nombre')
    proveedores = Proveedor.objects.filter(activo=True)
    conceptos   = ConceptoAdicional.objects.filter(activo=True, aplica_a__in=['compra','todos'])
    return render(request, 'compras/compra_form.html', {
        'productos':   productos,
        'proveedores': proveedores,
        'conceptos':   conceptos,
        'hoy':         timezone.now().date(),
    })


def _confirmar_compra(compra, usuario):
    for item in compra.items.all():
        stock, _ = StockActual.objects.get_or_create(producto=item.producto)
        anterior = stock.cantidad
        stock.cantidad += item.cantidad
        stock.ultima_compra = timezone.now()
        stock.save()
        MovimientoStock.objects.create(
            producto=item.producto,
            tipo='entrada_compra',
            cantidad=item.cantidad,
            stock_anterior=anterior,
            stock_posterior=stock.cantidad,
            referencia_tipo='compra',
            referencia_id=compra.id,
            observacion=f'Compra {compra.numero}',
            creado_por=usuario,
        )
        item.producto.precio_costo = item.precio_unitario
        item.producto.save(update_fields=['precio_costo'])
    compra.estado = 'recibida'
    compra.save(update_fields=['estado'])


@login_required
def compra_detalle(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    if request.method == 'POST' and compra.estado == 'borrador':
        try:
            with transaction.atomic():
                _confirmar_compra(compra, request.user)
            messages.success(request, f'Compra {compra.numero} confirmada. Stock actualizado.')
        except Exception as e:
            messages.error(request, f'Error: {e}')
        return redirect('compras:detalle', pk=pk)
    return render(request, 'compras/compra_detalle.html', {'compra': compra})


@login_required
def compra_editar(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    if compra.estado != 'borrador':
        messages.error(request, 'Solo se pueden editar compras en estado borrador.')
        return redirect('compras:detalle', pk=pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                compra.proveedor_id  = request.POST.get('proveedor') or None
                compra.fecha         = request.POST['fecha']
                compra.moneda        = request.POST.get('moneda', 'PYG')
                compra.tipo_cambio   = request.POST.get('tipo_cambio') or 1
                compra.nro_factura   = request.POST.get('nro_factura', '')
                compra.observaciones = request.POST.get('observaciones', '')
                compra.save()
                compra.items.all().delete()
                compra.adicionales.all().delete()
                productos_ids = request.POST.getlist('producto_id[]')
                cantidades    = request.POST.getlist('cantidad[]')
                precios       = request.POST.getlist('precio_unitario[]')
                for pid, cant, precio in zip(productos_ids, cantidades, precios):
                    if pid and cant and precio:
                        ItemCompra.objects.create(
                            compra=compra,
                            producto_id=pid,
                            cantidad=int(cant),
                            precio_unitario=precio,
                        )
                conceptos_ids = request.POST.getlist('concepto_id[]')
                descripciones = request.POST.getlist('adicional_desc[]')
                montos        = request.POST.getlist('adicional_monto[]')
                for cid, desc, monto in zip(conceptos_ids, descripciones, montos):
                    if cid and monto:
                        AdicionalCompra.objects.create(
                            compra=compra,
                            concepto_id=cid,
                            descripcion=desc,
                            monto=monto,
                        )
                if request.POST.get('accion') == 'confirmar':
                    _confirmar_compra(compra, request.user)
                    messages.success(request, f'Compra {compra.numero} confirmada. Stock actualizado.')
                    return redirect('compras:index')
                else:
                    messages.success(request, f'Compra {compra.numero} actualizada.')
                    return redirect('compras:detalle', pk=pk)
        except Exception as e:
            messages.error(request, f'Error al guardar la compra: {e}')

    productos   = Producto.objects.filter(activo=True).order_by('nombre')
    proveedores = Proveedor.objects.filter(activo=True)
    conceptos   = ConceptoAdicional.objects.filter(activo=True, aplica_a__in=['compra', 'todos'])
    return render(request, 'compras/compra_form.html', {
        'compra':      compra,
        'productos':   productos,
        'proveedores': proveedores,
        'conceptos':   conceptos,
    })


@login_required
def compra_eliminar(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    if request.method == 'POST':
        numero = compra.numero
        compra.delete()
        messages.success(request, f'Compra {numero} eliminada.')
        return redirect('compras:index')
    tiene_stock = compra.estado == 'recibida'
    return render(request, 'compras/compra_confirmar_eliminar.html', {
        'object': compra,
        'tiene_stock': tiene_stock,
    })


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
            'precio_costo': int(p.precio_costo),
        }
        for p in qs
    ]
    return JsonResponse({'productos': data})
