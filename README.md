# Ekoparty Guardrails Demo

Demo reproducible que acompaña al artículo **"Guardrails más allá del modelo:
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

Todo vive en `guardrail_hook.py`, en una sola clase `GuardrailHook`. Cada
checkpoint imprime en consola cuando interviene, con el prefijo `[GUARDRAIL]`.

## Estructura

```
ekoparty-guardrails-demo/
├── guardrail_hook.py     # La clase GuardrailHook (los tres checkpoints)
├── tools.py              # web_search y get_customer_data (herramientas de ejemplo)
├── agente_inseguro.py    # Agente SIN hook — muestra el ataque exitoso
├── agente_seguro.py      # Agente CON hook — muestra el bloqueo
├── attack_doc.txt        # "Documento externo" con la inyección indirecta
├── requirements.txt
├── infra/                # CDK (Python) que crea los dos guardrails en AWS
│   ├── app.py
│   ├── cdk.json
│   ├── requirements.txt
│   └── guardrails_demo/
│       └── guardrails_stack.py
└── README.md
```

## Prerrequisitos

- Una cuenta de AWS con acceso a Amazon Bedrock y el modelo **Amazon Nova Pro**
  habilitado (`us.amazon.nova-pro-v1:0`) en `us-east-2`.
- Python 3.11 o superior.
- [Node.js](https://nodejs.org/) y el [AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)
  (`npm install -g aws-cdk`) para crear los guardrails.
- Credenciales de AWS configuradas con permisos para crear guardrails de Bedrock
  (CloudFormation + `bedrock:CreateGuardrail`), y para correr la demo,
  `bedrock:ApplyGuardrail` y `bedrock:InvokeModel`.

Los dos guardrails que necesita la demo (uno para `web_search`, otro para
`get_customer_data`) los crea el stack de CDK en `infra/`. No hace falta crearlos
a mano en la consola.

## Crear los recursos en AWS (CDK)

El stack `infra/` despliega dos [Amazon Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html):

- `ekoparty-websearch`: filtro de contenido, para la salida de `web_search`.
- `ekoparty-customerdata`: detección de PII (email, tarjeta, SSN, teléfono), para
  los parámetros de `get_customer_data`.

```bash
cd infra
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Solo la primera vez en la cuenta/región:
cdk bootstrap

cdk deploy
```

Al terminar, el deploy imprime tres salidas: `WebSearchGuardrailId`,
`CustomerDataGuardrailId` y `GuardrailVersion`. Los vas a usar en el paso
siguiente.

## Instalar la demo

Desde la raíz del repo (no desde `infra/`):

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

Exporta los IDs que imprimió `cdk deploy`:

```bash
export GR_WEBSEARCH_ID="<WebSearchGuardrailId>"
export GR_CUSTOMERDATA_ID="<CustomerDataGuardrailId>"
export GR_VERSION="DRAFT"
```

Luego corre el agente seguro. Acepta un argumento (`1`, `2` o `3`) que elige qué
checkpoint demostrar; sin argumento usa el `3` por defecto:

```bash
python agente_seguro.py 1   # Checkpoint 1 — bloquea la ENTRADA del usuario
python agente_seguro.py 2   # Checkpoint 2 — bloquea los PARAMETROS de get_customer_data
python agente_seguro.py 3   # Checkpoint 3 — bloquea la SALIDA de web_search (default)
```

Cada opción usa un prompt distinto, pensado para disparar un checkpoint:

- **`1` — Entrada.** El prompt del usuario pide contenido de odio/violencia. El
  content filter lo bloquea en `validate_inbound` antes de que el modelo lo vea.
- **`2` — Parámetros.** El prompt mete PII (email + tarjeta) como `customer_id`.
  Cuando el modelo intenta llamar `get_customer_data` con ese parámetro, el
  guardrail de PII cancela la llamada en `validate_input`.
- **`3` — Salida.** El prompt es inocente; el ataque vive en el contenido externo
  que trae `web_search`. El guardrail valida ese resultado en `validate_output` y
  lo reemplaza por un mensaje de bloqueo antes de llegar al modelo.

En cada caso verás en consola la línea `[GUARDRAIL] Checkpoint N ...` indicando
qué checkpoint intervino, y la respuesta final no contendrá la PII.

## Criterio de éxito

- `agente_inseguro.py`: la respuesta final contiene el email y la tarjeta (ataque exitoso).
- `agente_seguro.py`: la respuesta final contiene el mensaje de bloqueo del guardrail, no la PII.

## Costos

Esta demo usa servicios de pago por uso. Tenlo en cuenta antes de desplegar:

- **Crear los guardrails con CDK no genera cargo por sí mismo.** Amazon Bedrock
  Guardrails se cobra por uso, cuando llamas a `ApplyGuardrail`, no por tener el
  guardrail creado. Un guardrail inactivo en tu cuenta no cuesta nada.
- **Correr la demo sí genera cargos**, pequeños pero reales: cada corrida invoca
  el modelo Amazon Nova Pro (se cobra por tokens de entrada y salida) y evalúa el
  contenido con los guardrails (se cobra por unidad de texto, separado por filtro
  de contenido y por detección de PII). Para unas pocas corridas de prueba el
  costo es de centavos, pero depende de tu región y del volumen.
- El stack de CDK **no crea recursos con costo fijo mensual** (no hay VPC, NAT,
  endpoints ni nada que cobre por hora). Solo crea los dos guardrails.
- Consulta los precios vigentes en [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/)
  (secciones de Guardrails y de los modelos Amazon Nova) antes de correr la demo a
  gran escala.

## Destruir los recursos

Cuando termines, borra todo para no dejar nada en la cuenta:

```bash
cd infra
source .venv/bin/activate   # si no está activo
cdk destroy
```

`cdk destroy` elimina los dos guardrails (es el único recurso que creó el stack).
Confirma con `y` cuando lo pida. Después de esto no queda nada de la demo en tu
cuenta de AWS.

Si corriste `cdk bootstrap` solo para esta demo y no lo usas para nada más,
puedes borrar también el stack `CDKToolkit` desde la consola de CloudFormation.
Si usas CDK para otros proyectos, déjalo.

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
