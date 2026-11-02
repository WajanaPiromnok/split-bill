import argparse
import json

from splitbill.app import app
from splitbill.config import PROJECT_ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description="Export or verify the implemented API schema")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = PROJECT_ROOT / "docs" / "openapi.json"
    rendered = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not path.exists() or path.read_text() != rendered:
            parser.exit(1, "OpenAPI snapshot is stale; run python -m splitbill.openapi\n")
        print("Implemented OpenAPI snapshot is current.")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered)
        print("Exported implemented APIs to docs/openapi.json")


if __name__ == "__main__":
    main()
