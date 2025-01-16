from pyfiglet import Figlet

def display_banner(text:str) -> None:
    f = Figlet(width=200)
    print(f.renderText(text))
