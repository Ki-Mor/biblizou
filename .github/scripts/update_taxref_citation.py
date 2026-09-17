import urllib.request
import re
import sys

URL = "https://taxref.mnhn.fr/taxref-web/about"
README_PATH = ".github/README.md"


def fetch_citation():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode("utf-8")
    except Exception as e:
        print(f"Erreur réseau lors de la récupération de la page TAXREF : {e}")
        sys.exit(1)

    match = re.search(r'<span id="fullCitation">(.*?)</span>', html, re.DOTALL)
    if not match:
        print("Bloc 'fullCitation' introuvable dans la page TAXREF (structure du site modifiée ?).")
        sys.exit(1)

    citation_text = re.sub(r'<[^>]+>', '', match.group(1))
    return ' '.join(citation_text.split())


def update_readme(citation):
    with open(README_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r'<!-- TAXREF_START -->.*?<!-- TAXREF_END -->'
    replacement = f'<!-- TAXREF_START -->\n{citation}\n<!-- TAXREF_END -->'
    updated_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    with open(README_PATH, 'w', encoding='utf-8') as f:
        f.write(updated_content)


if __name__ == "__main__":
    citation = fetch_citation()
    update_readme(citation)
    print(f"Citation mise à jour : {citation}")
