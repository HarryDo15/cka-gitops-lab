"""Write a digest-pinned image into Kustomize; review, commit, then push it."""
import argparse
import json
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("image", help="Registry/repository@sha256:<64 hex characters>")
args = parser.parse_args()
if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:/-]*@sha256:[0-9a-f]{64}", args.image):
    parser.error("An immutable sha256 image reference is required")
name, digest = args.image.split("@")
path = Path(__file__).resolve().parents[1] / "deploy/kustomization.yaml"
source = path.read_text()
source, count = re.subn(r"(?m)^    newName:.*$", "    newName: " + json.dumps(name), source)
if count != 1:
    raise SystemExit("Expected exactly one newName in deploy/kustomization.yaml")
source, count = re.subn(r"(?m)^    (?:newTag|digest):.*$", "    digest: " + json.dumps(digest), source)
if count != 1:
    raise SystemExit("Expected exactly one image tag or digest")
path.write_text(source)
print(f"Updated {path}. Review the diff, test, commit, and push to GitHub before Argo CD sync.")
