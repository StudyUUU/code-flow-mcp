"""一个简单的代码分析示例"""
import json


def read_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def validate(data: dict) -> bool:
    return "name" in data


def transform(data: dict) -> dict:
    data["level"] = data.get("level", 0) + 1
    return data


def save_result(data: dict, path: str):
    with open(path, "w") as f:
        json.dump(data, f)


class MCPClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    def call_tool(self, name: str, args: dict) -> str:
        return f"called {name} with {args}"

    def read_resource(self, uri: str) -> str:
        resources = {"memory://state": '{"status": "ok"}'}
        return resources.get(uri, "")


class Processor:
    def __init__(self, source: str):
        self.source = source
        self.client = MCPClient("http://localhost:9999")

    def run(self) -> str:
        config = read_config(self.source)
        if not validate(config):
            return "invalid config"
        result = transform(config)
        save_result(result, "/tmp/output.json")
        return "done"

    def run_with_mcp(self) -> str:
        tool_result = self.client.call_tool("parse", {"input": self.source})
        resource = self.client.read_resource("memory://state")
        return f"{tool_result} | {resource}"


def main():
    p = Processor("config.json")
    print(p.run())
    print(p.run_with_mcp())


if __name__ == "__main__":
    main()
