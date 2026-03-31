import calendar
import json
from datetime import date, timedelta

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Sum
from django.utils import timezone

from apps.inventario.models import Producto, StockActual
from apps.ventas.models import Venta
from apps.compras.models import Compra
from apps.gastos.models import GastoGeneral

REMEMBER_ME_AGE = 30 * 24 * 60 * 60  # 30 días en segundos


class CustomLoginView(LoginView):
    """LoginView extendido con soporte de 'Recordar sesión'."""
    template_name = 'login.html'

    def form_valid(self, form):
        remember = self.request.POST.get('remember_me')
        response = super().form_valid(form)
        if remember:
            self.request.session.set_expiry(REMEMBER_ME_AGE)
        else:
            self.request.session.set_expiry(0)  # expira al cerrar el navegador
        return response


MESES_ES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

AÑO_INICIAL = 2024


@login_required
def index(request):
    hoy = timezone.now().date()

    # ── Período seleccionado (GET: mes, anio) ────────────────────────────────
    try:
        mes = int(request.GET['mes'])
        if not 1 <= mes <= 12:
            raise ValueError
    except (KeyError, ValueError, TypeError):
        mes = hoy.month

    try:
        anio = int(request.GET['anio'])
        if not (AÑO_INICIAL <= anio <= hoy.year):
            raise ValueError
    except (KeyError, ValueError, TypeError):
        anio = hoy.year

    inicio_mes = date(anio, mes, 1)
    _, ultimo_dia = calendar.monthrange(anio, mes)
    fin_mes = date(anio, mes, ultimo_dia)

    # ── KPIs del período ─────────────────────────────────────────────────────
    ventas_mes_qs = (
        Venta.objects
        .filter(fecha__gte=inicio_mes, fecha__lte=fin_mes)
        .exclude(estado__in=['cancelada', 'devuelta'])
        .prefetch_related('items', 'adicionales')
    )
    # Separar productos de adicionales en ventas
    total_ventas_productos = sum(v.subtotal_productos for v in ventas_mes_qs)
    total_adicionales_venta = sum(v.total_adicionales for v in ventas_mes_qs)
    total_ventas_mes = total_ventas_productos + total_adicionales_venta

    compras_mes_qs = (
        Compra.objects
        .filter(fecha__gte=inicio_mes, fecha__lte=fin_mes)
        .exclude(estado='cancelada')
        .prefetch_related('items', 'adicionales')
    )
    # Separar productos de adicionales en compras
    total_compras_productos = sum(c.subtotal_productos for c in compras_mes_qs)
    total_adicionales_compra = sum(c.total_adicionales for c in compras_mes_qs)
    total_compras_mes = total_compras_productos + total_adicionales_compra

    # Gastos generales — solo GastoGeneral, NO incluye AdicionalCompra/AdicionalVenta
    total_gastos_mes = (
        GastoGeneral.objects
        .filter(fecha__gte=inicio_mes, fecha__lte=fin_mes)
        .aggregate(total=Sum('monto'))['total'] or 0
    )

    ganancia_bruta = total_ventas_mes - total_compras_mes - total_gastos_mes

    # ── Stock bajo (< 3 unidades) ────────────────────────────────────────────
    stock_minimo = 3
    stock_bajo = (
        StockActual.objects
        .filter(cantidad__lt=stock_minimo)
        .select_related('producto', 'producto__categoria')
        .order_by('cantidad')
    )

    # ── Últimas 5 ventas ─────────────────────────────────────────────────────
    ultimas_ventas = (
        Venta.objects
        .select_related('cliente')
        .order_by('-fecha', '-creado_en')[:5]
    )

    # ── Últimas 5 compras ────────────────────────────────────────────────────
    ultimas_compras = (
        Compra.objects
        .select_related('proveedor')
        .order_by('-fecha', '-creado_en')[:5]
    )

    # ── Gráfico ventas últimos 7 días ────────────────────────────────────────
    hace_7_dias = hoy - timedelta(days=6)
    ventas_7d = (
        Venta.objects
        .filter(fecha__gte=hace_7_dias)
        .exclude(estado__in=['cancelada', 'devuelta'])
        .prefetch_related('items', 'adicionales')
    )

    totales_por_dia = {}
    for v in ventas_7d:
        key = v.fecha.strftime('%d/%m')
        totales_por_dia[key] = totales_por_dia.get(key, 0) + v.total

    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        key = dia.strftime('%d/%m')
        chart_labels.append(key)
        chart_data.append(int(totales_por_dia.get(key, 0)))

    # ── Gráfico ventas acumuladas por día de semana del mes ──────────────────
    DIAS_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    totales_por_dow = {i: 0 for i in range(7)}
    for v in ventas_mes_qs:
        totales_por_dow[v.fecha.weekday()] += v.total
    chart_dow_labels = DIAS_SEMANA
    chart_dow_data = [int(totales_por_dow[i]) for i in range(7)]

    context = {
        # Período seleccionado
        'mes_seleccionado': mes,
        'anio_seleccionado': anio,
        'nombre_mes': MESES_ES[mes - 1],
        'anios_disponibles': list(range(AÑO_INICIAL, hoy.year + 1)),
        'meses_disponibles': list(enumerate(MESES_ES, start=1)),
        # KPIs existentes
        'total_productos': Producto.objects.filter(activo=True).count(),
        'productos_sin_stock': StockActual.objects.filter(cantidad=0).count(),
        # KPIs del período
        'total_ventas_mes': total_ventas_mes,
        'total_ventas_productos': total_ventas_productos,
        'total_adicionales_venta': total_adicionales_venta,
        'total_compras_mes': total_compras_mes,
        'total_compras_productos': total_compras_productos,
        'total_adicionales_compra': total_adicionales_compra,
        'total_gastos_mes': total_gastos_mes,
        'ganancia_bruta': ganancia_bruta,
        # Tablas
        'stock_bajo': stock_bajo,
        'ultimas_ventas': ultimas_ventas,
        'ultimas_compras': ultimas_compras,
        # Chart 7 días
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        # Chart día de semana
        'chart_dow_labels': json.dumps(chart_dow_labels),
        'chart_dow_data': json.dumps(chart_dow_data),
    }
    return render(request, 'dashboard/index.html', context)
