from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Producto, CategoriaProducto, StockActual
import os
import uuid
from django.conf import settings


def guardar_imagen_local(archivo):
    """Guarda el archivo en media/productos/ con nombre uuid4 y devuelve la URL relativa."""
    try:
        ext = os.path.splitext(archivo.name)[1].lower() or '.jpg'
        nombre_archivo = f"{uuid.uuid4()}{ext}"
        ruta_relativa = os.path.join('productos', nombre_archivo)
        ruta_absoluta = os.path.join(settings.MEDIA_ROOT, 'productos')
        os.makedirs(ruta_absoluta, exist_ok=True)
        archivo.seek(0)
        with open(os.path.join(ruta_absoluta, nombre_archivo), 'wb') as f:
            for chunk in archivo.chunks():
                f.write(chunk)
        return settings.MEDIA_URL + ruta_relativa
    except Exception:
        return ''


def generar_codigo():
    """Genera el próximo código de producto disponible"""
    ultimo = Producto.objects.order_by('-id').first()
    num = (ultimo.id + 1) if ultimo else 1
    codigo = f"PROD-{num:04d}"
    # Asegurarse que no existe
    while Producto.objects.filter(codigo=codigo).exists():
        num += 1
        codigo = f"PROD-{num:04d}"
    return codigo


@login_required
def index(request):
    productos = Producto.objects.select_related('stock').all()
    return render(request, 'inventario/index.html', {'productos': productos})


@login_required
def producto_nuevo(request):
    if request.method == 'POST':
        try:
            imagen_url = ''
            if request.FILES.get('imagen_archivo'):
                archivo = request.FILES['imagen_archivo']
                imagen_url = guardar_imagen_local(archivo)
                if not imagen_url:
                    messages.warning(request, 'No se pudo procesar la imagen.')
            if not imagen_url:
                imagen_url = request.POST.get('imagen_url', '')

            producto = Producto(
                codigo         = generar_codigo(),
                nombre         = request.POST['nombre'],
                modelo_celular = request.POST.get('modelo_celular', ''),
                color          = request.POST.get('color', ''),
                descripcion    = request.POST.get('descripcion', ''),
                precio_costo   = request.POST.get('precio_costo') or 0,
                precio_venta   = request.POST.get('precio_venta') or 0,
                imagen_url     = imagen_url,
                activo         = request.POST.get('activo') == '1',
            )
            cat_id = request.POST.get('categoria')
            if cat_id:
                producto.categoria_id = cat_id
            producto.save()
            StockActual.objects.get_or_create(producto=producto)
            messages.success(request, f'Producto {producto.codigo} creado correctamente.')
            return redirect('inventario:index')
        except Exception as e:
            messages.error(request, f'Error al crear el producto: {e}')

    categorias = CategoriaProducto.objects.filter(activo=True)
    proximo_codigo = generar_codigo()
    return render(request, 'inventario/producto_form.html', {
        'categorias': categorias,
        'proximo_codigo': proximo_codigo,
    })


@login_required
def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        try:
            if request.FILES.get('imagen_archivo'):
                archivo = request.FILES['imagen_archivo']
                url = guardar_imagen_local(archivo)
                if url:
                    producto.imagen_url = url
                else:
                    messages.warning(request, 'No se pudo procesar la imagen.')
            elif request.POST.get('imagen_url'):
                producto.imagen_url = request.POST.get('imagen_url')

            producto.nombre         = request.POST['nombre']
            producto.modelo_celular = request.POST.get('modelo_celular', '')
            producto.color          = request.POST.get('color', '')
            producto.descripcion    = request.POST.get('descripcion', '')
            producto.precio_costo   = request.POST.get('precio_costo') or 0
            producto.precio_venta   = request.POST.get('precio_venta') or 0
            producto.activo         = request.POST.get('activo') == '1'
            cat_id = request.POST.get('categoria')
            producto.categoria_id   = cat_id if cat_id else None
            producto.save()
            messages.success(request, f'Producto {producto.codigo} actualizado.')
            return redirect('inventario:index')
        except Exception as e:
            messages.error(request, f'Error al guardar: {e}')

    categorias = CategoriaProducto.objects.filter(activo=True)
    return render(request, 'inventario/producto_form.html', {
        'object': producto,
        'categorias': categorias,
    })


@login_required
def producto_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        codigo = producto.codigo
        try:
            producto.delete()
            messages.success(request, f'Producto {codigo} eliminado.')
        except Exception:
            # Tiene registros relacionados — desactivar en lugar de eliminar
            producto.activo = False
            producto.save(update_fields=['activo'])
            messages.warning(request, f'Producto {codigo} tiene historial de ventas/compras y fue desactivado en lugar de eliminado.')
        return redirect('inventario:index')
    return render(request, 'inventario/producto_confirmar_eliminar.html', {'object': producto})


import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@login_required
@require_POST
def api_crear_producto(request):
    try:
        data = json.loads(request.body)
        nombre = data.get('nombre', '').strip()
        if not nombre:
            return JsonResponse({'ok': False, 'error': 'El nombre es obligatorio'})

        producto = Producto(
            codigo         = generar_codigo(),
            nombre         = nombre,
            modelo_celular = data.get('modelo_celular', ''),
            color          = data.get('color', ''),
            precio_costo   = data.get('precio_costo') or 0,
            precio_venta   = data.get('precio_venta') or 0,
            activo         = True,
        )
        producto.save()
        StockActual.objects.get_or_create(producto=producto)

        partes = [producto.nombre]
        if producto.modelo_celular:
            partes.append(producto.modelo_celular)
        if producto.color:
            partes.append(producto.color)
        texto = f"{producto.codigo} — {' / '.join(partes)}"

        return JsonResponse({
            'ok':    True,
            'id':    producto.pk,
            'codigo': producto.codigo,
            'texto': texto,
            'costo': float(producto.precio_costo),
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})
