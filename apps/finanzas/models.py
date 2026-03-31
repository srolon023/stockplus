from django.db import models


class Movimiento(models.Model):
    """
    Movimientos financieros manuales: inversiones, retiros y ajustes.
    Los movimientos de ventas, compras y gastos se derivan de sus respectivos módulos.
    """
    TIPO_CHOICES = [
        ('inversion_entrada', 'Inversión entrada'),
        ('inversion_salida',  'Inversión salida'),
        ('retiro',            'Retiro'),
        ('ajuste',            'Ajuste'),
    ]

    fecha           = models.DateField(db_index=True)
    tipo            = models.CharField(max_length=20, choices=TIPO_CHOICES, db_index=True)
    descripcion     = models.CharField(max_length=300)
    monto           = models.DecimalField(max_digits=14, decimal_places=0,
                                          help_text="Positivo = entrada de dinero, Negativo = salida")
    referencia_tipo = models.CharField(max_length=50, blank=True)
    referencia_id   = models.PositiveIntegerField(null=True, blank=True)
    creado_en       = models.DateTimeField(auto_now_add=True)
    creado_por      = models.ForeignKey('auth.User', on_delete=models.SET_NULL,
                                        null=True, blank=True)

    class Meta:
        verbose_name = 'Movimiento financiero'
        verbose_name_plural = 'Movimientos financieros'
        ordering = ['-fecha', '-creado_en']

    def __str__(self):
        return f"{self.fecha} | {self.get_tipo_display()} | Gs. {self.monto:,.0f}"

    @property
    def es_ingreso(self):
        return self.tipo == 'inversion_entrada' or (self.tipo == 'ajuste' and self.monto > 0)
