from django.core.management.base import BaseCommand
from apps.inventario.models import Producto


# Palabras con capitalización especial que title() o capitalize() arruinaría
PRESERVE_CASE = {w.lower(): w for w in [
    'iPhone', 'MacBook', 'AirPods', 'AirTag', 'iPod', 'iMac',
    'iOS', 'iPadOS', 'macOS', 'watchOS',
    'USB', 'HDMI', 'HD', 'UHD', 'LCD', 'OLED', 'AMOLED', 'LED',
    'TV', 'Wi-Fi', 'WiFi',
    'Samsung', 'Xiaomi', 'Motorola', 'Huawei', 'OnePlus', 'Realme',
    'LG', 'HTC', 'Nokia',
]}


def smart_title(text):
    """Title Case respetando marcas y términos técnicos conocidos."""
    if not text:
        return text
    words = text.split()
    result = []
    for word in words:
        key = word.lower()
        if key in PRESERVE_CASE:
            result.append(PRESERVE_CASE[key])
        else:
            result.append(word.capitalize())
    return ' '.join(result)


class Command(BaseCommand):
    help = 'Normaliza nombre, modelo_celular y color de todos los Productos a Title Case'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Aplicar los cambios (sin este flag solo muestra preview)',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        productos = Producto.objects.all().order_by('codigo')
        cambios = []

        for p in productos:
            nombre_nuevo = smart_title(p.nombre)
            modelo_nuevo = smart_title(p.modelo_celular) if p.modelo_celular else p.modelo_celular
            color_nuevo = smart_title(p.color) if p.color else p.color

            changed = (
                nombre_nuevo != p.nombre
                or modelo_nuevo != p.modelo_celular
                or color_nuevo != p.color
            )
            if changed:
                cambios.append({
                    'producto': p,
                    'nombre_viejo': p.nombre, 'nombre_nuevo': nombre_nuevo,
                    'modelo_viejo': p.modelo_celular, 'modelo_nuevo': modelo_nuevo,
                    'color_viejo': p.color, 'color_nuevo': color_nuevo,
                })

        if not cambios:
            self.stdout.write(self.style.SUCCESS('No se encontraron nombres para normalizar.'))
            return

        self.stdout.write(f'\n{len(cambios)} producto(s) con cambios pendientes:\n')
        for c in cambios:
            p = c['producto']
            self.stdout.write(f'\n  [{p.codigo}]')
            if c['nombre_nuevo'] != c['nombre_viejo']:
                self.stdout.write(f'    nombre:  "{c["nombre_viejo"]}"  →  "{c["nombre_nuevo"]}"')
            if c['modelo_nuevo'] != c['modelo_viejo']:
                self.stdout.write(f'    modelo:  "{c["modelo_viejo"]}"  →  "{c["modelo_nuevo"]}"')
            if c['color_nuevo'] != c['color_viejo']:
                self.stdout.write(f'    color:   "{c["color_viejo"]}"  →  "{c["color_nuevo"]}"')

        if apply:
            for c in cambios:
                p = c['producto']
                p.nombre = c['nombre_nuevo']
                if p.modelo_celular is not None:
                    p.modelo_celular = c['modelo_nuevo']
                if p.color is not None:
                    p.color = c['color_nuevo']
                p.save(update_fields=['nombre', 'modelo_celular', 'color'])
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ {len(cambios)} producto(s) actualizados.')
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    '\n(modo preview — ejecutá con --apply para aplicar los cambios)'
                )
            )
