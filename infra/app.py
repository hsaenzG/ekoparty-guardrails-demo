#!/usr/bin/env python3
"""
CDK app para la demo de guardrails en las herramientas.

Despliega dos Amazon Bedrock Guardrails:
  - uno para la herramienta web_search (filtro de contenido, salida estricta),
  - uno para la herramienta get_customer_data (deteccion de PII).

Tras el deploy, el stack imprime los IDs de los guardrails. Expórtalos como
GR_WEBSEARCH_ID y GR_CUSTOMERDATA_ID antes de correr agente_seguro.py.
"""

import aws_cdk as cdk

from guardrails_demo.guardrails_stack import GuardrailsStack

app = cdk.App()

GuardrailsStack(
    app,
    "EkopartyGuardrailsDemo",
    description="Amazon Bedrock Guardrails para la demo de guardrails en las herramientas (Ekoparty 2026).",
    env=cdk.Environment(region="us-east-2"),
)

app.synth()
