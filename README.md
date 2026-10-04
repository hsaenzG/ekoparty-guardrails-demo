# Ekoparty Guardrails Demo

Demo reproducible que acompaña al artículo **"Guardrails en las herramientas:
cierra la brecha que tu agente deja abierta"** y a la charla de Ekoparty 2026
*"Tu agente obedece a cualquiera"*.

Muestra cómo extender [Amazon Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)
desde el límite del modelo hasta el límite de las herramientas de un agente
[Strands](https://strandsagents.com/), con tres checkpoints de validación
construidos sobre los hooks del ciclo de vida del SDK y la API `ApplyGuardrail`.

El agente de ejemplo tiene dos herramientas:

- `web_search`: simula una búsqueda web que trae contenido externo no confiable.
- `get_customer_data`: simula un registro interno con PII.

La demo corre el mismo flujo dos veces: una sin guardrails (el ataque funciona) y
otra con el `GuardrailHook` registrado (el ataque se corta).

## El ataque: inyección indirecta

`attack_doc.txt` es el "documento externo" que `web_search` trae. Adentro esconde
una instrucción que le pide al agente llamar a `get_customer_data` y devolver el
email y la tarjeta del cliente. El payload no viene del usuario, viene del
contenido que la herramienta trajo de afuera. Por eso el guardrail del modelo no
lo atrapa: nunca pasó por la entrada del modelo como prompt del usuario.

## Los tres checkpoints

| Checkpoint | Qué valida | Hook |
|---|---|---|
| 1. Entrada | Lo que llega al modelo | `BeforeInvocationEvent` |
| 2. Herramienta | Los parámetros antes de ejecutar la herramienta | `BeforeToolCallEvent` |
| 3. Salida | El resultado que devuelve la herramienta | `AfterToolCallEvent` |

Todo vive en `guardrail_hook.py`, en una sola clase `GuardrailHook`.

## Estructura

```
ekoparty-guardrails-demo/
├── guardrail_hook.py     # La clase GuardrailHook (los tres checkpoints)
├── tools.py              # web_search y get_customer_data (herramientas de ejemplo)
├── agente_inseguro.py    # Agente SIN hook — muestra el ataque exitoso
├── agente_seguro.py      # Agente CON hook — muestra el bloqueo
├── attack_doc.txt        # "Documento externo" con la inyección indirecta
├── requirements.txt
└── README.md
```

## Prerrequisitos

- Una cuenta de AWS con acceso a Amazon Bedrock y el modelo **Amazon Nova Pro**
  habilitado (`us.amazon.nova-pro-v1:0`) en `us-east-1`.
- Un [Amazon Bedrock Guardrail](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-create.html)
  creado, con detección de PII y filtro de contenido. Anota su `guardrail_id` y
  su versión (usa `DRAFT` para pruebas). Para la demo con guardrails distintos
  por herramienta, crea dos (uno para `web_search`, otro para `get_customer_data`).
- Python 3.11 o superior.
- Credenciales de AWS configuradas con permisos `bedrock:ApplyGuardrail` y
  `bedrock:InvokeModel`.

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Correr la demo

### 1. El ataque funciona (sin guardrails)

```bash
python agente_inseguro.py
```

El agente busca en la web, lee la inyección y termina devolviendo el email y la
tarjeta del cliente. **El camino feliz es inseguro.**

### 2. El ataque se corta (con el GuardrailHook)

Primero exporta los IDs de tus guardrails:

```bash
export GR_WEBSEARCH_ID="tu-guardrail-id-para-web-search"
export GR_CUSTOMERDATA_ID="tu-guardrail-id-para-datos-de-cliente"
export GR_VERSION="DRAFT"
```

Luego corre el agente seguro:

```bash
python agente_seguro.py
```

Ahora el resultado de `web_search` se valida en el checkpoint 3 y se reemplaza
por un mensaje de bloqueo antes de llegar al modelo. Si el modelo igual intenta
pasar PII a `get_customer_data`, el checkpoint 2 cancela la llamada.

## Criterio de éxito

- `agente_inseguro.py`: la respuesta final contiene el email y la tarjeta (ataque exitoso).
- `agente_seguro.py`: la respuesta final contiene el mensaje de bloqueo del guardrail, no la PII.

## Notas

- Las herramientas están simuladas a propósito para que la demo sea reproducible
  sin dependencias externas ni datos reales. La PII es ficticia.
- El `GuardrailHook` es un `HookProvider` standalone: el mismo paquete sirve para
  varios agentes, se despliega igual en Lambda, ECS o Amazon Bedrock AgentCore
  Runtime, y le inyectas el guardrail ID por entorno sin tocar el código del agente.

## Referencias

- [Extend Amazon Bedrock Guardrails to Tool Interactions Using the Strands Agents SDK (AWS Security Blog)](https://aws.amazon.com/blogs/security/extend-amazon-bedrock-guardrails-to-tool-interactions-using-the-strands-agents-sdk/)
- [Amazon Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)
- [Strands Agents SDK — Hooks](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/agents/hooks/)
- [OWASP Top 10 for Agentic Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
