# agent/memory.py — Memoria de conversaciones con SQLite
# Generado por AgentKit

"""
Sistema de memoria del agente. Guarda el historial de conversaciones
por número de teléfono usando SQLite (local) o PostgreSQL (producción).
También guarda idempotencia de webhooks y datos propios del rubro
(prospectos, hallazgos de descubrimiento y eventos para sincronizar
con el pipeline de Google Sheets vía n8n).
"""

import os
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, select, Integer
from dotenv import load_dotenv

load_dotenv()

# Configuración de base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agentkit.db")

# Si es PostgreSQL en producción, ajustar el esquema de URL
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Mensaje(Base):
    """Modelo de mensaje en la base de datos."""
    __tablename__ = "mensajes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    role: Mapped[str] = mapped_column(String(20))  # "user" o "assistant"
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EventoWebhook(Base):
    """
    Registro de mensaje_id ya procesados. Meta y Twilio reintentan la
    entrega del webhook si no reciben 200 a tiempo — sin esta tabla,
    un reintento haría que el agente responda el mismo mensaje 2+ veces.
    """
    __tablename__ = "eventos_webhook"

    mensaje_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    procesado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Prospecto(Base):
    """
    Persona que escribió por WhatsApp desde el link de LinkedIn/email.
    `ref` es el ID de su fila en la hoja Pipeline (viene en el texto
    precargado del link wa.me: "... (ref 12)").
    """
    __tablename__ = "prospectos"

    telefono: Mapped[str] = mapped_column(String(50), primary_key=True)
    ref: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    empresa: Mapped[str | None] = mapped_column(String(200), nullable=True)
    rol: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    estado: Mapped[str] = mapped_column(String(30), default="conversando")
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Hallazgo(Base):
    """Un problema/dolor concreto que contó el prospecto (la materia prima del descubrimiento)."""
    __tablename__ = "hallazgos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    tema: Mapped[str] = mapped_column(String(100))
    descripcion: Mapped[str] = mapped_column(Text)
    frecuencia: Mapped[str | None] = mapped_column(String(200), nullable=True)
    impacto: Mapped[str | None] = mapped_column(String(300), nullable=True)
    herramienta_actual: Mapped[str | None] = mapped_column(String(300), nullable=True)
    cita_textual: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Evento(Base):
    """
    Bitácora append-only de lo que pasa en las conversaciones. n8n la lee
    con GET /api/eventos?desde_id=N y actualiza la hoja Pipeline. Usar un
    id incremental como cursor evita perder o duplicar eventos entre syncs.
    """
    __tablename__ = "eventos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    tipo: Mapped[str] = mapped_column(String(30))  # primer_contacto | datos | hallazgo | agendado | no_contactar | escalar
    detalle: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def inicializar_db():
    """Crea las tablas si no existen."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def mensaje_ya_procesado(mensaje_id: str) -> bool:
    """Retorna True si este mensaje_id ya fue procesado antes (reintento del proveedor)."""
    if not mensaje_id:
        return False
    async with async_session() as session:
        result = await session.get(EventoWebhook, mensaje_id)
        return result is not None


async def marcar_mensaje_procesado(mensaje_id: str):
    """Registra un mensaje_id como procesado. Idempotente: ignora si ya existe."""
    if not mensaje_id:
        return
    async with async_session() as session:
        existente = await session.get(EventoWebhook, mensaje_id)
        if existente is None:
            session.add(EventoWebhook(mensaje_id=mensaje_id))
            await session.commit()


async def guardar_mensaje(telefono: str, role: str, content: str):
    """Guarda un mensaje en el historial de conversación."""
    async with async_session() as session:
        mensaje = Mensaje(
            telefono=telefono,
            role=role,
            content=content,
            timestamp=datetime.utcnow()
        )
        session.add(mensaje)
        await session.commit()


async def obtener_historial(telefono: str, limite: int = 20) -> list[dict]:
    """
    Recupera los últimos N mensajes de una conversación.

    Args:
        telefono: Número de teléfono del cliente
        limite: Máximo de mensajes a recuperar (default: 20)

    Returns:
        Lista de diccionarios con role y content
    """
    async with async_session() as session:
        query = (
            select(Mensaje)
            .where(Mensaje.telefono == telefono)
            .order_by(Mensaje.timestamp.desc())
            .limit(limite)
        )
        result = await session.execute(query)
        mensajes = result.scalars().all()

        # Invertir para orden cronológico (los más recientes están primero)
        mensajes.reverse()

        return [
            {"role": msg.role, "content": msg.content}
            for msg in mensajes
        ]


async def limpiar_historial(telefono: str):
    """Borra todo el historial de una conversación."""
    async with async_session() as session:
        query = select(Mensaje).where(Mensaje.telefono == telefono)
        result = await session.execute(query)
        mensajes = result.scalars().all()
        for msg in mensajes:
            await session.delete(msg)
        await session.commit()


async def registrar_evento(telefono: str, tipo: str, detalle: dict | None = None):
    """Agrega un evento a la bitácora que consume n8n."""
    async with async_session() as session:
        session.add(Evento(telefono=telefono, tipo=tipo, detalle=json.dumps(detalle or {}, ensure_ascii=False)))
        await session.commit()


async def obtener_prospecto(telefono: str) -> Prospecto | None:
    async with async_session() as session:
        return await session.get(Prospecto, telefono)


async def crear_prospecto_si_no_existe(telefono: str, ref: str | None) -> bool:
    """
    Crea el prospecto en su primer mensaje. Si ya existía sin ref y ahora
    llega una, la completa. Retorna True si es un contacto nuevo.
    """
    async with async_session() as session:
        p = await session.get(Prospecto, telefono)
        if p is None:
            session.add(Prospecto(telefono=telefono, ref=ref))
            await session.commit()
            return True
        if ref and not p.ref:
            p.ref = ref
            await session.commit()
        return False


async def actualizar_prospecto(telefono: str, **campos):
    """Actualiza solo los campos recibidos que no sean None."""
    async with async_session() as session:
        p = await session.get(Prospecto, telefono)
        if p is None:
            p = Prospecto(telefono=telefono)
            session.add(p)
        for k, v in campos.items():
            if v is not None:
                setattr(p, k, v)
        await session.commit()


async def guardar_hallazgo(telefono: str, **campos) -> int:
    async with async_session() as session:
        h = Hallazgo(telefono=telefono, **campos)
        session.add(h)
        await session.commit()
        await session.refresh(h)
        return h.id


async def listar_eventos(desde_id: int = 0, limite: int = 200) -> list[dict]:
    """Eventos posteriores a `desde_id`, con la ref y datos del prospecto ya resueltos."""
    async with async_session() as session:
        result = await session.execute(
            select(Evento).where(Evento.id > desde_id).order_by(Evento.id).limit(limite)
        )
        eventos = result.scalars().all()
        salida = []
        for e in eventos:
            p = await session.get(Prospecto, e.telefono)
            salida.append({
                "id": e.id,
                "tipo": e.tipo,
                "telefono": e.telefono,
                "ref": p.ref if p else None,
                "nombre": p.nombre if p else None,
                "empresa": p.empresa if p else None,
                "creado_en": e.creado_en.isoformat() + "Z",
                "detalle": json.loads(e.detalle or "{}"),
            })
        return salida
