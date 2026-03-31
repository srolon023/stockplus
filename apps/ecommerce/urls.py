from django.urls import path
from . import views

app_name = 'ecommerce'

urlpatterns = [
    path('', views.index, name='index'),
    path('producto/<int:pk>/publicar/', views.publicar_producto, name='publicar_producto'),
    path('producto/<int:pk>/toggle/', views.toggle_campo, name='toggle_campo'),
    path('producto/<int:pk>/precio/', views.precio_web_editar, name='precio_web_editar'),
    path('pedido/<int:pk>/confirmar/', views.confirmar_pedido, name='confirmar_pedido'),
    path('pedido/<int:pk>/cancelar/', views.cancelar_pedido, name='cancelar_pedido'),
]
