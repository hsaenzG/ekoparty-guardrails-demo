"""
Agente CON el GuardrailHook registrado.

Mismo flujo que agente_inseguro.py, pero con dos guardrails acotados por
herramienta:

  web_search        -> filtro de salida estricto (checkpoint 3). El contenido
                       externo con la inyeccion se bloquea antes de llegar al modelo.
  get_customer_data -> deteccion de PII (checkpoint 2). Si el modelo intenta
                       pasar o retornar PII, la llamada se cancela.

Reemplaza los guardrail_id por los de tu cuenta (consola de Bedrock > Guardrails).
Usa la version "DRAFT" para pruebas o un numero de version publicada.

Correr:  python agente_seguro.py
"""

import os

from strands import Agent
from strands.models import BedrockModel

from guardrail_hook import GuardrailHook
from tools import web_search, get_customer_data

REGION = "us-east-1"
MODEL_ID = "us.amazon.nova-pro-v1:0"

# IDs de guardrail inyectados por entorno. Exporta estas variables antes de correr:
#   export GR_WEBSEARCH_ID=...   export GR_CUSTOMERDATA_ID=...
GR_WEBSEARCH_ID = os.environ.get("GR_WEBSEARCH_ID", "gr-websearch-id")
GR_CUSTOMERDATA_ID = os.environ.get("GR_CUSTOMERDATA_ID", "gr-customerdata-id")
GR_VERSION = os.environ.get("GR_VERSION", "DRAFT")

model = BedrockModel(model_id=MODEL_ID, region_name=REGION)

# Filtro de salida estricto para el contenido externo del web search.
web_search_hook = GuardrailHook(
    guardrail_id=GR_WEBSEARCH_ID,
    guardrail_version=GR_VERSION,
    region_name=REGION,
    tool_names={"web_search"},
)

# Deteccion de PII para la herramienta de datos de cliente.
customer_data_hook = GuardrailHook(
    guardrail_id=GR_CUSTOMERDATA_ID,
    guardrail_version=GR_VERSION,
    region_name=REGION,
    tool_names={"get_customer_data"},
)

agent = Agent(
    model=model,
    tools=[web_search, get_customer_data],
    system_prompt="You are a helpful assistant.",
    hooks=[web_search_hook, customer_data_hook],  # cada hook corre solo para su herramienta
)

if __name__ == "__main__":
    prompt = "Resume las ultimas novedades de seguridad en IA."
    print(f"\n>>> Usuario: {prompt}\n")
    print(agent(prompt))
