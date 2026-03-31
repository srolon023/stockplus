from django.db import models
from django.core.validators import MinValueValidator


class Cliente(models.Model):
    nombre      = models.CharField(max_length=200, db_index=True)
    telefono    = models.CharField(max_length=30, blank=True, db_index=True)
    email       = models.EmailField(blank=True)
    direccion   = models.TextField(blank=True)
    notas       = models.TextField(blank=True)
    creado_en   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nombre']

    def __str__(self):
        if self.telefono:
            return f"{self.nombre} ({self.telefono})"
        return self.nombre


class Venta(models.Model):
    ESTADO_CHOICES = [
        ('borrador',   'Borrador'),
        ('confirmada', 'Confirmada'),
        ('preparando', 'Preparando'),
        ('enviada',    'Enviada'),
        ('entregada',  'Entregada'),
        ('cancelada',  'Cancelada'),
        ('devuelta',   'Devuelta'),
    ]
    CANAL_CHOICES = [
        ('whatsapp',   'WhatsApp'),
        ('ecommerce',  'Tienda online'),
        ('presencial', 'Presencial'),
        ('instagram',  'Instagram'),
        ('facebook',   'Facebook'),
        ('otro',       'Otro'),
    ]

    numero           = models.CharField(max_length=20, unique=True, db_index=True)
    cliente          = models.ForeignKey(Cliente, on_delete=models.PROTECT,
                                         null=True, blank=True, related_name='ventas')
    cliente_nombre   = models.CharField(max_length=200, blank=True)
    cliente_telefono = models.CharField(max_length=30, blank=True)
    fecha            = models.DateField(db_index=True)
    estado           = models.CharField(max_length=20, choices=ESTADO_CHOICES,
                                        default='confirmada', db_index=True)
    canal            = models.CharField(max_length=20, choices=CANAL_CHOICES,
                                        default='whatsapp')
    observaciones    = models.TextField(blank=True)
    creado_en        = models.DateTimeField(auto_now_add=True)
    actualizado_en   = models.DateTimeField(auto_now=True)
    creado_por       = models.ForeignKey('auth.User', on_delete=models.SET_NULL,
                                         null=True, blank=True)

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha', '-creado_en']

    def __str__(self):
        nombre = self.cliente.nombre if self.cliente else self.cliente_nombre or 'Sin nombre'
        return f"{self.numero} — {nombre} — {self.fecha}"

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
            ultima = Venta.objects.order_by('-id').first()
            num = (ultima.id + 1) if ultima else 1
            self.numero = f"VENTA-{num:05d}"
        super().save(*args, **kwargs)


class ItemVenta(models.Model):
    venta           = models.ForeignKey(Venta, on_delete=models.CASCADE,
                                        related_name='items')
    producto        = models.ForeignKey('inventario.Producto', on_delete=models.PROTECT,
                                        related_name='items_venta')
    cantidad        = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=0,
                                          validators=[MinValueValidator(0)])
    costo_unitario  = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    descuento       = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                          help_text="Descuento en porcentaje (0-100)")
    observacion     = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Ítem de venta"
        verbose_name_plural = "Ítems de venta"

    def __str__(self):
        return f"{self.venta.numero} | {self.producto.codigo} x{self.cantidad}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario * (1 - self.descuento / 100)

    def save(self, *args, **kwargs):
        if not self.costo_unitario and self.producto_id:
            self.costo_unitario = self.producto.precio_costo
        super().save(*args, **kwargs)


class AdicionalVenta(models.Model):
    """
    Ingresos y egresos adicionales de una venta.
    Ej: delivery cobrado al cliente (ingreso), packaging asumido por el negocio (egreso).
    """
    A_CARGO_CHOICES = [
        ('cliente', 'Lo paga el cliente'),
        ('negocio', 'Lo asume el negocio'),
    ]

    venta       = models.ForeignKey(Venta, on_delete=models.CASCADE,
                                    related_name='adicionales')
    concepto    = models.ForeignKey('gastos.ConceptoAdicional', on_delete=models.PROTECT,
                                    related_name='adicionales_venta')
    descripcion = models.CharField(max_length=200, blank=True,
                                   help_text="Detalle opcional, ej: PedidosYa zona Central")
    monto       = models.DecimalField(max_digits=10, decimal_places=0,
                                      help_text="Positivo=ingreso, Negativo=descuento/egreso")
    a_cargo_de  = models.CharField(max_length=10, choices=A_CARGO_CHOICES, default='cliente')
    comprobante = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Adicional de venta"
        verbose_name_plural = "Adicionales de venta"

    def __str__(self):
        return f"{self.venta.numero} | {self.concepto.nombre} | Gs. {self.monto:,.0f}"
