"""
Print terminal banner utilities.
"""
from pyfiglet import Figlet # type: ignore

def display_banner(text:str) -> None:
    """
    Displays a banner with the given text using the Figlet library.

    Args:
        text (str): The text to be displayed as a banner.

    Returns:
        None
    """
    f = Figlet(width=200)
    print(f.renderText(text))
