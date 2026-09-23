#!/usr/bin/env python3
"""
Quarto Husson - Terminal Chat Assistant (Ollama)
Interface conversationnelle interactive directement dans le terminal macOS.
"""

import os
import sys
import json
import readline
import urllib.request
import urllib.error
from pathlib import Path
from io import StringIO
from ruamel.yaml import YAML

OLLAMA_API_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
yaml_parser = YAML()
yaml_parser.preserve_quotes = True

def get_local_models():
    url = f"{OLLAMA_API_URL.rstrip('/')}/api/tags"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Quarto-Terminal-Chat"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", []) if not ("remote_model" in m or "-cloud" in m.get("name", ""))]
    except Exception:
        return []

def stream_chat(model: str, messages: list, system_prompt: str):
    url = f"{OLLAMA_API_URL.rstrip('/')}/api/chat"
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    payload = json.dumps({
        "model": model,
        "messages": full_messages,
        "stream": True,
        "options": {"temperature": 0.2}
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90.0) as resp:
            for raw_line in resp:
                if raw_line:
                    try:
                        d = json.loads(raw_line.decode("utf-8"))
                        content = d.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if d.get("done", False):
                            break
                    except Exception:
                        pass
    except Exception as e:
        yield f"\n[Erreur de communication Ollama : {e}]\n"

def main():
    models = get_local_models()
    if not models:
        print("[Erreur] Aucun serveur Ollama detecte sur http://localhost:11434.")
        print("Veuillez lancer 'ollama serve' dans un terminal.")
        sys.exit(1)

    # Selection du modele par defaut
    model = "qwen2.5-coder:latest" if "qwen2.5-coder:latest" in models else models[0]

    # Document cible
    default_doc = Path("/Users/thomashusson/Documents/Projets/M2biostatistiques/S2/devoir_epidemio/devoir_epidemio.qmd")
    if len(sys.argv) > 1:
        doc_path = Path(sys.argv[1]).resolve()
    else:
        doc_path = default_doc

    doc_yaml = {}
    if doc_path.exists():
        try:
            content = doc_path.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    doc_yaml = yaml_parser.load(parts[1]) or {}
        except Exception:
            pass

    stream_y = StringIO()
    yaml_parser.dump(doc_yaml, stream_y)
    yaml_str = stream_y.getvalue()

    system_prompt = (
        "Tu es l'assistant de redaction Quarto et LaTeX du template Husson.\n"
        "Tu reponds aux questions techniques sur Quarto, Pandoc, XeLaTeX, R, KOMA-Script et la mise en page.\n\n"
        f"Document actif : {doc_path.name}\n"
        f"Chemin : {doc_path}\n"
        f"YAML du document :\n```yaml\n{yaml_str}\n```\n\n"
        "Consignes : reponds toujours en francais direct, technique et precis, sans aucun emoji."
    )

    print("=" * 65)
    print(" Quarto Husson - Terminal Chat Assistant")
    print(f" Modele local  : {model}")
    print(f" Document actif: {doc_path.name}")
    print(" Commandes     : 'exit' ou 'quit' pour fermer, 'clear' pour effacer")
    print("=" * 65)
    print()

    messages = []

    while True:
        try:
            user_input = input("\nVous > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nFermeture de l'assistant.")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "q"]:
            print("Au revoir.")
            break

        if user_input.lower() == "clear":
            messages.clear()
            print("[Historique de la conversation efface.]")
            continue

        messages.append({"role": "user", "content": user_input})
        print("\nAssistant > ", end="", flush=True)

        full_response = []
        for token in stream_chat(model, messages, system_prompt):
            print(token, end="", flush=True)
            full_response.append(token)
        print()

        messages.append({"role": "assistant", "content": "".join(full_response)})

if __name__ == "__main__":
    main()
