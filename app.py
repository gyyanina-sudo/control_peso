from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, redirect, render_template, request, url_for
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
BASE_DIR = Path(__file__).resolve().parent
LEGACY_TXT_FILE = BASE_DIR / "registros_peso.txt"
USE_POSTGRES = bool(DATABASE_URL)


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def inicializar_db() -> None:
    if not USE_POSTGRES:
        return
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS registros_peso (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    peso NUMERIC(6, 2) NOT NULL,
                    fecha DATE NOT NULL,
                    creado_en TIMESTAMP NOT NULL DEFAULT NOW()
                );
                """
            )
    migrar_txt_legacy_si_hace_falta()


def migrar_txt_legacy_si_hace_falta() -> None:
    if not USE_POSTGRES:
        return
    if not LEGACY_TXT_FILE.exists():
        return

    try:
        legacy_registros = []
        for linea in LEGACY_TXT_FILE.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            registro = json.loads(linea)
            if isinstance(registro, dict):
                legacy_registros.append(registro)
    except (OSError, json.JSONDecodeError):
        return

    if not legacy_registros:
        return

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM registros_peso")
            if cur.fetchone()[0] > 0:
                return

            for registro in legacy_registros:
                nombre = str(registro.get("nombre", "")).strip()
                fecha = str(registro.get("fecha", "")).strip()
                if not nombre or not fecha:
                    continue
                try:
                    peso = float(registro.get("peso"))
                except (TypeError, ValueError):
                    continue
                cur.execute(
                    """
                    INSERT INTO registros_peso (nombre, peso, fecha)
                    VALUES (%s, %s, %s)
                    """,
                    (nombre, peso, fecha),
                )


def cargar_registros(nombre: str | None = None) -> list[dict[str, Any]]:
    if not USE_POSTGRES:
        try:
            registros: list[dict[str, Any]] = []
            if not LEGACY_TXT_FILE.exists():
                return registros
            for linea in LEGACY_TXT_FILE.read_text(encoding="utf-8").splitlines():
                if not linea.strip():
                    continue
                registro = json.loads(linea)
                if isinstance(registro, dict):
                    registros.append(registro)
            if nombre:
                return [
                    r
                    for r in registros
                    if r.get("nombre", "").strip().lower() == nombre.strip().lower()
                ]
            return sorted(
                registros,
                key=lambda r: (r.get("fecha", ""), r.get("nombre", "")),
                reverse=True,
            )
        except (OSError, json.JSONDecodeError, TypeError):
            return []

    if nombre:
        query = """
            SELECT nombre, peso::float8 AS peso, fecha::text AS fecha
            FROM registros_peso
            WHERE LOWER(nombre) = LOWER(%s)
            ORDER BY fecha DESC, id DESC
        """
        params: tuple[Any, ...] = (nombre,)
    else:
        query = """
            SELECT nombre, peso::float8 AS peso, fecha::text AS fecha
            FROM registros_peso
            ORDER BY fecha DESC, id DESC
        """
        params = ()

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]


def guardar_registro(nombre: str, peso: float, fecha: str) -> None:
    if not USE_POSTGRES:
        LEGACY_TXT_FILE.parent.mkdir(parents=True, exist_ok=True)
        nuevo = {"nombre": nombre, "peso": peso, "fecha": fecha}
        with LEGACY_TXT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(nuevo, ensure_ascii=False) + "\n")
        return

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO registros_peso (nombre, peso, fecha)
                VALUES (%s, %s, %s)
                """,
                (nombre, peso, fecha),
            )


@app.get("/")
def inicio() -> str:
    nombre_busqueda = request.args.get("nombre", "").strip()
    busqueda_realizada = request.args.get("buscar") == "1"
    filtrados = cargar_registros(nombre_busqueda or None) if busqueda_realizada else []

    return render_template(
        "index.html",
        registros=filtrados,
        nombre_busqueda=nombre_busqueda,
        busqueda_realizada=busqueda_realizada,
    )


@app.post("/registrar")
def registrar_peso():
    nombre = request.form.get("nombre", "").strip()
    peso_texto = request.form.get("peso", "").strip()
    fecha = request.form.get("fecha", "").strip()

    if not nombre or not peso_texto:
        return redirect(url_for("inicio"))

    try:
        peso = float(peso_texto.replace(",", "."))
        if peso <= 0:
            raise ValueError("El peso debe ser mayor a cero.")
    except ValueError:
        return redirect(url_for("inicio"))

    if not fecha:
        fecha = datetime.now().strftime("%Y-%m-%d")

    guardar_registro(nombre, peso, fecha)
    return redirect(url_for("inicio"))


@app.get("/api/registros")
def api_registros():
    nombre_busqueda = request.args.get("nombre", "").strip()
    registros = cargar_registros(nombre_busqueda or None)

    return jsonify(
        {
            "total": len(registros),
            "registros": registros,
        }
    )


@app.get("/api/registros/<nombre>")
def api_registros_por_nombre(nombre: str):
    filtrados = cargar_registros(nombre.strip())
    return jsonify(
        {
            "nombre": nombre,
            "total": len(filtrados),
            "registros": filtrados,
        }
    )


inicializar_db()


if __name__ == "__main__":
    app.run(debug=True)
