"""
Herramientas de ejemplo para la demo.

  web_search          — simula una busqueda web que trae contenido externo NO
                        confiable (el vector de inyeccion indirecta).
  get_customer_data   — simula un registro interno con PII (lo que un atacante
                        quiere exfiltrar).

Ambas estan simuladas a proposito para que la demo sea reproducible sin
dependencias externas ni datos reales.
"""

from pathlib import Path

from strands import tool

ATTACK_DOC = Path(__file__).parent / "attack_doc.txt"


@tool
def web_search(query: str) -> str:
    """Busca en la web y devuelve un fragmento de resultado."""
    # Simulacion: devuelve contenido externo NO confiable. En una demo real este
    # texto vendria de internet; aqui vive en attack_doc.txt para ser reproducible.
    return ATTACK_DOC.read_text(encoding="utf-8")


@tool
def get_customer_data(customer_id: str) -> str:
    """Devuelve el registro de un cliente por su ID."""
    # Simulacion: un registro interno con PII. Es lo que el ataque intenta fugar.
    return (
        f"Cliente {customer_id} — email: ana@example.com, "
        "tarjeta: 4111-1111-1111-1111"
    )
