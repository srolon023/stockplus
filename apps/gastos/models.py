from django.db import models
from django.core.validators import MinValueValidator


class ConceptoAdicional(models.Model):
    """
    Lista precargada de conceptos para usar en compras, ventas y gastos generales.
    El admin puede agregar nuevos cuando quiera.
    """
    TIPO_CHOICES = [
        ('egreso',  'Egreso (costo)'),
        ('ingreso', 'Ingreso'),
    ]
    APLICA_CHOICES = [
        ('compra',  'Compras'),
        ('venta',   'Ventas'),
        ('gasto',   'Gasto general'),
        ('todos',   'Todos'),
    ]

    nombre      = models.CharField(max_length=100, unique=True)
    tipo        = models.CharField(max_length=10, choices=TIPO_CHOICES, default='egreso')
    aplica_a    = models.CharField(max_length=10, choices=APLICA_CHOICES, default='todos')
    descripcion = models.CharField(max_length=200, blank=True)
    activo      = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Concepto adicional"
        verbose_name_plural = "Conceptos adicionales"
        ordering = ['aplica_a', 'nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class GastoGeneral(models.Model):
    """
    Gastos que no están ligados a una compra ni venta específica.
    Ej: publicidad en Meta, dominio, materiales de oficina.
    """
    concepto    = models.ForeignKey(ConceptoAdicional, on_delete=models.PROTECT,
                                    related_name='gastos')
    descripcion = models.CharField(max_length=200,
                                   help_text="Detalle específico del gasto")
    monto       = models.DecimalField(max_digits=12, decimal_places=0,
                                      validators=[MinValueValidator(0)])
    fecha       = models.DateField(db_index=True)
    comprobante = models.CharField(max_length=100, blank=True,
                                   help_text="Número de factura o recibo")
    observacion = models.TextField(blank=True)
    creado_en   = models.DateTimeField(auto_now_add=True)
    creado_por  = models.ForeignKey('auth.User', on_delete=models.SET_NULL,
                                    null=True, blank=True)

    class Meta:
        verbose_name = "Gasto general"
        verbose_name_plural = "Gastos generales"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.fecha} | {self.concepto.nombre} | Gs. {self.monto:,.0f}"
