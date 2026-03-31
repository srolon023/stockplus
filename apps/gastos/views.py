from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import GastoGeneral, ConceptoAdicional
from django.utils import timezone


@login_required
def index(request):
    gastos = GastoGeneral.objects.select_related('concepto', 'creado_por').all()
    conceptos = ConceptoAdicional.objects.filter(activo=True, aplica_a__in=['gasto', 'todos'])

    concepto_filtro = request.GET.get('concepto', '')
    busqueda = request.GET.get('q', '')

    if concepto_filtro:
        gastos = gastos.filter(concepto_id=concepto_filtro)
    if busqueda:
        gastos = gastos.filter(
            Q(descripcion__icontains=busqueda) | Q(concepto__nombre__icontains=busqueda)
        )

    return render(request, 'gastos/index.html', {
        'gastos': gastos,
        'conceptos': conceptos,
        'concepto_filtro': concepto_filtro,
        'busqueda': busqueda,
    })


@login_required
def gasto_nuevo(request):
    if request.method == 'POST':
        try:
            GastoGeneral.objects.create(
                concepto_id=request.POST['concepto'],
                descripcion=request.POST.get('descripcion', ''),
                monto=request.POST['monto'],
                fecha=request.POST['fecha'],
                comprobante=request.POST.get('comprobante', ''),
                observacion=request.POST.get('observacion', ''),
                creado_por=request.user,
            )
            messages.success(request, 'Gasto registrado correctamente.')
            return redirect('gastos:index')
        except Exception as e:
            messages.error(request, f'Error al guardar: {e}')

    conceptos = ConceptoAdicional.objects.filter(activo=True, aplica_a__in=['gasto', 'todos'])
    return render(request, 'gastos/gasto_form.html', {
        'conceptos': conceptos,
        'hoy': timezone.now().date(),
    })


@login_required
def gasto_editar(request, pk):
    gasto = get_object_or_404(GastoGeneral, pk=pk)

    if request.method == 'POST':
        try:
            gasto.concepto_id = request.POST['concepto']
            gasto.descripcion = request.POST.get('descripcion', '')
            gasto.monto = request.POST['monto']
            gasto.fecha = request.POST['fecha']
            gasto.comprobante = request.POST.get('comprobante', '')
            gasto.observacion = request.POST.get('observacion', '')
            gasto.save()
            messages.success(request, 'Gasto actualizado correctamente.')
            return redirect('gastos:index')
        except Exception as e:
            messages.error(request, f'Error al guardar: {e}')

    conceptos = ConceptoAdicional.objects.filter(activo=True, aplica_a__in=['gasto', 'todos'])
    return render(request, 'gastos/gasto_form.html', {
        'gasto': gasto,
        'conceptos': conceptos,
    })


@login_required
def gasto_eliminar(request, pk):
    gasto = get_object_or_404(GastoGeneral, pk=pk)
    if request.method == 'POST':
        gasto.delete()
        messages.success(request, 'Gasto eliminado.')
        return redirect('gastos:index')
    return render(request, 'gastos/gasto_confirmar_eliminar.html', {'gasto': gasto})
