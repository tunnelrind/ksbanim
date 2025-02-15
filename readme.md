# ksbanim

The python module **ksbanim** supports the drawing of primitive shapes and user input objects. Through its simple design, students can learn the basic principles of programming.

## Features

* position and rotate primitive shapes
* draw circles, ellipses, rectangles, triangle and more
* draw buttons, labels, text inputs and more
* manage keyboard and mouse input
* animate shape transitions

## Installation

In the explorer view, use the buttons at the botto mleft (KSBANIM) to install the necessary dependencies.

<img src="https://raw.githubusercontent.com/tunnelrind/ksbanim/4661cfacc0b00a21fbcded36300b883c65a80a2a/images/screenshot.png" alt="screenshot" width="200"/>

A working installation of python3 and pip is necessary. So go and install python first.

* download python extension for VSC
* download PyQt5 (is getting installed via pip)
* download ksbanim.py (to the active working directory)

## Usage Example

from ksbanim import *

createWindow()

setPos(500,500)
setRot(45)
drawCircle(100)

run()

## Contributing

If you have any questions, feel free to ask.

## License

GPL-3.0 

The graphics is based on PyQt5. ksbanim is free software for educational purposes.