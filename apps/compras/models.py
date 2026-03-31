from django.db import models
from django.core.validators import MinValueValidator


class Proveedor(models.Model):
    nombre      = models.CharField(max_length=200)
    ruc         = models.CharField(max_length=30, blank=True)
    telefono    = models.CharField(max_length=30, blank=True)
    email       = models.EmailField(blank=True)
    direccion   = models.TextField(blank=True)
    activo      = models.BooleanField(default=True)
    notas       = models.TextField(blank=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Compra(models.Model):
    ESTADO_CHOICES = [
        ('borrador',   'Borrador'),
        ('confirmada', 'Confirmada'),
        ('recibida',   'Recibida'),
        ('cancelada',  'Cancelada'),
    ]
    MONEDA_CHOICES = [
        ('PYG', 'Guaraníes'),
        ('USD', 'Dólares'),
        ('BRL', 'Reales'),
    ]

    numero          = models.CharField(max_length=20, unique=True, db_index=True)
    proveedor       = models.ForeignKey(Proveedor, on_delete=models.PROTECT,
                                        null=True, blank=True, related_name='compras')
    fecha           = models.DateField(db_index=True)
    estado          = models.CharField(max_length=20, choices=ESTADO_CHOICES,
                                       default='borrador')
    moneda          = models.CharField(max_length=5, choices=MONEDA_CHOICES, default='PYG')
    tipo_cambio     = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    nro_factura     = models.CharField(max_length=50, blank=True)
    observaciones   = models.TextField(blank=True)
    creado_en       = models.DateTimeField(auto_now_add=True)
    actualizado_en  = models.DateTimeField(auto_now=True)
    creado_por      = models.ForeignKey('auth.User', on_delete=models.SET_NULL,
                                        null=True, blank=True)

    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
        ordering = ['-fecha', '-creado_en']

    def __str__(self):
        return f"{self.numero} — {self.fecha}"

    @property
    def subtotal_productos(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def total_adicionales(self):
        return sum(a.monto for a in self.adicionales.all())

    @property
    def total(self):
        return self.subtotal_productos + self.total_adicionales

    def save(self, *args, **kwargs):
        if not self.numero:
            ultima = Compra.objects.order_by('-id').first()
            num = (ultima.id + 1) if ultima else 1
            self.numero = f"COMP-{num:04d}"
        super().save(*args, **kwargs)


class ItemCompra(models.Model):
    compra          = models.ForeignKey(Compra, on_delete=models.CASCADE,
                                        related_name='items')
    producto        = models.ForeignKey('inventario.Producto', on_delete=models.PROTECT,
                                        related_name='items_compra')
    cantidad        = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=0,
                                          validators=[MinValueValidator(0)])
    observacion     = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Ítem de compra"
        verbose_name_plural = "Ítems de compra"

    def __str__(self):
        return f"{self.compra.numero} | {self.producto.codigo} x{self.cantidad}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario


class AdicionalCompra(models.Model):
    """
    Costos adicionales de una compra: traslado, packaging, aduana, etc.
    Se elige de la lista de ConceptoAdicional.
    """
    compra      = models.ForeignKey(Compra, on_delete=models.CASCADE,
                                    related_name='adicionales')
    concepto    = models.ForeignKey('gastos.ConceptoAdicional', on_delete=models.PROTECT,
                                    related_name='adicionales_compra')
    descripcion = models.CharField(max_length=200, blank=True,
                                   help_text="Detalle opcional, ej: Transportista Pérez")
    monto       = models.DecimalField(max_digits=12, decimal_places=0,
                                      validators=[MinValueValidator(0)])
    comprobante = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Adicional de compra"
        verbose_name_plural = "Adicionales de compra"

    def __str__(self):
        return f"{self.compra.numero} | {self.concepto.nombre} | Gs. {self.monto:,.0f}"
