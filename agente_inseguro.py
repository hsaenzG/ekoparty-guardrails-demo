"""
Agente SIN guardrails en las herramientas.

Muestra el camino feliz inseguro: el usuario pide algo inocente, el agente busca
en la web, lee la inyeccion indirecta escondida en el contenido externo, y
termina llamando a get_customer_data y filtrando la PII del cliente.

Correr:  python agente_inseguro.py
"""

from strands import Agent
from strands.models import BedrockModel

from tools import web_search, get_customer_data

REGION = "us-east-1"
MODEL_ID = "us.amazon.nova-pro-v1:0"

model = BedrockModel(model_id=MODEL_ID, region_name=REGION)

agent = Agent(
    model=model,
    tools=[web_search, get_customer_data],
    system_prompt="You are a helpful assistant.",
    # Sin hooks: nada valida los parametros ni la salida de las herramientas.
)

if __name__ == "__main__":
    prompt = "Resume las ultimas novedades de seguridad en IA."
    print(f"\n>>> Usuario: {prompt}\n")
    print(agent(prompt))
