#!/usr/bin/env python3
"""Package the Velo VS Code extension into a versioned .vsix.

Self-contained and offline (no Node / vsce dependency): produces the same layout
VS Code accepts - `extension.vsixmanifest` + `[Content_Types].xml` at the zip root,
all runtime files under `extension/`. Identity fields are read from `package.json`,
so a version bump only requires changing package.json, then re-running:

    python pack_vsix.py

Dev artifacts listed in `.vscodeignore` are excluded. Phase 4 of ROADMAP.md may
migrate this to `vsce` inside CI; until then this is the canonical packager.
"""
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# extension runtime payload: source path -> archive path
PAYLOAD = [
    ("package.json", "extension/package.json"),
    ("README.md", "extension/readme.md"),
    ("language-configuration.json", "extension/language-configuration.json"),
    ("pkg-language-configuration.json", "extension/pkg-language-configuration.json"),
    ("icon.png", "extension/icon.png"),
    ("js/extension.js", "extension/js/extension.js"),
    ("js/lsp_client.js", "extension/js/lsp_client.js"),
    ("_server/velo_lsp.py", "extension/_server/velo_lsp.py"),
    ("_server/velo_analysis.py", "extension/_server/velo_analysis.py"),
    ("syntaxes/velo.tmLanguage.json", "extension/syntaxes/velo.tmLanguage.json"),
    ("syntaxes/velo.pkg.tmLanguage.json", "extension/syntaxes/velo.pkg.tmLanguage.json"),
    ("snippets/velo.json", "extension/snippets/velo.json"),
    ("snippets/velo.pkg.json", "extension/snippets/velo.pkg.json"),
]

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension=".json" ContentType="application/json"/>'
    '<Default Extension=".md" ContentType="text/markdown"/>'
    '<Default Extension=".png" ContentType="image/png"/>'
    '<Default Extension=".vsixmanifest" ContentType="text/xml"/>'
    '<Default Extension=".js" ContentType="application/javascript"/>'
    '<Default Extension=".py" ContentType="text/x-python"/></Types>'
)


def load_and_honour_ignore(payload: list) -> list:
    """Drop payload entries matched by .vscodeignore (name or path wildcards)."""
    import fnmatch

    ignore_path = ROOT / ".vscodeignore"
    rules = []
    if ignore_path.exists():
        rules = [
            line.strip()
            for line in ignore_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    def ignored(source: str) -> bool:
        return any(
            fnmatch.fnmatch(source, r) or fnmatch.fnmatch(Path(source).name, r)
            for r in rules
        )
    return [(src, arc) for src, arc in payload if not ignored(src)]


def vsixmanifest(pkg: dict) -> str:
    version = pkg["version"]
    publisher = pkg["publisher"]
    display = pkg["displayName"]
    description = pkg["description"]
    repo = pkg.get("repository", {}).get("url", "")
    tags = ",".join(pkg.get("keywords", [])) + ",snippet,Velo,__ext_vl,__web_extension"
    categories = ",".join(pkg.get("categories", ["Programming Languages"]))
    engine = pkg.get("engines", {}).get("vscode", "^1.60.0")
    return f'''<?xml version="1.0" encoding="utf-8"?>
	<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011" xmlns:d="http://schemas.microsoft.com/developer/vsx-schema-design/2011">
		<Metadata>
			<Identity Language="en-US" Id="velo-lang" Version="{version}" Publisher="{publisher}" />
			<DisplayName>{display}</DisplayName>
			<Description xml:space="preserve">{description}</Description>
			<Tags>{tags}</Tags>
			<Categories>{categories}</Categories>
			<GalleryFlags>Public</GalleryFlags>

			<Properties>
				<Property Id="Microsoft.VisualStudio.Code.Engine" Value="{engine}" />
				<Property Id="Microsoft.VisualStudio.Code.ExtensionDependencies" Value="" />
				<Property Id="Microsoft.VisualStudio.Code.ExtensionPack" Value="" />
				<Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="ui,workspace,web" />
				<Property Id="Microsoft.VisualStudio.Code.LocalizedLanguages" Value="" />
				<Property Id="Microsoft.VisualStudio.Code.EnabledApiProposals" Value="" />


				<Property Id="Microsoft.VisualStudio.Services.Links.Source" Value="{repo}" />
				<Property Id="Microsoft.VisualStudio.Services.Links.Getstarted" Value="{repo}" />
				<Property Id="Microsoft.VisualStudio.Services.Links.GitHub" Value="{repo}" />
				<Property Id="Microsoft.VisualStudio.Services.Links.Support" Value="{repo}/issues" />
				<Property Id="Microsoft.VisualStudio.Services.Links.Learn" Value="{repo}#readme" />


				<Property Id="Microsoft.VisualStudio.Services.GitHubFlavoredMarkdown" Value="true" />
				<Property Id="Microsoft.VisualStudio.Services.Content.Pricing" Value="Free"/>


			</Properties>


		</Metadata>
		<Installation>
			<InstallationTarget Id="Microsoft.VisualStudio.Code"/>
		</Installation>
		<Dependencies/>
		<Assets>
			<Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
			<Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/readme.md" Addressable="true" />
		</Assets>
	</PackageManifest>
'''


def main() -> int:
    pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    version = pkg["version"]
    out_path = ROOT / f"velo-lang-{version}.vsix"
    payload = load_and_honour_ignore(PAYLOAD)

    missing = [src for src, _ in payload if not (ROOT / src).exists()]
    if missing:
        print(f"[pack_vsix] missing payload files: {', '.join(missing)}")
        return 1

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # manifest + content types first (mimics vsce archive ordering)
        zf.writestr("extension.vsixmanifest", vsixmanifest(pkg))
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        for src, arc in payload:
            zf.write(ROOT / src, arc.replace("/", "\\"))

    print(f"[pack_vsix] wrote {out_path.name} (v{version}), {out_path.stat().st_size} bytes, "
          f"{len(payload)} payload files + manifest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
