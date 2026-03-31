from django.urls import path
from . import views

app_name = 'finanzas'

urlpatterns = [
    path('', views.resumen, name='resumen'),
    path('registrar/', views.registrar_movimiento, name='registrar'),
]
