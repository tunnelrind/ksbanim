from ksbanim import *

createWindow()


input = drawInput("name")

def print_input():
    print(input.getText())

move(0,-100)
drawButton("submit", print_input)
drawLabel("hello\ngoodbye")
run()