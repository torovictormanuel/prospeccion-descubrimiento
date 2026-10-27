# tests/test_local.py — Simulador de chat en terminal
# Generado por AgentKit

"""
Prueba tu agente sin necesitar WhatsApp.
Simula una conversación en la terminal, incluida la detección de la ref
del link wa.me y la bitácora de eventos que después lee n8n.
"""

import asyncio
import sys
import os
import re

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.brain import generar_respuesta
from agent.memory import (
    inicializar_db,
    guardar_mensaje,
    obtener_historial,
    limpiar_historial,
    crear_prospecto_si_no_existe,
    registrar_evento,
    listar_eventos,
)

TELEFONO_TEST = "test-local-001"
REF_RE = re.compile(r"\bref\.?\s*#?\s*(\d{1,6})\b|\bc[oó]digo\s*:?\s*([A-Za-z0-9]{6,12})\b", re.IGNORECASE)


async def main():
    """Loop principal del chat de prueba."""
    await inicializar_db()

    print()
    print("=" * 55)
    print("   AgentKit — Test Local (Descubrimiento)")
    print("=" * 55)
    print()
    print("  Escribe como si fueras el socio de un estudio contable.")
    print("  Arrancá con el texto del link wa.me, por ejemplo:")
    print("    'Hola Victor, vengo de LinkedIn (ref 12)'")
    print("  Después probá:")
    print("    'prefiero contestar por acá'")
    print("    'lo que más nos cuesta es pedirle los papeles a los clientes'")
    print("    'dale, agendemos la llamada'")
    print("    'no me interesa, gracias'")
    print()
    print("  Comandos especiales:")
    print("    'eventos'  — muestra lo que n8n leería de /api/eventos")
    print("    'limpiar'  — borra el historial")
    print("    'salir'    — termina el test")
    print()
    print("-" * 55)
    print()

    while True:
        try:
            mensaje = input("Tu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nTest finalizado.")
            break

        if not mensaje:
            continue

        if mensaje.lower() == "salir":
            print("\nTest finalizado.")
            break

        if mensaje.lower() == "limpiar":
            await limpiar_historial(TELEFONO_TEST)
            print("[Historial borrado]\n")
            continue

        if mensaje.lower() == "eventos":
            for e in await listar_eventos(0):
                print(f"  #{e['id']} {e['tipo']} ref={e['ref']} {e['detalle']}")
            print()
            continue

        # Misma lógica que main.py para vincular el chat con la fila del Pipeline
        match = REF_RE.search(mensaje)
        if await crear_prospecto_si_no_existe(TELEFONO_TEST, (match.group(1) or match.group(2)) if match else None):
            await registrar_evento(TELEFONO_TEST, "primer_contacto", {"texto": mensaje[:300]})

        # Obtener historial ANTES de guardar (brain.py agrega el mensaje actual)
        historial = await obtener_historial(TELEFONO_TEST)

        # Generar respuesta
        print("\nAgente: ", end="", flush=True)
        respuesta = await generar_respuesta(mensaje, historial, TELEFONO_TEST)
        print(respuesta)
        print()

        # Guardar mensaje del usuario y respuesta del agente
        await guardar_mensaje(TELEFONO_TEST, "user", mensaje)
        await guardar_mensaje(TELEFONO_TEST, "assistant", respuesta)


if __name__ == "__main__":
    asyncio.run(main())
