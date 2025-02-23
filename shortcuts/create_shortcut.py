import os
import typer
from pyshortcuts import make_shortcut

app = typer.Typer()

@app.command()
def create_shortcut(
    script_path: str = typer.Argument(..., help="Full path to the Python script"),
    app_name: str = typer.Argument(..., help="Name for the desktop shortcut"),
    icon: str = typer.Argument(None, help="Path to the icon file (optional)"),
    terminal: bool = typer.Option(True, "--terminal", "-t", help="Run the script in a terminal (set to False for GUI apps)")
):
    """
    Create a desktop shortcut for a Python script.
    """
    if not os.path.exists(script_path):
        typer.echo(f"Error: The script path '{script_path}' does not exist.")
        raise typer.Exit(code=1)
    
    if icon:
        if not os.path.exists(icon):
            typer.echo(f"Warning: Icon file '{icon}' not found. Shortcut will be created without an icon.")
            icon = None

    try:
        make_shortcut(script_path,
                      name=app_name,
                      desktop=True,    # Place the shortcut on the desktop.
                      terminal=terminal,
                      icon=icon)
        typer.echo("Desktop shortcut created successfully.")
    except PermissionError as e:
        typer.echo("PermissionError: Unable to create the desktop shortcut.")
        typer.echo(str(e))
    except Exception as e:
        typer.echo("An error occurred while creating the shortcut:")
        typer.echo(str(e))

if __name__ == '__main__':
    app()
