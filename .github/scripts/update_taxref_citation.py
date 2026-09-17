import json
import os
import re
import sys
import urllib.request
import urllib.error

URL = "https://taxref.mnhn.fr/taxref-web/about"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
README_PATH = os.path.join(SCRIPT_DIR, "..", "README.md")  # .github/scripts/ -> .github/README.md

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


def fetch_citation():
    req = urllib.request.Request(URL, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html_content = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:1000]
        print(f"Erreur HTTP {e.code} lors de la récupération de la page TAXREF.")
        print(f"Corps de la réponse (extrait) :\n{body}")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur réseau lors de la récupération de la page TAXREF : {e}")
        sys.exit(1)

    match = re.search(r'var fullCitation = (".*?");', html_content, re.DOTALL)
    if not match:
        print("Variable JS 'fullCitation' introuvable dans la page TAXREF (structure du site modifiée ?).")
        sys.exit(1)

    try:
        raw_citation = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        print(f"Impossible de décoder la citation extraite : {e}")
        sys.exit(1)

    citation = ' '.join(re.sub(r'<[^>]+>', '', raw_citation).split())

    if not citation or not citation.startswith("TAXREF"):
        print(f"Citation extraite invalide ou vide : {citation!r}")
        sys.exit(1)

    return citation


def build_bullet(citation_text: str) -> str:
    rest = citation_text[len("TAXREF"):].lstrip()
    return f"* **TAXREF** {rest}"


def update_readme(citation: str):
    with open(README_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r'<!-- TAXREF_START -->.*?<!-- TAXREF_END'

if __name__ == "__main__":
    citation = fetch_citation()
    update_readme(citation)
    print(f"Citation mise à jour : {citation}")
