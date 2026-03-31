from django.urls import path
from apps.ecommerce import views

app_name = 'tienda'

urlpatterns = [
    path('', views.tienda_index, name='index'),
    path('pedido/', views.tienda_pedido, name='pedido'),
]
