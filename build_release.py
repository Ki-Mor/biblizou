#!/usr/bin/env python3
"""
Construit un zip de release "épuré" pour un plugin QGIS issu de Plugin Builder.

Objectif : ne conserver dans le zip que ce dont l'utilisateur final a besoin
pour installer et faire fonctionner le plugin, en excluant tout l'outillage
de développement (i18n sources, scripts, config pb_tool, tests, CI, etc.).

Usage :
    python build_release.py <chemin_du_plugin> [--output dist] [--name nom_technique]

Exemples :
    # Cas classique Plugin Builder : le dossier du plugin EST la racine du dépôt
    python build_release.py . --output dist

    # Si le nom du dossier sur disque diffère du nom technique attendu par QGIS
    # (celui utilisé dans metadata.txt / les imports), on force le nom du dossier
    # racine à l'intérieur du zip :
    python build_release.py . --name biblizou --output dist
"""
import argparse
import fnmatch
import zipfile
from pathlib import Path

# Motifs exclus du zip final, relatifs à la racine du plugin.
# Adapter cette liste au besoin (ex. retirer "*.ts"/"i18n" si vous voulez
# garder les traductions compilées .qm pour les utilisateurs finaux).
EXCLUDE_PATTERNS = [
    "i18n", "i18n/*", "*.ts", "*.pro",  # sources de traduction Qt Linguist
    "scripts", "scripts/*",  # répertoire scripts et fichiers associés
    "test", "test/*",  # répertoire test et fichiers associés
    "help", "help/*"  # répertoire help et fichiers associés
            "pb_tool.cfg",
    "pylintrc", ".pylintrc",  # outils pylint
    "Makefile",
    "requirements-dev.txt",
    ".git", ".git/*", ".gitignore", ".gitattributes", ".github", ".github/*",  # répertoire et fichiers git
    ".vscode", ".vscode/*", ".idea", ".idea/*", "*.pyc", "__pycache__", "__pycache__/*", ".Rproj.user",
    ".Rproj.user/*"  # répertoire et fichiers IDE
    "*.zip",
    "dist", "dist/*",
    "build_release.py"  # ce fichier
]


def is_excluded(rel_parts) -> bool:
    rel_str = "/".join(rel_parts)
    return any(
        fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(rel_parts[0], pattern)
        for pattern in EXCLUDE_PATTERNS
    )


def build_zip(plugin_dir: Path, output_dir: Path, plugin_name: str | None):
    plugin_dir = plugin_dir.resolve()
    root_name = plugin_name or plugin_dir.name
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{root_name}.zip"

    included, excluded = 0, 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(plugin_dir.rglob("*")):
            if path.is_dir():
                continue
            rel_parts = path.relative_to(plugin_dir).parts
            if is_excluded(rel_parts):
                excluded += 1
                continue
            arcname = str(Path(root_name, *rel_parts))
            zf.write(path, arcname=arcname)
            included += 1

    print(f"Release générée : {zip_path}")
    print(f"  fichiers inclus  : {included}")
    print(f"  fichiers exclus  : {excluded}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plugin_dir", type=Path, help="Chemin vers le dossier du plugin")
    parser.add_argument("--output", type=Path, default=Path("dist"), help="Dossier de sortie (défaut : dist)")
    parser.add_argument("--name", default=None,
                        help="Nom technique du plugin (dossier racine dans le zip). Défaut : nom du dossier sur disque.")
    args = parser.parse_args()
    build_zip(args.plugin_dir, args.output, args.name)
