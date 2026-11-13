# Verdugo Digital — Growth Engineering (reconstrucción)
Esta es la **rama de trabajo** para sustituir el núcleo anterior por exactamente diez sistemas de Growth Engineering. La rama `main` todavía conserva la versión previa. El respaldo verificado está en `backup/pre-growth-ten-20261112`.

## Estado comprobable
- Fuentes upstream localizadas: **10/10**.
- Sistemas descargados e instalados: **0/10**.
- Integraciones entre sistemas validadas: **0/10**.
- Despliegues productivos certificados: **0/10**.
- No se afirma que haya servicios ejecutándose.

El catálogo de `stack/catalog.json` registra los diez proyectos y sus roles. No implica que el código de esas aplicaciones esté copiado, que sus licencias estén revisadas o que sus APIs funcionen.

## Requisitos antes de desplegar
1. Auditar licencias, versiones, imágenes oficiales, requisitos de hardware y costes de cada proyecto.
2. Resolver solapamientos (PostHog/Countly, erxes/Twenty, Mautic/Dittofeed) y fijar autoridad sobre cada dato.
3. Implementar despliegue reproducible con dependencias, secretos aislados, backups y redes privadas.
4. Integrar identificadores, eventos, consentimiento, oportunidades y conversiones entre los sistemas.
5. Ejecutar pruebas reales de extremo a extremo, recuperación, seguridad y rendimiento.

## Verificación de este commit
```sh
python3 -m unittest discover -s tests -v
```
Esta prueba verifica **solo el catálogo**, no la integración ni el despliegue de ningún servicio.

Ver `docs/ARCHITECTURE.md` para el contrato de integración propuesto.
