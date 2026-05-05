"""斜杠命令解析器，将用户输入文本解析为 (命令名, 参数字典) 元组。"""

from ..utils.log_utils import LogUtils


class CommandParser:
    """命令解析器：根据 commands 配置将 /cmd 格式的输入映射到命令名和结构化参数。

    核心流程：
    1. 检查是否以 "/" 开头 → 非命令返回 (None, {})
    2. 通过 trigger 匹配命令名（大小写不敏感）
    3. 根据命令类型调用不同的参数提取逻辑
    """

    def __init__(self, commands_config: dict):
        """初始化命令解析器。

        Args:
            commands_config: 命令配置字典，结构为 {"commands": {name: {trigger, description, usage}}}
        """
        self.commands = commands_config.get("commands", {})
        # 构建 trigger → 命令名 的快速查找映射，trigger 统一小写
        self._trigger_map = {
            cfg["trigger"].lower(): name
            for name, cfg in self.commands.items()
        }

    def parse(self, text: str) -> tuple:
        """解析用户输入，返回 (command_name, params) 或 (None, {})。

        Args:
            text: 用户输入文本（如 "/qa Python random 3"）

        Returns:
            (命令名, 参数字典) 元组；非命令输入返回 (None, {})
        """
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
        """根据命令类型分发到对应的参数提取逻辑。

        所有命令的参数字典都包含 "raw_args" 字段（原始参数列表）。
        """
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
        """解析 /qa 命令的复杂参数。

        支持三种模式：
        - ask_intent: 无参数 → 引导用户选择领域
        - random: 包含 "random" 关键字 → 随机抽题（前面部分是 target 领域/关键词，后面可选数字）
        - direct: 其他参数 → 直接按领域/关键词选题

        Returns:
            包含 mode, target, random_count 的字典
        """
        result = {"mode": "idle", "target": None, "random_count": None}

        # 无参数 → 询问用户意图
        if not args:
            result["mode"] = "ask_intent"
            return result

        # 查找 "random" 关键字的位置
        random_idx = None
        for i, arg in enumerate(args):
            if arg.lower() == "random":
                random_idx = i
                break

        if random_idx is not None:
            # "random" 之前的参数拼接为 target（领域/搜索词）
            if random_idx > 0:
                result["target"] = " ".join(args[:random_idx])
            result["mode"] = "random"
            # "random" 之后的参数为抽题数量，解析失败默认 1
            if random_idx + 1 < len(args):
                try:
                    result["random_count"] = int(args[random_idx + 1])
                except ValueError:
                    result["random_count"] = 1
            else:
                result["random_count"] = 1
        else:
            # 无 "random" → 全部参数作为 target
            result["target"] = " ".join(args)
            result["mode"] = "direct"

        return result

    def get_command_list(self) -> list[dict]:
        """返回所有注册命令的列表，供 /help 展示使用。

        Returns:
            包含 trigger, description, usage 的字典列表
        """
        return [
            {
                "trigger": c["trigger"],
                "description": c["description"],
                "usage": c.get("usage", ""),
            }
            for c in self.commands.values()
        ]
