import calendar
from datetime import date
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone

from apps.ventas.models import Venta
from apps.compras.models import Compra
from apps.gastos.models import GastoGeneral
from .models import Movimiento


def _rango_mes(mes_param):
    """Devuelve (inicio, fin) de mes dado 'YYYY-MM'. Usa mes actual si inválido."""
    hoy = timezone.now().date()
    if mes_param:
        try:
            year, month = map(int, mes_param.split('-'))
            inicio = date(year, month, 1)
        except (ValueError, TypeError):
            inicio = hoy.replace(day=1)
    else:
        inicio = hoy.replace(day=1)
    ultimo_dia = calendar.monthrange(inicio.year, inicio.month)[1]
    fin = date(inicio.year, inicio.month, ultimo_dia)
    return inicio, fin


@login_required
def resumen(request):
    mes_param = request.GET.get('mes', '')
    tipo_filtro = request.GET.get('tipo', '')

    inicio_mes, fin_mes = _rango_mes(mes_param)
    mes_display = inicio_mes.strftime('%B %Y')

    # ── Datos operacionales ──────────────────────────────────────────────────
    ventas_qs = (Venta.objects
                 .filter(fecha__range=(inicio_mes, fin_mes))
                 .exclude(estado__in=['cancelada', 'devuelta'])
                 .prefetch_related('items', 'adicionales'))

    compras_qs = (Compra.objects
                  .filter(fecha__range=(inicio_mes, fin_mes))
                  .exclude(estado='cancelada')
                  .prefetch_related('items', 'adicionales'))

    gastos_qs = (GastoGeneral.objects
                 .filter(fecha__range=(inicio_mes, fin_mes))
                 .select_related('concepto'))

    movs_qs = Movimiento.objects.filter(fecha__range=(inicio_mes, fin_mes))

    # ── Totales (sin filtro de tipo para que los KPIs sean siempre del mes) ──
    total_ingresos_venta = sum(v.total for v in ventas_qs)
    total_egresos_compra = sum(c.total for c in compras_qs)
    total_egresos_gasto = gastos_qs.aggregate(s=Sum('monto'))['s'] or 0

    # AdicionalCompra y AdicionalVenta ya están incluidos en total de cada operación
    # Se muestran en su respectiva sección, NO como GastoGeneral
    total_adicionales_venta = sum(v.total_adicionales for v in ventas_qs)
    total_adicionales_compra = sum(c.total_adicionales for c in compras_qs)

    total_inv_entrada = movs_qs.filter(tipo='inversion_entrada').aggregate(s=Sum('monto'))['s'] or 0
    total_inv_salida = movs_qs.filter(tipo='inversion_salida').aggregate(s=Sum('monto'))['s'] or 0
    total_retiros = movs_qs.filter(tipo='retiro').aggregate(s=Sum('monto'))['s'] or 0
    total_ajustes = movs_qs.filter(tipo='ajuste').aggregate(s=Sum('monto'))['s'] or 0

    total_ingresos = total_ingresos_venta + total_inv_entrada
    total_egresos = total_egresos_compra + total_egresos_gasto + total_inv_salida + total_retiros
    saldo = total_ingresos - total_egresos + total_ajustes

    # ── Lista unificada de movimientos (filtrables) ──────────────────────────
    movimientos = []

    TIPOS_OPERACIONALES = ('ingreso_venta', 'egreso_compra', 'egreso_gasto')

    if not tipo_filtro or tipo_filtro == 'ingreso_venta':
        for v in ventas_qs:
            movimientos.append({
                'fecha': v.fecha,
                'tipo': 'ingreso_venta',
                'tipo_display': 'Ingreso por venta',
                'descripcion': f'Venta {v.numero} — '
                               f'{v.cliente.nombre if v.cliente else v.cliente_nombre or "Sin nombre"}',
                'monto': v.total,
                'referencia': v.numero,
                'positivo': True,
            })

    if not tipo_filtro or tipo_filtro == 'egreso_compra':
        for c in compras_qs:
            movimientos.append({
                'fecha': c.fecha,
                'tipo': 'egreso_compra',
                'tipo_display': 'Egreso por compra',
                'descripcion': f'Compra {c.numero} — {c.proveedor or "Sin proveedor"}',
                'monto': c.total,
                'referencia': c.numero,
                'positivo': False,
            })

    if not tipo_filtro or tipo_filtro == 'egreso_gasto':
        for g in gastos_qs:
            movimientos.append({
                'fecha': g.fecha,
                'tipo': 'egreso_gasto',
                'tipo_display': 'Gasto general',
                'descripcion': f'{g.concepto.nombre} — {g.descripcion}',
                'monto': g.monto,
                'referencia': '',
                'positivo': False,
            })

    # Movimientos manuales
    movs_filtrados = movs_qs
    if tipo_filtro and tipo_filtro not in TIPOS_OPERACIONALES:
        movs_filtrados = movs_qs.filter(tipo=tipo_filtro)
    elif tipo_filtro in TIPOS_OPERACIONALES:
        movs_filtrados = movs_qs.none()

    for m in movs_filtrados:
        positivo = m.tipo == 'inversion_entrada' or (m.tipo == 'ajuste' and m.monto > 0)
        movimientos.append({
            'fecha': m.fecha,
            'tipo': m.tipo,
            'tipo_display': m.get_tipo_display(),
            'descripcion': m.descripcion,
            'monto': abs(m.monto),
            'referencia': '',
            'positivo': positivo,
        })

    movimientos.sort(key=lambda x: x['fecha'], reverse=True)

    context = {
        'mes_param': inicio_mes.strftime('%Y-%m'),
        'mes_display': mes_display,
        'tipo_filtro': tipo_filtro,
        'movimientos': movimientos,
        # KPIs
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'saldo': saldo,
        # Desglose
        'total_ingresos_venta': total_ingresos_venta,
        'total_adicionales_venta': total_adicionales_venta,
        'total_egresos_compra': total_egresos_compra,
        'total_adicionales_compra': total_adicionales_compra,
        'total_egresos_gasto': total_egresos_gasto,
        'total_inv_entrada': total_inv_entrada,
        'total_inv_salida': total_inv_salida,
        'total_retiros': total_retiros,
        'total_ajustes': total_ajustes,
    }
    return render(request, 'finanzas/index.html', context)


@login_required
def registrar_movimiento(request):
    TIPOS_MANUALES = [
        ('inversion_entrada', 'Inversión entrada'),
        ('inversion_salida',  'Inversión salida'),
        ('retiro',            'Retiro'),
        ('ajuste',            'Ajuste'),
    ]
    TIPOS_KEYS = [t[0] for t in TIPOS_MANUALES]

    if request.method == 'POST':
        try:
            tipo = request.POST.get('tipo', '')
            if tipo not in TIPOS_KEYS:
                raise ValueError('Tipo de movimiento inválido.')

            fecha_str = request.POST.get('fecha', '').strip()
            descripcion = request.POST.get('descripcion', '').strip()
            monto_str = request.POST.get('monto', '').strip()

            if not fecha_str or not descripcion or not monto_str:
                raise ValueError('Todos los campos son obligatorios.')

            from datetime import datetime
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()

            # Soportar separador de miles con punto (formato PY)
            monto_limpio = monto_str.replace('.', '').replace(',', '').replace(' ', '')
            monto = Decimal(monto_limpio)

            Movimiento.objects.create(
                fecha=fecha,
                tipo=tipo,
                descripcion=descripcion,
                monto=monto,
                creado_por=request.user,
            )
            messages.success(request, 'Movimiento registrado.')
        except (ValueError, InvalidOperation) as e:
            messages.error(request, f'Error: {e}')

        return redirect('finanzas:resumen')

    return redirect('finanzas:resumen')
