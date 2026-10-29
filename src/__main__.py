"""Показати проєктну конфігурацію без завантаження моделей."""

import argparse
import json
from pathlib import Path
import tomllib


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show-config", action="store_true", required=True)
    args = parser.parse_args()
    if args.show_config:
        config_path = Path(__file__).resolve().parents[1] / "config" / "project.toml"
        with config_path.open("rb") as config_file:
            config = tomllib.load(config_file)
        print(json.dumps(config, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
