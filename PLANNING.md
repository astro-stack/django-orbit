# Django Orbit — Planning & Strategy

> **Fuente de verdad interna.** Este archivo es leído por el agente PO antes de escribir cualquier spec.
> Actualizar siempre que cambie la estrategia, el roadmap o las prioridades.

---

## Contexto del producto

**Django Orbit** es un dashboard de observabilidad para Django, publicado en PyPI como `django-orbit` (MIT).
Inspirado en Laravel Telescope. Captura requests, SQL, logs, excepciones, cache, jobs, Redis, etc.
desde `/orbit/` sin interferir con la app host.

- **Estado actual:** v0.8.1, Beta
- **Stars en GitHub:** 160+
- **Modelo de negocio:** Open-core — la librería es gratis y open-source; el revenue futuro viene de Orbit Cloud y features de pago.
- **Usuarios primarios:** Desarrolladores Django (solo devs, equipos pequeños, agencias).

---

## Business Model: Open-Core

```
┌──────────────────────────────────────────────────────────┐
│  TIER FREE (MIT, siempre gratis)                         │
│  • django-orbit en PyPI                                  │
│  • Dashboard self-hosted en /orbit/                      │
│  • Todos los watchers actuales (18 tipos de eventos)     │
│  • MCP Server para IAs                                   │
│  • Storage limit: 1000 entries                           │
│  • Un solo servidor, sin colaboración                    │
└──────────────────────────────────────────────────────────┘
            │
            ├──→  TIER TEAM  (~$29-49/mes)
            │     • Dashboard hosteado (Orbit Cloud)
            │     • 5 desarrolladores con acceso compartido
            │     • Alertas: Slack / email / webhook
            │     • 500K entries/mes, retención 30 días
            │
            └──→  TIER PRO / ENTERPRISE (~$99-199/mes / negociado)
                  • Retención 90 días → 1 año
                  • Equipos ilimitados
                  • AI Insights Engine
                  • Agregación multi-servidor
                  • SSO/SAML
                  • SLA 99.9%
```

---

## Roadmap oficial (público, en README)

| # | Feature | Estado | Descripción |
|---|---|---|---|
| R1 | **Alerting** | Planeado | Notificaciones Slack / email / webhook para excepciones y requests lentos |
| R2 | **VS Code / Cursor Extension** | Planeado | Panel de Orbit en el sidebar del editor mientras se codea |
| R3 | **AI Insights Engine** | Planeado | Detección automática de patrones + resúmenes en lenguaje natural vía LLM |
| R4 | **Orbit Cloud** | Planeado | Dashboards compartidos en equipo con retención histórica |

---

## Estrategias de monetización

### Estrategia A — Orbit Cloud (SaaS) ★★★ Mayor revenue a largo plazo

**Qué es:** Versión hosteada de Orbit donde el equipo comparte el dashboard, ve datos históricos y configura alertas.

**¿Qué tan difícil es montar la infraestructura?**

El stack mínimo viable para Orbit Cloud es un Django app separada que recibe datos y los sirve:

```
django-orbit (librería)
    └─→ envía datos via HTTP a →  Orbit Cloud API
                                       ├─ Django + DRF (ingestión)
                                       ├─ PostgreSQL (storage)
                                       ├─ Redis (colas / websockets)
                                       ├─ Celery (procesamiento async)
                                       └─ UI hosteada (Nginx + Gunicorn)
```

**Fases de complejidad:**

| Fase | Complejidad | Tiempo estimado | Descripción |
|---|---|---|---|
| **Fase 1 — MVP Cloud** | ★★☆ Media | 4-8 semanas | App Django hosteada en Railway/Fly.io + autenticación de usuarios + backend HTTP para recibir OrbitEntry desde la librería |
| **Fase 2 — Billing** | ★★★ Media-Alta | 2-4 semanas | Stripe Checkout + webhooks + plan limits (entries/mes, seats) |
| **Fase 3 — Multi-tenancy** | ★★★ Media-Alta | 3-6 semanas | Aislamiento de datos por proyecto/organización, roles (admin/viewer) |
| **Fase 4 — Alertas** | ★★☆ Media | 2-3 semanas | Rules engine + Slack/email webhooks |
| **Fase 5 — AI Insights** | ★★★ Alta | 4-8 semanas | LLM calls sobre datos de telemetría, summaries semanales |

**Lo más difícil:**
- Multi-tenancy seguro (datos aislados por cliente)
- Ingestión de alto volumen sin perder datos (colas)
- Billing con plan limits en tiempo real

**Lo más fácil de empezar:**
- Railway/Fly.io resuelve hosting y PostgreSQL con un click
- Django + Stripe tiene excelentes librerías (dj-stripe)
- El UI del Cloud puede reusar el 80% del template actual de Orbit

**Cambio requerido en la librería (mínimo):**
```python
# settings.py del usuario
ORBIT_CONFIG = {
    "CLOUD_ENDPOINT": "https://cloud.orbit.dev/ingest/",
    "CLOUD_API_KEY": "sk-orbit-xxxx",
    "CLOUD_PROJECT": "my-app-prod",
}
```
Se agrega un backend `CloudBackend` que envía `OrbitEntry` via HTTP en background. El usuario self-hosted no se ve afectado.

**Conclusión:** No es imposible, pero requiere un proyecto separado paralelo a la librería. **El MVP viable es 6-10 semanas de trabajo.** Se recomienda empezar después de tener Alerting implementado (que puede ser parte del Cloud).

---

### Estrategia B — VS Code / Cursor Extension ★ La más rápida de lanzar

**Qué es:** Extensión gratuita de VS Code que muestra el panel de Orbit en el sidebar mientras se codea. Al abrir un archivo, muestra las últimas queries/errores relacionados.

**¿Por qué es la más rápida?**
- Se construye **encima del MCP Server que ya existe** en v0.7.0
- Las extensiones de VS Code son TypeScript puro, bien documentadas
- Distribución gratuita vía VS Code Marketplace (tracción orgánica)
- No requiere infraestructura externa — conecta al Orbit local del developer

**Stack:**
```
VS Code Extension (TypeScript)
    └─→ llama al MCP Server local de Orbit (stdio)
         ├─ get_recent_requests()
         ├─ get_slow_queries()
         ├─ get_exceptions()
         └─ get_request_detail()
```

**Features del MVP:**
- Panel lateral "Orbit" con últimos requests, errores y queries lentas
- Al abrir un archivo `.py`, filtra entries relacionadas (por stack trace)
- Badge en la barra de estado: `Orbit: 3 errores | P95: 240ms`
- Un click para abrir el detalle completo en el browser

**Complejidad:** ★☆☆ Baja — 2-3 semanas para un MVP funcional.

**Monetización indirecta:** La extensión es gratuita pero convierte users self-hosted en usuarios de Orbit Cloud (el panel mostraría CTA "Ver historial en Orbit Cloud").

**Repositorio:** Proyecto separado `astro-stack/orbit-vscode` (o `orbit-cursor`).

---

### Estrategia C — Licencia comercial (django-orbit-pro) ★★ Revenue sin infraestructura

**Qué es:** Un modelo de doble licencia donde el core es MIT pero features enterprise están bajo licencia comercial paga.

**¿Cómo funciona el dual licensing?**

No es complicado — es básicamente un paquete PyPI separado que requiere una license key:

```
django-orbit          → MIT, gratis, siempre
django-orbit-pro      → Licencia comercial, requiere ORBIT_PRO_LICENSE_KEY en settings
```

**Cómo valida la licencia (sin servidor):**
```python
# orbit_pro/license.py
import hmac, base64, json

def validate_license(key: str) -> bool:
    # El key es un JWT firmado con tu clave privada.
    # La validación es local — no llama a ningún servidor.
    # Solo verificas la firma + fecha de expiración.
    payload = jwt.decode(key, PUBLIC_KEY, algorithms=["RS256"])
    return payload["product"] == "orbit-pro" and not is_expired(payload)
```

El usuario compra la key una vez (o anualmente) en Gumroad / LemonSqueezy / Polar.sh. No hay servidor de licencias que mantener.

**Features candidatas para `orbit-pro`:**

| Feature | Por qué es "pro" |
|---|---|
| **Export a DataDog / Grafana / New Relic** | Integración con stacks enterprise |
| **RBAC (roles en el dashboard)** | Admin, viewer, dev — para equipos |
| **Compliance audit logs** | HIPAA / SOC2 — inmutables, exportables |
| **Custom data retention policies** | Más de 1000 entries, TTL configurable |
| **Performance regression alerts (local)** | Baseline + threshold, sin cloud |
| **Request replay** | Reproducir requests capturados contra el server |
| **Query optimizer suggestions** | Sugerir `select_related()` exacto cuando hay N+1 |

**Precios sugeridos:**
- Licencia perpetua individual: $49 one-time (Gumroad)
- Licencia anual por organización: $199/año (incluye actualizaciones)
- Enterprise (sin límite de proyectos): $499/año

**Plataformas de distribución:**
- **Polar.sh** — diseñada para open-source (permite "patrocinar" + comprar features)
- **LemonSqueezy** — simple, cero fees hasta cierto volumen
- **Gumroad** — la más conocida para software de nicho

**Complejidad:** ★★☆ Media — 3-4 semanas para implementar el sistema de licencias + 2-3 features pro iniciales.

---

## Ideas nuevas (backlog de features)

### Herramientas de productividad

| ID | Feature | Complejidad | Impacto | Descripción |
|---|---|---|---|---|
| I1 | **Query optimizer suggestions** | ★★☆ | Alto | Al detectar N+1, mostrar el `select_related()` o `prefetch_related()` exacto que lo resuelve, con el modelo y field correcto |
| I2 | **Performance regression tracking** | ★★☆ | Alto | Comparar P95 de esta semana vs. la anterior en `/orbit/stats/`. Alerta visual si sube >20% |
| I3 | **Request replay** | ★★★ | Medio | Reproducir cualquier request capturado enviándolo nuevamente al servidor actual (útil en debug mode) |
| I4 | **Diff de payloads** | ★☆☆ | Medio | Comparar el body/response de dos requests side-by-side en el dashboard |
| I5 | **Custom event types** | ★★☆ | Medio | API pública para que el usuario registre sus propios tipos de eventos con payload custom |

### Integraciones que generan tracción

| ID | Feature | Complejidad | Impacto | Descripción |
|---|---|---|---|---|
| I6 | **pytest plugin** | ★★☆ | Alto | Captura queries/requests durante tests; falla si detecta N+1 o supera un threshold de queries |
| I7 | **GitHub Actions integration** | ★★★ | Alto | Report de performance en cada PR: P95, error rate, slow queries vs. main branch |
| I8 | **Django REST Framework watcher** | ★★☆ | Alto | Watcher específico DRF: serializer timing, viewset name, throttle hits, schema info |
| I9 | **Django Channels watcher** | ★★★ | Medio | Captura WebSocket connections, messages, disconnect events |
| I10 | **Stripe / payment watcher** | ★★☆ | Medio | Watcher para Stripe webhooks: payment intents, charge events, subscription changes |

### AI-native features

| ID | Feature | Complejidad | Impacto | Descripción |
|---|---|---|---|---|
| I11 | **Auto-diagnosis en dashboard** | ★★★ | Alto | LLM analiza las queries lentas y N+1 del request actual → sugiere fix en lenguaje natural directamente en el detail panel |
| I12 | **Weekly digest email** | ★★☆ | Alto | Resumen semanal generado por LLM: "Tu app tuvo 3 regresiones; `/api/users/` empeoró 40ms; 2 N+1 nuevos" |
| I13 | **Anomaly detection** | ★★★ | Alto | Baseline de comportamiento normal + alerta cuando el error rate, latencia o queries/request se desvían estadísticamente |
| I14 | **Code attribution** | ★★★ | Medio | Linkear queries lentas al archivo y línea de código origen (stack trace parsing + git blame) |

### Ecosistema y comunidad

| ID | Feature | Complejidad | Impacto | Descripción |
|---|---|---|---|---|
| I15 | **Watcher marketplace / registry** | ★★★ | Medio | Repositorio de watchers de terceros publicables en PyPI (`orbit-watcher-stripe`, `orbit-watcher-aws-s3`) |
| I16 | **Share entry (URL temporal)** | ★★☆ | Alto | Generar una URL pública y temporal para compartir un trace específico sin que el receptor tenga acceso al dashboard |
| I17 | **Status badge para README** | ★☆☆ | Medio | `![Orbit: healthy](...)` que sirva un SVG con el health status actual del proyecto |
| I18 | **Orbit Toolbar (minimal)** | ★★☆ | Alto | Mini-bar opcional (non-injected) que flota en la esquina del browser durante desarrollo, similar a Debug Toolbar pero sin inyección DOM |

---

## Priorización recomendada

### Próximos 2 meses — Consolidar el core y tracción

```
1. Alerting (R1)                   — roadmap existente, alta demanda, necesario para Cloud
2. pytest plugin (I6)              — nuevo canal de usuarios, diferenciador técnico
3. Query optimizer suggestions (I7)— diferenciador vs. debug_toolbar, facil de mostrar en demos
4. VS Code / Cursor Extension (R2) — aumenta DAU, base para monetización Cloud
```

### 2-6 meses — Monetización

```
5. django-orbit-pro (Estrategia C) — revenue sin infraestructura, validación de willingness to pay
6. Orbit Cloud Beta (Estrategia A) — waitlist → beta → pricing validation
7. AI Insights Engine (R3)         — diferenciador premium, feature star del Cloud tier
```

### 6+ meses — Escala

```
8. GitHub Actions integration (I7)
9. Watcher marketplace (I15)
10. Performance regression tracking (I2)
11. Orbit Cloud GA + Enterprise tier
```

---

## Decisiones tomadas

| Decisión | Fecha | Razonamiento |
|---|---|---|
| Modelo open-core (no dual-license puro) | 2026-04 | La librería MIT maximiza adopción; el Cloud es el revenue principal |
| MIT license (no BSL/AGPL) | 2026-04 | Facilita adopción en empresas; sin fricción de compliance |
| Single-table `OrbitEntry` con JSONField | 2025-12 | Simplicidad de migrations; permite agregar tipos sin schema changes |
| `WATCHER_FAIL_SILENTLY` irrompible | 2025-12 | La app host nunca puede crashear por culpa de Orbit |

---

## Anti-patrones a evitar

- **No inyectar HTML en templates del usuario** — Orbit vive en `/orbit/`, nunca en la app
- **No forzar dependencias** — todo opcional, watchers fallan silenciosamente si la lib no está
- **No duplicar lo que Sentry hace bien** — Orbit es para debugging en desarrollo, no alerting en producción (eso es el Cloud tier)
- **No sobre-indexar en enterprise antes de validar** — construir Cloud MVP antes de features enterprise complejas
