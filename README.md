# Verdugo Digital — núcleo comercial local

Desarrollo en GitHub; ejecución prevista en Termux. No requiere contratar Railway,
Render ni otro alojamiento para usar el núcleo local. Esta rama sigue siendo una
reconstrucción en curso, **no la integración completa de los diez servidores**.

## Implementado en esta revisión

- Un panel y una API local para capturar prospectos, calificarlos o descartarlos,
  registrar ventas declaradas y actualizar consentimiento.
- SQLite transaccional: historial de eventos, persistencia tras reinicio,
  separación por espacio de trabajo y deduplicación por identificador de evento.
- Ventas en unidades menores enteras, pedidos únicos y totales por moneda
  (MXN, USD, EUR). Son declaraciones del operador, **no cobros conciliados**.
- Cola persistente para dos adaptadores HTTP: PostHog y RudderStack. Están
  desactivados por defecto. Retirar consentimiento cancela trabajos pendientes.
- Los envíos inciertos no se repiten automáticamente. La cola queda ligada al
  destino y credencial originales para no redirigir datos por un cambio de configuración.
- Autenticación local, límite de cuerpo JSON, control de origen/Host y archivos
  privados. Sin campañas, correos, SMS, inversión publicitaria ni cargos externos.

## Estado de los diez proyectos

| Evidencia | Estado |
|---|---|
| Repositorios upstream fijados mediante submódulos | 10/10 |
| Adaptadores de eventos implementados y probados con HTTP local sintético | 2/10: PostHog y RudderStack |
| Aplicaciones upstream instaladas y verificadas | 0/10 |
| Integraciones aceptadas contra proveedores auténticos | 0/10 |
| Flujo E2E de los diez originales | No ejecutado |
| Ejecución del núcleo en el Android del usuario | Pendiente |

El núcleo es código propio; **no sustituye ni reproduce todas las capacidades** de
PostHog, GrowthBook, erxes, Mautic, Dittofeed, RudderStack, OpenReplay, Twenty,
Countly o Formbricks. Los otros ocho adaptadores operativos siguen pendientes.
`stack/catalog.json` conserva el estado no certificado de los diez proveedores.

## Ejecutar

Requiere Node.js >=22.16 con `node:sqlite` disponible; no hay dependencias NPM.
El instalador comprueba esa capacidad antes de continuar. SQLite sigue siendo
experimental en Node 22; su disponibilidad real se comprueba, no se presupone.

```sh
bash scripts/termux-install.sh
node scripts/growth-demo.mjs
bash scripts/termux-run.sh
```

Abrir `http://127.0.0.1:8177` en el mismo equipo. El token se genera localmente en
`~/.config/verdugo/environment`. La base predeterminada está en
`~/.local/share/verdugo/growth.sqlite`, fuera del repositorio. No subir estos datos
ni secretos a GitHub. La demo usa datos sintéticos, borra su base temporal y no
realiza solicitudes externas.

[Instalación y límites en Termux](docs/TERMUX.md) ·
[API y contratos de los adaptadores](docs/GROWTH_CORE.md)

## Verificación

```sh
node --test tests/*.test.mjs
python -m unittest discover -s tests -p 'test_*.py' -v
node scripts/growth-demo.mjs
```

El workflow comprueba Node 22.16 y Node 24 en Linux, el catálogo de diez fuentes,
las transacciones, la API, el aislamiento, el consentimiento y los contratos HTTP
con servidores de prueba locales. **No equivale a probar Android ni a instalar
los diez proveedores**. Consultar la ejecución del commit concreto en Actions.

`main` y `backup/pre-growth-ten-20261112` se conservan. El PR #14 permanece en
borrador hasta la aceptación del alcance completo; no se ha contratado alojamiento.
