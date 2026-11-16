# Prompt para Astra — los 666

> **ARCHIVADO (15 nov 2026, decisión del dueño):** Verdugo Digital se queda en **300 piezas libres**. Este catálogo de ampliación no se integra. Se conserva solo como referencia; no es una cola de trabajo. Los PR #24 y #25 quedaron cerrados sin fusionar.

Copia y pega esto al empezar cada sesión con Astra.

```
Trabajas en el repo github.com/josuechavando350-png/Verdugo-Digital, rama base main.

Lee primero, en este orden: AGENTS.md, docs/PLAN_666.md, sources/simulador-mercado.json, sources/cerebro-150.json y sources/final-166.json.

Tu trabajo: construir Verdugo hasta los 666 siguiendo la tabla "Orden de construcción" de docs/PLAN_666.md. Haz UNA tanda por sesión, de máximo 50 piezas, en orden: Tanda 0, luego 1, 2, 3... Antes de empezar, revisa en docs/PLAN_666.md y en los PR abiertos cuál fue la última tanda terminada y continúa con la siguiente.

Reglas que no se rompen:
1. Nada de pago. Ningún proveedor de pago, ni como opción.
2. Nunca escribas license_policy_exception. Solo el dueño puede.
3. Licencia leída del LICENSE en el commit fijado. En libre_nucleo, no uses la parte enterprise, Pro o ee.
4. Antes de usar un modelo, lee la licencia de sus PESOS. Si no es libre, usa otro modelo libre.
5. Cada ruta, encabezado y formato de respuesta debe salir del código original en el commit fijado, con la evidencia guardada (repositorio, commit, ruta, blob sha, sha256). Si el código no lo respalda, la pieza queda pendiente. No adivines y no uses documentación como sustituto sin decirlo.
6. Nada se marca conectado ni verificado sin evidencia. live_verified solo con prueba real.
7. Toda acción con efecto (publicar, enviar, gastar, crear campañas) va en dry-run por defecto y exige aprobación explícita del operador, con idempotencia y registro en SQLite. Programar el repo no autoriza a lanzar campañas, mandar mensajes a terceros ni contratar hosting.
8. Sin datos privados persistidos; solo recuentos. Sin raspado contra términos de servicio, sin suplantar navegadores, sin APIs no oficiales.
9. No toques nada de Cano ni de Vercel. El repo es público: sin secretos ni nombres de clientes.
10. No fusiones a main. Abre un PR por tanda, encadenado al anterior.

Al terminar la tanda:
- Corre todas las pruebas y deja verdes los tres workflows.
- Actualiza docs/PLAN_666.md marcando la tanda como terminada, con números reales.
- En la descripción del PR, separa lo comprobado de lo que no, y lista lo que quedó pendiente y por qué.
- Dime en 5 líneas: qué conectaste, qué quedó pendiente, qué falló y cuál es la siguiente tanda.
```
