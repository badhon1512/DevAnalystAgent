from pathlib import Path

from langchain_community.agent_toolkits import FileManagementToolkit

FRONTEND_ROOT = Path(__file__).resolve().parents[3] / "frontend"


def get_file_management_toolkit() -> list:
    toolkit = FileManagementToolkit(
        root_dir=str(FRONTEND_ROOT),
        selected_tools=["read_file", "write_file", "list_directory"],
    )
    return toolkit.get_tools()
