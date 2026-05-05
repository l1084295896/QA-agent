from ..utils.log_utils import LogUtils


class CommandParser:
    """Parses slash-command input into (command_name, params) tuples."""

    def __init__(self, commands_config: dict):
        self.commands = commands_config.get("commands", {})
        self._trigger_map = {
            cfg["trigger"].lower(): name
            for name, cfg in self.commands.items()
        }

    def parse(self, text: str) -> tuple:
        """Returns (command_name, params) or (None, {})."""
        text = text.strip()
        if not text.startswith("/"):
            return None, {}

        parts = text.split()
        trigger = parts[0].lower()
        cmd_name = self._trigger_map.get(trigger)
        if not cmd_name:
            return None, {}

        params = self._extract_params(cmd_name, parts[1:])
        LogUtils.debug(f"Parsed: {cmd_name} params={params}")
        return cmd_name, params

    def _extract_params(self, cmd_name: str, args: list[str]) -> dict:
        result = {"raw_args": args}

        if cmd_name == "qa":
            result.update(self._parse_qa(args))
        elif cmd_name == "list_questions":
            result["domain"] = args[0] if args else None
        elif cmd_name == "add_file":
            result["file_path"] = args[0] if args else None
        elif cmd_name in ("edit", "delete"):
            result["question_id"] = args[0] if args else None

        return result

    def _parse_qa(self, args: list[str]) -> dict:
        result = {"mode": "idle", "target": None, "random_count": None}

        if not args:
            result["mode"] = "ask_intent"
            return result

        random_idx = None
        for i, arg in enumerate(args):
            if arg.lower() == "random":
                random_idx = i
                break

        if random_idx is not None:
            if random_idx > 0:
                result["target"] = " ".join(args[:random_idx])
            result["mode"] = "random"
            if random_idx + 1 < len(args):
                try:
                    result["random_count"] = int(args[random_idx + 1])
                except ValueError:
                    result["random_count"] = 1
            else:
                result["random_count"] = 1
        else:
            result["target"] = " ".join(args)
            result["mode"] = "direct"

        return result

    def get_command_list(self) -> list[dict]:
        return [
            {
                "trigger": c["trigger"],
                "description": c["description"],
                "usage": c.get("usage", ""),
            }
            for c in self.commands.values()
        ]
