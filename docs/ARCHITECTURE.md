# Arquitectura objetivo — diez sistemas

| Sistema | Responsabilidad propuesta | Criterio de aceptación pendiente |
|---|---|---|
| RudderStack | Puerta de entrada de eventos de visitantes y ventas | Esquemas, idempotencia y reparto comprobados |
| PostHog | Analítica principal y embudos | Ingesta de eventos y consulta coherente |
| Countly | Analítica secundaria delimitada | Sin doble contabilización |
| OpenReplay | Sesiones y análisis de fricción | Consentimiento, retención y control PII |
| Formbricks | Captura de feedback | Relación del feedback con sesiones autorizadas |
| GrowthBook | Decisiones de experimentación | Asignación, exposición y resultados sin sesgo |
| erxes | Automatización comercial específica | Contrato CRM y roles delimitados |
| Twenty | Registro autorizado de oportunidades | Identificadores y estado de venta deduplicados |
| Mautic | Captación y lead nurturing | Consentimiento y límites de envíos |
| Dittofeed | Journeys y retención | Exclusión mutua de mensajes y opt-out |

## Flujo deseado
Visitante -> eventos consentidos -> RudderStack -> PostHog/Countly -> análisis y experimentación.
Formulario -> registro CRM en Twenty -> cambios comerciales sincronizados con erxes bajo contratos explícitos.
Mautic y Dittofeed consumen segmentos aprobados, con reglas para evitar campañas duplicadas.
Formbricks y OpenReplay generan señales auxiliares, nunca sustituyen eventos de venta conciliados.

## Decisiones de ingeniería obligatorias
- **Una autoridad por campo**: Twenty debe ser CRM maestro o se debe justificar otra elección; no dos registros maestros.
- **Una clave canónica de identidad** por cliente y consentimiento; anonimización y revocación verificables.
- **Eventos versionados** con deduplicación, tratamiento de retrasos y procesamiento idempotente.
- **Separación de tenants**, secretos en gestor seguro, control de acceso y auditoría.
- **Métricas**: visitas -> lead válido -> oportunidad -> venta conciliada -> margen; experimentos con controles.
- **Pruebas**: arranque de diez servicios, healthchecks reales, persistencia, eventos cruzados, rollback y tests E2E.
- **Puertas de activación**: nada de envíos o campañas en producción hasta consentimiento y controles operativos.

## Alcance de esta primera revisión
Únicamente manifiesto y pruebas estáticas. No se han instalado los diez repositorios, levantado contenedores, autenticado APIs ni ejecutado flujos comerciales.
