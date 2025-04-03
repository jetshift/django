import importlib.metadata


# @click.command(help='Show the current version of JetShift.')
def show_version():
    output = ""

    try:
        js_version = importlib.metadata.version("jetshift")
        output += f"JetShift v{js_version}\n"
    except importlib.metadata.PackageNotFoundError:
        output += "JetShift version not found.\n"

    try:
        js_core_version = importlib.metadata.version("jetshift-core")
        output += f"JetShift Core v{js_core_version}\n"
    except importlib.metadata.PackageNotFoundError:
        output += "JetShift Core version not found.\n"

    return output


if __name__ == "__main__":
    show_version()
