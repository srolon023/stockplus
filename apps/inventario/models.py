from django.db import models
from django.core.validators import MinValueValidator


class CategoriaProducto(models.Model):
    nombre      = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo      = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    codigo          = models.CharField(max_length=20, unique=True, db_index=True)
    categoria       = models.ForeignKey(CategoriaProducto, on_delete=models.PROTECT,
                                        null=True, blank=True, related_name='productos')
    nombre          = models.CharField(max_length=200)
    modelo_celular  = models.CharField(max_length=100, blank=True)
    color           = models.CharField(max_length=80, blank=True)
    descripcion     = models.TextField(blank=True)
    precio_costo    = models.DecimalField(max_digits=12, decimal_places=0, default=0,
                                          validators=[MinValueValidator(0)])
    precio_venta    = models.DecimalField(max_digits=12, decimal_places=0, default=0,
                                          validators=[MinValueValidator(0)])
    imagen          = models.ImageField(upload_to='productos/%Y/%m/', null=True, blank=True)
    imagen_url      = models.URLField(blank=True)
    activo          = models.BooleanField(default=True, db_index=True)
    creado_en       = models.DateTimeField(auto_now_add=True)
    actualizado_en  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['codigo']

    def __str__(self):
        partes = [self.nombre]
        if self.modelo_celular:
            partes.append(self.modelo_celular)
        if self.color:
            partes.append(self.color)
        return ' / '.join(partes)

    @property
    def stock_disponible(self):
        try:
            return self.stock.cantidad
        except StockActual.DoesNotExist:
            return 0

    @property
    def imagen_src(self):
        if self.imagen:
            return self.imagen.url
        return self.imagen_url or ''


class StockActual(models.Model):
    producto        = models.OneToOneField(Producto, on_delete=models.CASCADE,
                                           related_name='stock', primary_key=True)
    cantidad        = models.IntegerField(default=0)
    ultima_compra   = models.DateTimeField(null=True, blank=True)
    ultima_venta    = models.DateTimeField(null=True, blank=True)
    actualizado_en  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Stock actual"
        verbose_name_plural = "Stock actual"

    def __str__(self):
        return f"{self.producto.codigo}: {self.cantidad} unidades"


class MovimientoStock(models.Model):
    TIPO_CHOICES = [
        ('entrada_compra',    'Entrada por compra'),
        ('salida_venta',      'Salida por venta'),
        ('ajuste_positivo',   'Ajuste positivo'),
        ('ajuste_negativo',   'Ajuste negativo'),
        ('devolucion_venta',  'Devolución de venta'),
        ('devolucion_compra', 'Devolución a proveedor'),
    ]
    producto        = models.ForeignKey(Producto, on_delete=models.PROTECT,
                                        related_name='movimientos')
    tipo            = models.CharField(max_length=30, choices=TIPO_CHOICES)
    cantidad        = models.IntegerField()
    stock_anterior  = models.IntegerField()
    stock_posterior = models.IntegerField()
    referencia_tipo = models.CharField(max_length=30, blank=True)
    referencia_id   = models.PositiveIntegerField(null=True, blank=True)
    observacion     = models.TextField(blank=True)
    creado_en       = models.DateTimeField(auto_now_add=True)
    creado_por      = models.ForeignKey('auth.User', on_delete=models.SET_NULL,
                                        null=True, blank=True)

    class Meta:
        verbose_name = "Movimiento de stock"
        verbose_name_plural = "Movimientos de stock"
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.producto.codigo} | {self.get_tipo_display()} | {self.cantidad:+d}"
