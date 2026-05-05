from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, redirect, render_template, request, url_for

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = Path(os.getenv("DATA_FILE", BASE_DIR / "registros_peso.txt"))
LEGACY_JSON_FILE = BASE_DIR / "pesos.json"


def cargar_registros() -> list[dict[str, Any]]:
    if not DATA_FILE.exists() and LEGACY_JSON_FILE.exists():
        # Migra datos del formato anterior (JSON completo) al nuevo TXT (JSONL).
        try:
            legacy = json.loads(LEGACY_JSON_FILE.read_text(encoding="utf-8"))
            if isinstance(legacy, list):
                guardar_registros(legacy)
                return legacy
        except (json.JSONDecodeError, OSError):
            return []

    if not DATA_FILE.exists():
        return []

    try:
        registros: list[dict[str, Any]] = []
        for linea in DATA_FILE.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            registro = json.loads(linea)
            if isinstance(registro, dict):
                registros.append(registro)
        return registros
    except (json.JSONDecodeError, OSError, TypeError):
        return []


def guardar_registros(registros: list[dict[str, Any]]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    contenido = "\n".join(
        json.dumps(registro, ensure_ascii=False) for registro in registros
    )
    DATA_FILE.write_text(f"{contenido}\n" if contenido else "", encoding="utf-8")


@app.get("/")
def inicio() -> str:
    registros = cargar_registros()
    nombre_busqueda = request.args.get("nombre", "").strip()

    if nombre_busqueda:
        filtrados = [
            registro
            for registro in registros
            if registro.get("nombre", "").strip().lower() == nombre_busqueda.lower()
        ]
    else:
        filtrados = registros

    return render_template(
        "index.html",
        registros=filtrados,
        nombre_busqueda=nombre_busqueda,
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

    registros = cargar_registros()
    registros.append(
        {
            "nombre": nombre,
            "peso": peso,
            "fecha": fecha,
        }
    )
    guardar_registros(registros)
    return redirect(url_for("inicio"))


@app.get("/api/registros")
def api_registros():
    nombre_busqueda = request.args.get("nombre", "").strip()
    registros = cargar_registros()

    if nombre_busqueda:
        registros = [
            registro
            for registro in registros
            if registro.get("nombre", "").strip().lower() == nombre_busqueda.lower()
        ]

    return jsonify(
        {
            "total": len(registros),
            "registros": registros,
        }
    )


@app.get("/api/registros/<nombre>")
def api_registros_por_nombre(nombre: str):
    registros = cargar_registros()
    filtrados = [
        registro
        for registro in registros
        if registro.get("nombre", "").strip().lower() == nombre.strip().lower()
    ]
    return jsonify(
        {
            "nombre": nombre,
            "total": len(filtrados),
            "registros": filtrados,
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
