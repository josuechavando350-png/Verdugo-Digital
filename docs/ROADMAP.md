# Continuación verificable

## Entregado en esta base

Catálogo de 100 IDs, 12 recetas API, entrada única CLI/MCP, DAG, datos entre pasos, aprobación por lote, idempotencia persistente, separación tenant/dataset/moneda, auditoría de ejecución y demo comercial local. Todas las conexiones externas están desactivadas al generar configuración.

## Siguiente puerta: primeros proveedores reales

1. Disponer de un host autorizado, workspace de pruebas y presupuesto definido; no se ha contratado infraestructura.
2. Revisar licencia/edición, fijar artefacto y verificar schema real de Twenty, Chatwoot y Activepieces. Las APIs pueden requerir permisos o modalidades comerciales específicas.
3. Configurar secretos por empresa fuera de Git. Ejecutar lectura de aceptación y puente de contacto en sandbox; guardar IDs/fechas/evidencia de resultado, sin publicar datos personales.
4. Establecer webhooks autenticados, identidad canónica entre sistemas, normalización y reconciliación. Actualmente los eventos son internos; no hay suscripción a webhooks de los 100 proveedores.

## Integraciones restantes

88 proyectos solo tienen registro y lugar lógico en la arquitectura. Requieren implementación específica: servicios HTTP, bibliotecas Python/JS, procesos de render y voz, herramientas de datos/modelado, comercio/facturación, identidad, CI y backups. No inventar una API genérica para bibliotecas que no la tienen.

Cada adaptador nuevo debe declarar acciones, contratos de entrada/salida, permisos, costos, versión, pruebas de contrato y prueba viva en entorno autorizado. Los sustitutos pueden configurarse por cliente sin hacer que todos sean simultáneamente fuentes de verdad.

## Antes de producción multiempresa

SSO/autorización real; secretos por ámbito; protección/cifrado/retención de datos; restauración probada; modelo de estados inciertos y conciliación; colas/workers durables y límites por cliente; políticas de gasto; pruebas de carga y fallos; lock de artefactos y SBOM; auditoría independiente. SQLite local es una decisión de arranque, no una afirmación de escalabilidad horizontal.

## Antes de prometer dinero o una tasa de éxito

Clientes reales pagados, conciliación de cobros y costos, capacidad de entrega y una métrica de éxito definida. Los registros declarados, una simulación y pruebas de software no demuestran rentabilidad, causalidad ni una probabilidad del 90%.
