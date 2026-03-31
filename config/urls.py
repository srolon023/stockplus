from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from apps.dashboard.views import CustomLoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('dashboard/', include('apps.dashboard.urls')),
    path('inventario/', include('apps.inventario.urls')),
    path('compras/', include('apps.compras.urls')),
    path('ventas/', include('apps.ventas.urls')),
    path('gastos/', include('apps.gastos.urls')),
    path('ecommerce/', include('apps.ecommerce.urls')),
    path('tienda/', include('apps.ecommerce.tienda_urls')),
    path('finanzas/', include('apps.finanzas.urls')),
    path('', lambda request: redirect('dashboard:index')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
