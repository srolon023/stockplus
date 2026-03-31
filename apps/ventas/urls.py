from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    path('', views.index, name='index'),
    path('nueva/', views.venta_nueva, name='nueva'),
    path('mi-dashboard/', views.dashboard_vendedor, name='dashboard_vendedor'),
    path('<int:pk>/', views.venta_detalle, name='detalle'),
    path('<int:pk>/editar/', views.venta_editar, name='editar'),
    path('<int:pk>/eliminar/', views.venta_eliminar, name='eliminar'),
    path('api/buscar-productos/', views.api_buscar_productos, name='api_buscar_productos'),
]
