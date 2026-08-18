import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def generate_sbom(output_path: str = "sbom.json") -> None:
    """Generate a CycloneDX SBOM from the installed pip packages."""
    try:
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "cyclonedx_py", "environment", "-o", output_path, "--of", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        sys.stderr.write(f"SBOM generated successfully: {output_path}\n")
        sys.stderr.write(result.stdout)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(f"Failed to generate SBOM: {exc.stderr}\n")
        sys.exit(1)
    except FileNotFoundError:
        sys.stderr.write("cyclonedx-bom not found. Install with: pip install cyclonedx-bom\n")
        sys.exit(1)


def enrich_sbom_with_metadata(sbom_path: str = "sbom.json") -> None:
    """Add metadata to the SBOM."""
    path = Path(sbom_path)
    if not path.exists():
        sys.stderr.write(f"SBOM file not found: {sbom_path}\n")
        sys.exit(1)

    with open(path, encoding="utf-8") as handle:
        sbom = json.load(handle)

    sbom.setdefault("metadata", {})
    sbom["metadata"]["timestamp"] = datetime.now(UTC).isoformat()
    tools = sbom["metadata"].get("tools", [])
    if isinstance(tools, dict):
        tools = [tools]
    tools.append({
        "vendor": "IntentLock",
        "name": "generate_sbom.py",
        "version": "1.0.0",
    })
    sbom["metadata"]["tools"] = tools

    with open(path, "w", encoding="utf-8") as handle:
        json.dump(sbom, handle, indent=2)
        handle.write("\n")

    sys.stderr.write(f"SBOM metadata enriched: {sbom_path}\n")


def main() -> None:
    generate_sbom()
    enrich_sbom_with_metadata()


if __name__ == "__main__":
    main()
