from langchain_community.agent_toolkits import FileManagementToolkit


def get_file_management_toolkit() -> list:
    toolkit = FileManagementToolkit(
        root_dir="./",
        selected_tools=["read_file", "write_file", "list_directory"],
    )
    return toolkit.get_tools()
