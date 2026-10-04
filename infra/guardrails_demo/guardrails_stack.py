"""
Stack con los dos Amazon Bedrock Guardrails de la demo.

  web_search guardrail        -> filtro de contenido (contenido externo no confiable).
  get_customer_data guardrail -> deteccion de PII (email + tarjeta).

Ambos usan el recurso AWS::Bedrock::Guardrail (CfnGuardrail). La version del
guardrail es la que crea el deploy; para pruebas rapidas tambien puedes usar la
version "DRAFT" sin publicar.
"""

from aws_cdk import (
    CfnOutput,
    Stack,
    aws_bedrock as bedrock,
)
from constructs import Construct

BLOCKED_INPUT = "Esta solicitud fue bloqueada por una barrera de seguridad."
BLOCKED_OUTPUT = "Este contenido fue bloqueado por una barrera de seguridad."

# Categorias de content filter (todas a MEDIUM para la demo).
CONTENT_FILTER_TYPES = ["HATE", "INSULTS", "SEXUAL", "VIOLENCE", "MISCONDUCT", "PROMPT_ATTACK"]

# Entidades de PII que la demo quiere bloquear en los datos de cliente.
PII_ENTITIES = ["EMAIL", "CREDIT_DEBIT_CARD_NUMBER", "US_SOCIAL_SECURITY_NUMBER", "PHONE"]


class GuardrailsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- Guardrail para web_search: filtro de contenido estricto ---
        web_search_guardrail = bedrock.CfnGuardrail(
            self,
            "WebSearchGuardrail",
            name="ekoparty-websearch",
            description="Filtra contenido no deseado del resultado de web_search (checkpoint 3).",
            blocked_input_messaging=BLOCKED_INPUT,
            blocked_outputs_messaging=BLOCKED_OUTPUT,
            content_policy_config=bedrock.CfnGuardrail.ContentPolicyConfigProperty(
                filters_config=[
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type=filter_type,
                        input_strength="HIGH",
                        output_strength="HIGH",
                    )
                    for filter_type in CONTENT_FILTER_TYPES
                ]
            ),
        )

        # --- Guardrail para get_customer_data: deteccion de PII ---
        customer_data_guardrail = bedrock.CfnGuardrail(
            self,
            "CustomerDataGuardrail",
            name="ekoparty-customerdata",
            description="Detecta y bloquea PII en los parametros de get_customer_data (checkpoint 2).",
            blocked_input_messaging=BLOCKED_INPUT,
            blocked_outputs_messaging=BLOCKED_OUTPUT,
            sensitive_information_policy_config=bedrock.CfnGuardrail.SensitiveInformationPolicyConfigProperty(
                pii_entities_config=[
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type=entity,
                        action="BLOCK",
                    )
                    for entity in PII_ENTITIES
                ]
            ),
        )

        # --- Salidas: los IDs que pide la demo ---
        CfnOutput(
            self,
            "WebSearchGuardrailId",
            value=web_search_guardrail.attr_guardrail_id,
            description="Exportalo como GR_WEBSEARCH_ID antes de correr agente_seguro.py",
        )
        CfnOutput(
            self,
            "CustomerDataGuardrailId",
            value=customer_data_guardrail.attr_guardrail_id,
            description="Exportalo como GR_CUSTOMERDATA_ID antes de correr agente_seguro.py",
        )
        CfnOutput(
            self,
            "GuardrailVersion",
            value="DRAFT",
            description="Usa DRAFT para pruebas, o publica una version en la consola de Bedrock.",
        )
