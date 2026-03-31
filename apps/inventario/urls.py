from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.index, name='index'),
    path('nuevo/', views.producto_nuevo, name='producto_nuevo'),
    path('<int:pk>/editar/', views.producto_editar, name='producto_editar'),
    path('<int:pk>/eliminar/', views.producto_eliminar, name='producto_eliminar'),
    path('api/crear-producto/', views.api_crear_producto, name='api_crear_producto'),
]
