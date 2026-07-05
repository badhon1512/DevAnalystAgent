import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp.server"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = [tool.name for tool in tools.tools]
            print("TraceStock MCP tools:")
            for name in tool_names:
                print(f"- {name}")

            result = await session.call_tool("tracestock_mcp_status", {})
            print("\nStatus tool result:")
            print(result.content[0].text if result.content else result)


if __name__ == "__main__":
    asyncio.run(main())
