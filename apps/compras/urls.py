from django.urls import path
from . import views

app_name = 'compras'

urlpatterns = [
    path('', views.index, name='index'),
    path('nueva/', views.compra_nueva, name='nueva'),
    path('<int:pk>/', views.compra_detalle, name='detalle'),
    path('<int:pk>/editar/', views.compra_editar, name='editar'),
    path('<int:pk>/eliminar/', views.compra_eliminar, name='eliminar'),
    path('api/buscar-productos/', views.api_buscar_productos, name='api_buscar_productos'),
]
