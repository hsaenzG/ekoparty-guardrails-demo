"""
GuardrailHook — extiende Amazon Bedrock Guardrails al limite de las herramientas.

Una sola clase HookProvider que registra tres checkpoints de validacion en el
ciclo de vida de un agente Strands:

  Checkpoint 1 (BeforeInvocationEvent): valida la entrada antes de que llegue al modelo.
  Checkpoint 2 (BeforeToolCallEvent):   valida los parametros antes de ejecutar la herramienta.
  Checkpoint 3 (AfterToolCallEvent):    valida el resultado de la herramienta.

Los tres comparten _check(), que llama a la API ApplyGuardrail de Bedrock.
Basado en el AWS Security Blog:
https://aws.amazon.com/blogs/security/extend-amazon-bedrock-guardrails-to-tool-interactions-using-the-strands-agents-sdk/
"""

import boto3
from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import (
    BeforeInvocationEvent,
    BeforeToolCallEvent,
    AfterToolCallEvent,
)


class GuardrailHook(HookProvider):
    def __init__(self, guardrail_id, guardrail_version, region_name, tool_names=None):
        self.region_name = region_name
        self.guardrail_id = guardrail_id
        self.guardrail_version = guardrail_version
        self.tool_names = tool_names  # None = aplica a todas las herramientas
        self._client = None

    @property
    def client(self):
        # El cliente se crea en el primer uso para no resolver credenciales al
        # instanciar el hook.
        if self._client is None:
            self._client = boto3.client("bedrock-runtime", region_name=self.region_name)
        return self._client

    def register_hooks(self, registry: HookRegistry, **kwargs):
        registry.add_callback(BeforeInvocationEvent, self.validate_inbound)   # Checkpoint 1
        registry.add_callback(BeforeToolCallEvent, self.validate_input)       # Checkpoint 2
        registry.add_callback(AfterToolCallEvent, self.validate_output)       # Checkpoint 3

    def _check(self, content, source="INPUT"):
        """Llama a ApplyGuardrail. Devuelve True si el contenido es seguro."""
        response = self.client.apply_guardrail(
            guardrailIdentifier=self.guardrail_id,
            guardrailVersion=self.guardrail_version,
            source=source,  # "INPUT" aplica politicas de entrada; "OUTPUT" las de salida
            content=[{"text": {"text": content}}],
        )
        return response["action"] != "GUARDRAIL_INTERVENED"

    # Checkpoint 1 — valida el ultimo mensaje del usuario antes de la inferencia.
    # El modelo no ve el contenido bloqueado.
    async def validate_inbound(self, event: BeforeInvocationEvent):
        for msg in reversed(event.messages):
            if msg.get("role") == "user":
                for block in msg.get("content", []):
                    text = block.get("text", "")
                    if text and not self._check(text):
                        print(
                            "\n[GUARDRAIL] Checkpoint 1 (entrada) BLOQUEO la peticion "
                            "del usuario antes de llegar al modelo.",
                            flush=True,
                        )
                        event.messages.clear()
                        event.messages.append({
                            "role": "user",
                            "content": [{"text": "Request blocked by safety guardrail."}],
                        })
                        return
                break

    # Checkpoint 2 — valida los parametros antes de ejecutar la herramienta.
    # Se saltea si el nombre de la herramienta no esta en tool_names.
    async def validate_input(self, event: BeforeToolCallEvent):
        if self.tool_names and event.tool_use.get("name") not in self.tool_names:
            return
        tool_name = event.tool_use.get("name")
        tool_input = event.tool_use.get("input", {})
        for param_value in tool_input.values():
            if isinstance(param_value, str) and not self._check(param_value):
                print(
                    f"\n[GUARDRAIL] Checkpoint 2 (parametros) BLOQUEO la llamada a "
                    f"'{tool_name}': un parametro no paso el guardrail.",
                    flush=True,
                )
                event.cancel_tool = "This request was blocked by a safety guardrail."
                return

    # Checkpoint 3 — valida el resultado de la herramienta con source="OUTPUT".
    # Se saltea si el nombre de la herramienta no esta en tool_names.
    async def validate_output(self, event: AfterToolCallEvent):
        if self.tool_names and event.tool_use.get("name") not in self.tool_names:
            return
        tool_name = event.tool_use.get("name")
        content_parts = [
            block["text"]
            for block in event.result.get("content", [])
            if "text" in block
        ]
        content = "\n".join(content_parts)
        if content and not self._check(content, source="OUTPUT"):
            print(
                f"\n[GUARDRAIL] Checkpoint 3 (salida) BLOQUEO el resultado de "
                f"'{tool_name}': el contenido no paso el guardrail.",
                flush=True,
            )
            event.result = {
                "toolUseId": event.result["toolUseId"],
                "status": "error",
                "content": [{"text": "Content blocked by safety guardrail."}],
            }
