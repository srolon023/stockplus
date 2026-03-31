from django.db import models
from django.core.validators import MinValueValidator


class ProductoWeb(models.Model):
    """
    Versión pública de un producto para la tienda online.
    """
    producto        = models.OneToOneField('inventario.Producto', on_delete=models.CASCADE,
                                           related_name='producto_web', primary_key=True)
    titulo_web      = models.CharField(max_length=200, blank=True)
    descripcion_web = models.TextField(blank=True)
    precio_web      = models.DecimalField(max_digits=12, decimal_places=0,
                                          validators=[MinValueValidator(0)], default=0)
    visible         = models.BooleanField(default=True, db_index=True)
    destacado       = models.BooleanField(default=False)
    orden           = models.PositiveIntegerField(default=0)
    actualizado_en  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Producto (tienda)"
        verbose_name_plural = "Productos (tienda)"
        ordering = ['orden', 'producto__codigo']

    def __str__(self):
        return f"[Web] {self.producto}"

    @property
    def titulo_display(self):
        return self.titulo_web or str(self.producto)

    @property
    def imagen_src(self):
        return self.producto.imagen_src


class PromoWeb(models.Model):
    """Combo o promoción que agrupa varios productos"""
    id_promo    = models.CharField(max_length=20, unique=True)
    nombre      = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    precio      = models.DecimalField(max_digits=12, decimal_places=0,
                                      validators=[MinValueValidator(0)])
    imagen      = models.ImageField(upload_to='promos/%Y/%m/', null=True, blank=True)
    imagen_url  = models.URLField(blank=True)
    visible     = models.BooleanField(default=True)
    destacada   = models.BooleanField(default=False)
    productos   = models.ManyToManyField('inventario.Producto',
                                         through='ItemPromoWeb',
                                         related_name='promos')
    creado_en       = models.DateTimeField(auto_now_add=True)
    actualizado_en  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Promo"
        verbose_name_plural = "Promos"

    def __str__(self):
        return f"{self.id_promo} — {self.nombre}"


class ItemPromoWeb(models.Model):
    promo    = models.ForeignKey(PromoWeb, on_delete=models.CASCADE,
                                 related_name='items')
    producto = models.ForeignKey('inventario.Producto', on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = [['promo', 'producto']]

    def __str__(self):
        return f"{self.promo.id_promo} | {self.producto.codigo} x{self.cantidad}"


class PedidoWeb(models.Model):
    """
    Pedido recibido desde la tienda online.
    Se convierte en Venta al confirmarse desde el backend.
    """
    ESTADO_CHOICES = [
        ('pendiente_contacto', 'Pendiente contacto'),
        ('pendiente_pago',     'Pendiente pago'),
        ('confirmado',         'Confirmado'),
        ('preparando',         'Preparando'),
        ('enviado',            'Enviado'),
        ('entregado',          'Entregado'),
        ('cancelado',          'Cancelado'),
    ]

    id_pedido        = models.CharField(max_length=20, unique=True, db_index=True)
    cliente_nombre   = models.CharField(max_length=200)
    cliente_telefono = models.CharField(max_length=30)
    fecha            = models.DateTimeField(auto_now_add=True, db_index=True)
    estado           = models.CharField(max_length=25, choices=ESTADO_CHOICES,
                                        default='pendiente_contacto', db_index=True)
    tipo_pedido      = models.CharField(max_length=10,
                                        choices=[('producto','Producto'),('promo','Promo')])
    producto         = models.ForeignKey('inventario.Producto', on_delete=models.PROTECT,
                                         null=True, blank=True, related_name='pedidos_web')
    promo            = models.ForeignKey(PromoWeb, on_delete=models.PROTECT,
                                         null=True, blank=True, related_name='pedidos_web')
    cantidad         = models.PositiveIntegerField(default=1)
    precio_unitario  = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    total            = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    observaciones    = models.TextField(blank=True)
    whatsapp_url     = models.TextField(blank=True)
    actualizado_en   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pedido web"
        verbose_name_plural = "Pedidos web"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.id_pedido} — {self.cliente_nombre} — {self.get_estado_display()}"

    @property
    def esta_vencido(self):
        from django.utils import timezone
        from datetime import timedelta
        return (timezone.now() > self.fecha + timedelta(hours=72) and
                self.estado in ('pendiente_contacto', 'pendiente_pago'))

    def save(self, *args, **kwargs):
        if not self.id_pedido:
            from django.utils import timezone
            ts = timezone.now().strftime('%Y%m%d%H%M%S')
            self.id_pedido = f"PED-{ts}"
        super().save(*args, **kwargs)
