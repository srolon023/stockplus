from django.urls import path
from . import views

app_name = 'gastos'

urlpatterns = [
    path('', views.index, name='index'),
    path('nuevo/', views.gasto_nuevo, name='nuevo'),
    path('<int:pk>/editar/', views.gasto_editar, name='editar'),
    path('<int:pk>/eliminar/', views.gasto_eliminar, name='eliminar'),
]
