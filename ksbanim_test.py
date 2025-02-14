import sys
import math
import traceback 
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QDesktopWidget, QLineEdit, QLabel, QVBoxLayout
from PyQt5.QtGui import QPainter, QBrush, QPen, QPixmap, QColor, QPolygon, QTransform, QFont, QFontMetrics
from PyQt5.QtCore import Qt, QTimer, QPoint, QElapsedTimer, QRect

# ==================================== INTERPOLATION/ACTIONS ===========================================
def interpolate(begin_value, end_value, fraction):
    if (isinstance(begin_value, list) or isinstance(begin_value, tuple)) and (isinstance(end_value, tuple) or isinstance(end_value, list)):
        if isinstance(begin_value[0], list) or isinstance(begin_value[0], tuple):
            return list([interpolate(begin_value[i], end_value[i], fraction) for i in range(len(begin_value))])
        else:
            return list([INTERPOLATION_FUNCTION(begin_value[i], end_value[i], fraction) for i in range(len(begin_value))])
    else:
        return INTERPOLATION_FUNCTION(begin_value, end_value, fraction)

def linear(begin_value, end_value, fraction):
    if fraction > 1:
        return end_value 
    if fraction < 0:
        return begin_value 
    else:
        return end_value * fraction + begin_value * (1 - fraction)

def cubic_ease_in_out(t):
    if t < 0.5:
        return 4 * t * t * t
    else:
        return (t - 1) * (2 * t - 2) * (2 * t - 2) + 1

def smooth(begin_value, end_value, fraction):
    if fraction > 1:
        return end_value 
    if fraction < 0:
        return begin_value 
    else:
        fraction = cubic_ease_in_out(fraction)
        return end_value * fraction + begin_value * (1 - fraction)

INTERPOLATION_FUNCTION = smooth

class kInterpolator:
    def __init__(self, end_value, getter, setter):
        self.begin_time = kstore.milliseconds
        self.end_time = kstore.animation + kstore.milliseconds
        self.dt = self.end_time - self.begin_time
        self.end_value = end_value
        self.getter = getter
        self.setter = setter
        self.begin_value = getter()
        
    def process(self, the_time):
        if the_time >= self.end_time:
            value = interpolate(self.begin_value, self.end_value, 1)
            self.setter(value)

            return -1 
        elif the_time < self.begin_time:
            self.begin_value = self.getter()
            return 0
        
        fraction = (the_time - self.begin_time)/self.dt

        value = interpolate(self.begin_value, self.end_value, fraction)

        self.setter(value)

        return 1

class kLoop:
    def __init__(self, loop_function, milliseconds):
        self.begin_time = kstore.milliseconds
        self.loop_function = loop_function 
        self.milliseconds = milliseconds

    def process(self, the_time):
        if self.begin_time <= the_time:
            self.loop_function()
            self.begin_time += self.milliseconds
            return 1
        else:
            return 0
        
class kAction:
    def __init__(self, action_function):
        self.begin_time = kstore.milliseconds
        self.action_function = action_function
    
    def process(self, the_time):
        if self.begin_time <= the_time:
            self.action_function()
            return -1
        else:
            return 0

class kSetter:
    def __init__(self, action_function, *args):
        self.begin_time = kstore.milliseconds
        self.action_function = action_function
        self.args = args
    
    def process(self, the_time):
        if self.begin_time <= the_time:
            self.action_function(*self.args)

            return -1
        else:
            return 0

class kActionQueue:
    def __init__(self):
        self.queue = []

    def add(self, action):
        self.queue.append(action)
        kstore.milliseconds += kstore.delay
    
    def process(self):
        i = 0
        the_time = kstore.elapsed_timer.elapsed()
        while i < len(self.queue):
            action = self.queue[i]
            if action.process(the_time) == -1:
                self.queue.pop(i)
            else:
                i = i + 1

action_queue = kActionQueue()

# ==================================== HELPER CLASSES ===========================================

def kInt(instance, name, initial_value):
    name = name
    private_name = f"_{name}"
    capitalized_name = name[0].upper() + name[1:]
    getter_name = f"get{capitalized_name}"
    setter_name = f"set{capitalized_name}"

    setattr(instance, private_name, int(initial_value))
    setattr(instance, name, int(initial_value))

    def private_getter():
        return getattr(instance, private_name)

    def private_setter(value):
        setattr(instance, private_name, int(value))
        instance.draw()

    def public_getter():
        return getattr(instance, name, initial_value)

    def public_setter(value):
        setattr(instance, name, int(value))
        action_queue.add(kInterpolator(int(value), private_getter, private_setter))

    setattr(instance, f"_{getter_name}", private_getter)
    setattr(instance, f"_{setter_name}", private_setter)
    setattr(instance, f"{getter_name}", public_getter)
    setattr(instance, f"{setter_name}", public_setter)

    def public_set_both(value):
        setattr(instance, private_name, int(value))
        setattr(instance, name, int(value))

    setattr(instance, f"init{name}", public_set_both)

    return (public_getter, public_setter)

def kValue(instance, name, initial_value):
    name = name
    private_name = f"_{name}"
    capitalized_name = name[0].upper() + name[1:]
    getter_name = f"get{capitalized_name}"
    setter_name = f"set{capitalized_name}"

    setattr(instance, private_name, initial_value)
    setattr(instance, name, initial_value)

    def private_getter():
        return getattr(instance, private_name)

    def private_setter(value):
        setattr(instance, private_name, value)
        instance.draw()

    def public_getter():
        return getattr(instance, name, initial_value)

    def public_setter(value):
        setattr(instance, name, value)
        action_queue.add(kSetter(private_setter, value))
    
    
    setattr(instance, f"_{getter_name}", private_getter)
    setattr(instance, f"_{setter_name}", private_setter)
    setattr(instance, f"{getter_name}", public_getter)
    setattr(instance, f"{setter_name}", public_setter)

    def public_set_both(value):
        setattr(instance, private_name, value)
        setattr(instance, name, value)

    setattr(instance, f"init{capitalized_name}", public_set_both)

    return (public_getter, public_setter)

def kVec2(instance, name, *initial_value):
    name = name
    private_name = f"_{name}"
    capitalized_name = name[0].upper() + name[1:]
    getter_name = f"get{capitalized_name}"
    setter_name = f"set{capitalized_name}"

    setattr(instance, private_name, toIntList(initial_value))
    setattr(instance, name, toIntList(initial_value))

    # > (x,y)

    def private_getter():
        return getattr(instance, private_name)

    def private_setter_draw(*value):
        setattr(instance, private_name, toIntList(value))
        instance.draw()

    def private_setter_no_draw(*value):
        setattr(instance, private_name, toIntList(value))

    if name == "pos":
        private_setter = private_setter_no_draw
    else:
        private_setter = private_setter_draw

    def public_getter():
        return getattr(instance, name, initial_value)

    def public_setter(*value):
        setattr(instance, name, toIntList(value))
        action_queue.add(kInterpolator(toIntList(value), private_getter, private_setter))

    
    setattr(instance, f"_{getter_name}", private_getter)
    setattr(instance, f"_{setter_name}", private_setter)
    setattr(instance, f"{getter_name}", public_getter)
    setattr(instance, f"{setter_name}", public_setter)

    def public_set_both(value):
        setattr(instance, private_name, toIntList(value))
        setattr(instance, name, toIntList(value))

    setattr(instance, f"init{capitalized_name}", public_set_both)

    # > x

    def private_getter_x():
        value = private_getter()
        return value[0]

    def private_setter_x(value):
        old_value = private_getter()
        private_setter(int(value), old_value[1])
    
    def public_getter_x():
        value = public_getter()
        return value[0]

    def public_setter_x(value):
        old_value = public_getter()
        old_value[0] = int(value)
        setattr(instance, name, old_value)
        action_queue.add(kInterpolator(value, private_getter_x, private_setter_x))

    setattr(instance, f"_{getter_name}X", private_getter_x)
    setattr(instance, f"_{setter_name}X", private_setter_x)
    setattr(instance, f"{getter_name}X", public_getter_x)
    setattr(instance, f"{setter_name}X", public_setter_x)

    # > y 

    def private_getter_y():
        value = private_getter()
        return value[1]

    def private_setter_y(value):
        old_value = private_getter()
        private_setter(old_value[0], int(value))
    
    def public_getter_y():
        value = public_getter()
        return value[1]

    def public_setter_y(value):
        old_value = public_getter()
        old_value[1] = int(value)
        setattr(instance, name, old_value)
        action_queue.add(kInterpolator(value, private_getter_y, private_setter_y))

    setattr(instance, f"_{getter_name}Y", private_getter_y)
    setattr(instance, f"_{setter_name}Y", private_setter_y)
    setattr(instance, f"{getter_name}Y", public_getter_y)
    setattr(instance, f"{setter_name}Y", public_setter_y)

    return (public_getter, public_setter, public_getter_x, public_setter_x, public_getter_y, public_setter_y)

def kColor(instance, name, *args):
    name = name
    private_name = f"_{name}"
    capitalized_name = name[0].upper() + name[1:]
    getter_name = f"get{capitalized_name}"
    setter_name = f"set{capitalized_name}"


    initial_value = toColor(args)
    
    setattr(instance, private_name, toIntList(initial_value))
    setattr(instance, name, toIntList(initial_value))

    # > rgba

    def private_getter():
        return getattr(instance, private_name)

    def private_setter(*value):
        setattr(instance, private_name, toIntList(value))
        instance.draw()

    def public_getter():
        return getattr(instance, name, initial_value)

    def public_setter(*value):
        setattr(instance, name, toIntList(value))
        action_queue.add(kInterpolator(toIntList(value), private_getter, private_setter))

    setattr(instance, f"_{getter_name}", private_getter)
    setattr(instance, f"_{setter_name}", private_setter)
    setattr(instance, f"{getter_name}", public_setter)
    setattr(instance, f"{setter_name}", public_getter)

    def public_set_both(value):
        setattr(instance, private_name, toColor(value))
        setattr(instance, name, toColor(value))

    setattr(instance, f"init{capitalized_name}", public_set_both)

    # > red 

    def private_getter_r():
        value = private_getter()
        return value[0]
    
    def private_setter_r(value):
        old_value = private_getter()
        private_setter(int(value), old_value[1], old_value[2], old_value[3])

    def public_getter_r():
        value = public_getter()
        return value[0]

    def public_setter_r(value):
        old_value = public_getter()
        old_value[0] = int(value) 
        setattr(instance, name, old_value)
        action_queue.add(kInterpolator(value, private_getter_r, private_setter_r))
    
    setattr(instance, f"_{getter_name}R", private_getter_r)
    setattr(instance, f"_{setter_name}R", private_setter_r)
    setattr(instance, f"{getter_name}R", public_setter_r)
    setattr(instance, f"{setter_name}R", public_getter_r)
    
    # > green 

    def private_getter_g():
        value = private_getter()
        return value[1]
    
    def private_setter_g(value):
        old_value = private_getter()
        private_setter(old_value[0], int(value), old_value[2], old_value[3])

    def public_getter_g():
        value = public_getter()
        return value[1]

    def public_setter_g(value):
        old_value = public_getter()
        old_value[1] = int(value) 
        setattr(instance, name, old_value)
        action_queue.add(kInterpolator(value, private_getter_g, private_setter_g))

    setattr(instance, f"_{getter_name}G", private_getter_g)
    setattr(instance, f"_{setter_name}G", private_setter_g)
    setattr(instance, f"{getter_name}G", public_setter_g)
    setattr(instance, f"{setter_name}G", public_getter_g)
    
    # > blue 

    def private_getter_b():
        value = private_getter()
        return value[2]
    
    def private_setter_b(value):
        old_value = private_getter()
        private_setter(old_value[0], old_value[1], int(value), old_value[3])

    def public_getter_b():
        value = public_getter()
        return value[2]

    def public_setter_b(value):
        old_value = public_getter()
        old_value[2] = int(value) 
        setattr(instance, name, old_value)
        action_queue.add(kInterpolator(value, private_getter_b, private_setter_b))

    setattr(instance, f"_{getter_name}B", private_getter_b)
    setattr(instance, f"_{setter_name}B", private_setter_b)
    setattr(instance, f"{getter_name}B", public_setter_b)
    setattr(instance, f"{setter_name}B", public_getter_b)

    # > alpha 

    def private_getter_a():
        value = private_getter()
        return value[3]
    
    def private_setter_a(value):
        old_value = private_getter()
        private_setter(old_value[0], old_value[1], old_value[2], int(value))

    def public_getter_a():
        value = public_getter()
        return value[3]

    def public_setter_a(value):
        old_value = public_getter()
        old_value[3] = int(value) 
        setattr(instance, name, old_value)
        action_queue.add(kInterpolator(value, private_getter_a, private_setter_a))

    setattr(instance, f"_{getter_name}A", private_getter_a)
    setattr(instance, f"_{setter_name}A", private_setter_a)
    setattr(instance, f"{getter_name}A", public_getter_a)
    setattr(instance, f"{setter_name}A", public_setter_a)

    # return (public_getter, public_setter, public_getter_r, public_setter_r, public_getter_g, public_setter_g, public_getter_b, public_setter_b, public_getter_a, public_setter_a)
    return (public_getter, public_setter)

def replaceLatex(text):
    latex_to_unicode = {
        r'\\alpha': 'α',
        r'\\beta': 'β',
        r'\\gamma': 'γ',
        r'\\delta': 'δ',
        r'\\epsilon': 'ε',
        r'\\zeta': 'ζ',
        r'\\eta': 'η',
        r'\\theta': 'θ',
        r'\\iota': 'ι',
        r'\\kappa': 'κ',
        r'\\lambda': 'λ',
        r'\\mu': 'μ',
        r'\\nu': 'ν',
        r'\\xi': 'ξ',
        r'\\omicron': 'ο',
        r'\\pi': 'π',
        r'\\rho': 'ρ',
        r'\\sigma': 'σ',
        r'\\tau': 'τ',
        r'\\upsilon': 'υ',
        r'\\phi': 'φ',
        r'\\chi': 'χ',
        r'\\psi': 'ψ',
        r'\\omega': 'ω',
        r'\\Alpha': 'Α',
        r'\\Beta': 'Β',
        r'\\Gamma': 'Γ',
        r'\\Delta': 'Δ',
        r'\\Epsilon': 'Ε',
        r'\\Zeta': 'Ζ',
        r'\\Eta': 'Η',
        r'\\Theta': 'Θ',
        r'\\Iota': 'Ι',
        r'\\Kappa': 'Κ',
        r'\\Lambda': 'Λ',
        r'\\Mu': 'Μ',
        r'\\Nu': 'Ν',
        r'\\Xi': 'Ξ',
        r'\\Omicron': 'Ο',
        r'\\Pi': 'Π',
        r'\\Rho': 'Ρ',
        r'\\Sigma': 'Σ',
        r'\\Tau': 'Τ',
        r'\\Upsilon': 'Υ',
        r'\\Phi': 'Φ',
        r'\\Chi': 'Χ',
        r'\\Psi': 'Ψ',
        r'\\Omega': 'Ω'
    }
    
    # Replace LaTeX symbols with Unicode counterparts
    for latex_symbol, unicode_symbol in latex_to_unicode.items():
        text = text.replace(latex_symbol, unicode_symbol)
    
    # Replace underscores followed by a character with its Unicode subscript counterpart
    subscript_map = {
        '_a': 'ₐ', '_b': 'b', '_c': 'ᶜ', '_d': 'ᵈ', '_f': 'ᶠ', '_g': 'ᵍ', '_e': 'ₑ', '_h': 'ₕ', '_i': 'ᵢ', '_j': 'ⱼ', '_k': 'ₖ', '_l': 'ₗ', '_m': 'ₘ', '_n': 'ₙ', '_o': 'ₒ', '_p': 'ₚ', '_r': 'ᵣ', 
        '_s': 'ₛ', '_t': 'ₜ', '_u': 'ᵤ', '_v': 'ᵥ', '_x': 'ₓ', '_y': 'ᵧ', '_z': 'ᶻ', 
        '_0': '₀', '_1': '₁', '_2': '₂', '_3': '₃', '_4': '₄', '_5': '₅', 
        '_6': '₆', '_7': '₇', '_8': '₈', '_9': '₉'
    }
    
    for subscript, unicode_subscript in subscript_map.items():
        text = text.replace(subscript, unicode_subscript)
    
    # Replace ^ followed by a character with its Unicode superscript counterpart
    superscript_map = {
        '^a': 'ᵃ', '^b': 'ᵇ', '^c': 'ᶜ', '^d': 'ᵈ', '^e': 'ᵉ', '^f': 'ᶠ', 
        '^g': 'ᵍ', '^h': 'ʰ', '^i': 'ⁱ', '^j': 'ʲ', '^k': 'ᵏ', '^l': 'ˡ', 
        '^m': 'ᵐ', '^n': 'ⁿ', '^o': 'ᵒ', '^p': 'ᵖ', '^q': 'q', '^r': 'ʳ', '^s': 'ˢ', 
        '^t': 'ᵗ', '^u': 'ᵘ', '^v': 'ᵛ', '^w': 'ʷ', '^x': 'ˣ', '^y': 'ʸ', '^z': 'ᶻ',
        '^0': '⁰', '^1': '¹', '^2': '²', '^3': '³', '^4': '⁴', '^5': '⁵', 
        '^6': '⁶', '^7': '⁷', '^8': '⁸', '^9': '⁹'
    }
    
    for superscript, unicode_superscript in superscript_map.items():
        text = text.replace(superscript, unicode_superscript)
    
    # Replace \cdot with a dot
    text = text.replace(r'\\cdot', '·')
    
    return text    

def toIntList(args):
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        return list([int(a) for a in args[0]])
    else:
        return list([int(a) for a in args])
    
def toColor(args):
    if len(args) == 1 and isinstance(args[0], list):
        if len(args[0]) == 3:
            r, g, b = args[0]
            a = 255
        elif len(args[0]) == 4:
            r, g, b, a = args[0]
        else:
            raise ValueError("List must have 3 or 4 elements")
    elif len(args) == 3:
        r, g, b = args
        a = 255
    elif len(args) == 4:
        r, g, b, a = args
    else:
        raise ValueError("Invalid arguments")

    return [r,g,b,a]

class kStore:
    def __init__(self):
        self.app = None 
        self.pixmap = None 
        self.size = [1000, 1000]
        self.pos = [500,500]
        self.rot = 0
        self.timer = None 
        self.dt = 0
        self.milliseconds = 0
        self.delay = 50
        self.animation = 500
        self.line = False 
        self.lineColor = [200,150,30, 255]
        self.lineWidth = 2
        self.fill = True
        self.fillColor = [255,200,50, 255]
        self.show_grid = True 
        self.cursor = None 
        self.draw_cursor = True 
        self.fontSize = 12 
        self.fontColor = [255,255,255, 255]
        self.backgroundColor = [0,0,0,255]

    def setPos(self, *point):
        self.pos = toIntList(point)
        self.scaleAnim(0)
        self.cursor.setPos(self.pos)
        self.unscaleAnim()

    def getPos(self):
        return self.pos.copy()

    def setX(self, x):
        setPos(x, self.pos[1])
    
    def getX(self):
        return self.pos[0]
    
    def setY(self, y):
        setPos(self.pos[0], y)
    
    def getY(self):
        return self.pos[1]
    
    def setRot(self, angle):
        self.rot = int(angle)
        self.scaleAnim(0)
        self.cursor.setRot(angle)
        self.unscaleAnim()

    def getRot(self):
        return self.rot

    def getColor(self):
        return self.fillColor
    
    def setColor(self, *rgba):
        color = toColor(rgba)
        self.lineColor = color
        self.fillColor = color
        self.scaleAnim(0)
        self.cursor.setColor(color)
        self.unscaleAnim()

    def getFillColor(self):
        return self.fillColor
    
    def setFillColor(self, *rgba):
        color = toColor(rgba)
        self.fillColor = color
        self.scaleAnim(0)
        self.cursor.setFillColor(color)
        self.unscaleAnim()

    def getFontColor(self):
        return self.fontColor
    
    def setFontColor(self, *rgb):
        self.fontColor = toColor(rgb)

    def getLineColor(self):
        return self.lineColor
    
    def setLineColor(self, *rgba):
        color = toColor(rgba)
        self.lineColor = color
        self.scaleAnim(0)
        self.cursor.setLineColor(color)
        self.unscaleAnim()

    def getFontSize(self):
        return self.fontSize
    
    def setFontsize(self, size):
        self.fontSize = int(size)

    def scaleAnim(self, factor):
        self._animation = self.animation
        self.animation = int(self.animation*factor)
        self._delay = self.delay 
        self.delay = int(self.delay*factor)

    def unscaleAnim(self):
        self.animation = self._animation 
        self.delay = self._delay 

kstore = kStore()

# ==================================== SHAPES ===========================================

shape_buffer = []
input_buffer = []

class kShape:
    def __init__(self):
        self._pixmap = None
        self._painter = None 
        self._transform = QTransform()
        
        self.getReady, self.setReady = kValue(self, "ready", False)

        self.getRot, self.setRot = kInt(self, "rot", kstore.rot)
        self.getLineWidth, self.setLineWidth = kInt(self, "lineWidth", kstore.lineWidth)

        self.getPos, self.setPos, self.getX, self.setX, self.getY, self.setY = kVec2(self, "pos", kstore.pos)

        self.getFillColor, self.setFillColor = kColor(self, "fillColor", kstore.fillColor)
        self.getLinecolor, self.setLinecolor = kColor(self, "lineColor", kstore.lineColor)

        self.getFill, self.setFill = kValue(self, "fill", kstore.fill)
        self.getLine, self.setLine = kValue(self, "line", kstore.line)

        self.getOnClick, self.setOnClick = kValue(self, "onClick", None)
        self.getOnRelease, self.setOnRelease = kValue(self, "onRelease", None)
        self.getOnMouseEnter, self.setOnMouseEnter = kValue(self, "onMouseEnter", None)
        self.getOnMouseExit, self.setOnMouseExit = kValue(self, "onMouseExit", None)

        self._mouse_over = False

        kstore.scaleAnim(0)
        self.show()
        kstore.unscaleAnim()
        shape_buffer.append(self)

    def show(self):
        self.setReady(True)
    
    def hide(self):
        self.setReady(False)
    
    def _remove(self):
        shape_buffer.remove(self)

    def remove(self):
        self.ready = False
        action_queue.add(kAction(self._remove))

    def getPos(self): pass
    def setPos(self, *point): pass
    def getX(self): pass 
    def setX(self, x): pass 
    def getY(self): pass
    def setY(self, y): pass 

    def getRot(self): pass 
    def setRot(self, angle): pass 

    def move(self, *distance):
        distance = toIntList(distance)
        self.pos[0] += distance[0]
        self.pos[1] += distance[1]
        action_queue.add(kInterpolator(self.pos, self._getPos, self._setPos))

    def rotate(self, angle):
        angle = int(angle)
        self.rot += angle
        action_queue.add(kInterpolator(self.rot, self._getRot, self._setRot))

        return self.pos.copy()

    def getFill(self): pass        
    def setFill(self, value): pass
    def getLine(self): pass         
    def setLine(self, value): pass

    def getLineWidth(self): pass    
    def setLineWidth(self, value): pass

    def _setColor(self, *rgba):
        color = toColor(rgba)
        self._lineColor = color
        self._fillColor = color
        self.draw()

    def getColor(self):
        return self.fillColor

    def _getColor(self):
        return self._fillColor
    
    def setColor(self, *rgba):
        color = toColor(rgba)
        self.lineColor = color
        self.fillColor = color
        action_queue.add(kInterpolator(color, self._getColor, self._setColor))

    def getFillColor(self): pass 
    def setFillColor(self, *rgb): pass
    def getLineColor(self): pass
    def setLineColor(self, *rgb): pass

    def _setPainter(self):
        painter = QPainter(self._pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        if self._fill:
            painter.setBrush(QBrush(QColor(*self._fillColor), Qt.SolidPattern))
        else:
            painter.setBrush(Qt.NoBrush)
        
        if self._line:
            painter.setPen(QPen(QColor(*self._lineColor), self._lineWidth, Qt.SolidLine))
        else:
            painter.setPen(Qt.NoPen)

        self._painter = painter

    def _setTransform(self, size):
        transform = QTransform()
        transform.translate(size, size)
        transform.rotate(self._rot)
        transform.translate(-size, -size)

        self._painter.setTransform(transform)

    def getOnMouseEnter(self): pass
    def setOnMouseEnter(self, handler): pass
    def getOnMouseExit(self): pass
    def setOnMouseExit(self, handler): pass 
    def getOnClick(self): pass
    def setOnClick(self, handler): pass 
    def getOnRelease(self): pass
    def setOnRelease(self, handler): pass

class kEllipse(kShape):
    def __init__(self, a, b):
        super().__init__()
        self.getA, self.setA = kInt(self, "a", a)
        self.getB, self.setB = kInt(self, "b", b)
        
        self._a = 1
        self._b = 1
        self.setA(a)
        self.setB(b)

    def draw(self):
        the_max = max(self._a, self._b)
        self._pixmap = QPixmap(2*the_max, 2*the_max)
        self._pixmap.fill(Qt.transparent)

        if not self._ready:
            return 

        self._setPainter()
        self._setTransform(the_max)

        self._painter.drawEllipse(the_max - self._a, the_max - self._b, self._a * 2, self._b * 2)
        self._painter.end()

    def getA(self): pass        
    def setA(self, a): pass
    def getB(self): pass 
    def setB(self, b): pass

    def contains(self, x, y):
        center_x, center_y = self.pos
        angle_rad = math.radians(self._rot)

        translated_x = x - center_x
        translated_y = y - center_y

        rotated_x = translated_x * math.cos(angle_rad) + translated_y * math.sin(angle_rad)
        rotated_y = -translated_x * math.sin(angle_rad) + translated_y * math.cos(angle_rad)

        return (rotated_x / self._a) ** 2 + (rotated_y / self._b) ** 2 <= 1

class kCircle(kEllipse):
    def __init__(self, radius):
        super().__init__(radius, radius)

    def _getRadius(self):
        return self._a 
    
    def _setRadius(self, radius):
        self._a = int(radius) 
        self._b = int(radius) 
        self.draw()

    def getRadius(self):
        return self.a 

    def setRadius(self, radius):
        self.a = int(radius) 
        self.b = int(radius)
        action_queue.add(kInterpolator(radius, self._getRadius, self._setRadius))


class kRect(kShape):
    def __init__(self, *size):
        super().__init__()
        self.getSize, self.setSize, self.getWidth, self.setWidth, self.getHeight, self.setHeight = kVec2(self, "size", size)

        self._size[0] = 1
        self._size[1] = 1

        kstore.scaleAnim(0.5)
        self.setWidth(size[0])
        self.setHeight(size[1])
        kstore.unscaleAnim()

    def draw(self):            
        the_max = max(self._size[0], self._size[1])
        the_max = int(1.42*the_max)
        self._pixmap = QPixmap(2*the_max, 2*the_max)
        self._pixmap.fill(Qt.transparent)

        if not self._ready:
            return 

        self._setPainter()
        self._setTransform(the_max)

        self._painter.drawRect(the_max, the_max, self._size[0], self._size[1])
        self._painter.end()

    def getWidth(self): pass    
    def setWidth(self, width): pass
    def getHeight(self): pass
    def setHeight(self, height): pass
    def getSize(self): pass
    def setSize(self, *size): pass

    def contains(self, x, y):
        local_x = x - self._pos[0]
        local_y = y - self._pos[1]

        angle = math.radians(self._rot)  
        cos_theta = math.cos(angle)
        sin_theta = math.sin(angle)
        rotated_x = local_x * cos_theta + local_y * sin_theta
        rotated_y = -local_x * sin_theta + local_y * cos_theta

        return (0 <= rotated_x <= self._size[0]) and (0 <= rotated_y <= self._size[1])

class kRoundedRect(kShape):
    def __init__(self, width, height, radius):
        super().__init__()
        self.getSize, self.setSize, self.getWidth, self.setWidth, self.getHeight, self.setHeight = kVec2(self, "size", width, height)
        self.getRadius, self.setRadius = kInt(self, "radius", radius)

        self._size[0] = 1
        self._size[1] = 1
        self._radius = 1 
        self.setCircle(self.radius)
        self.setSize([self.size[0], self.size[1]])

    def draw(self):          
        the_max = max(self._size[0], self._size[1])
        the_max = int(1.42 * the_max)
        self._pixmap = QPixmap(2 * the_max, 2 * the_max)
        self._pixmap.fill(Qt.transparent)

        if not self._ready:
            return 

        self._setPainter()
        self._setTransform(the_max)

        self._painter.drawRoundedRect(the_max, the_max, self._size[0], self._size[1], self._radius, self._radius)
        self._painter.end()

    def getWidth(self): pass
    def setWidth(self, width): pass
    def getHeight(self): pass
    def setHeight(self, height): pass
    def getSize(self): pass
    def setSize(self, *size): pass
    def getRadius(self): pass
    def setRadius(self, radius): pass

    def _setCircle(self, radius):
        radius = int(radius)
        self._size[0] = 2*radius
        self._size[1]= 2*radius
        self._radius = radius
        self.draw()

    def setCircle(self, radius):
        self.radius = radius
        action_queue.add(kInterpolator(radius, self._getRadius, self._setCircle))
    
    def contains(self, x, y):
        local_x = x - self._pos[0]
        local_y = y - self._pos[1]

        angle = math.radians(self._rot)
        cos_theta = math.cos(angle)
        sin_theta = math.sin(angle)
        rotated_x = local_x * cos_theta + local_y * sin_theta
        rotated_y = -local_x * sin_theta + local_y * cos_theta

        if (self._radius <= rotated_x <= self._size[0] - self._radius) and (0 <= rotated_y <= self._size[1]):
            return True
        if (0 <= rotated_x <= self._size[0]) and (self._radius <= rotated_y <= self._size[1] - self._radius):
            return True

        corner_centers = [
            (self._radius, self._radius),
            (self._size[0] - self._radius, self._radius),
            (self._radius, self._size[1] - self._radius),
            (self._size[0] - self._radius, self._size[1] - self._radius)
        ]
        for cx, cy in corner_centers:
            if (rotated_x - cx) ** 2 + (rotated_y - cy) ** 2 <= self._radius ** 2:
                return True

        return False

class kTriangle(kShape):
    def __init__(self, length):
        super().__init__()
        self.getLength, self.setLength = kInt(self, "length", length)

        self._length = 1
        self.setLength(length)

    def draw(self):
        the_max = self._length
        self._pixmap = QPixmap(2 * the_max, 2 * the_max)
        self._pixmap.fill(Qt.transparent)

        if not self._ready:
            return 
            
        self._setPainter()
        self._setTransform(the_max)

        half_side = self._length // 2
        height = int((self._length * (3 ** 0.5)) / 2)
        points = [
            QPoint(the_max, the_max),
            QPoint(the_max + self._length, the_max),
            QPoint(the_max + half_side, the_max + height)
        ]

        self._painter.drawPolygon(QPolygon(points))
        self._painter.end()

    def getLength(self): pass
    def setLength(self, length): pass

    def contains(self, x, y):
        local_x = x - self._pos[0]
        local_y = y - self._pos[1]

        angle = math.radians(self._rot)
        cos_theta = math.cos(angle)
        sin_theta = math.sin(angle)
        rotated_x = local_x * cos_theta + local_y * sin_theta
        rotated_y = -local_x * sin_theta + local_y * cos_theta

        height = (math.sqrt(3) / 2) * self._length

        v0 = (self._length, 0)
        v1 = (self._length / 2, height)
        v2 = (0, 0)

        def sign(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

        b1 = sign((rotated_x, rotated_y), v0, v1) < 0.0
        b2 = sign((rotated_x, rotated_y), v1, v2) < 0.0
        b3 = sign((rotated_x, rotated_y), v2, v0) < 0.0

        return (b1 == b2) and (b2 == b3)

class kCursor(kTriangle):
    def __init__(self):
        super().__init__(12)
        shape_buffer.remove(self)

        self._line = True
        self._line_width = 2
        
    def draw(self):           
        the_max = self._length
        self._pixmap = QPixmap(2*the_max, 2*the_max)
        self._pixmap.fill(Qt.transparent)

        if not self._ready:
            return 

        self._setPainter()
        self._setTransform(the_max)

        half_side = self._length // 3
        height = self._length
        points = [
            QPoint(the_max, the_max-half_side),
            QPoint(the_max + +height, the_max),
            QPoint(the_max, the_max+half_side),
        ]

        self._painter.drawPolygon(QPolygon(points))

        self._painter.end()

class kArc(kShape):
    def __init__(self, radius, angle):
        super().__init__()
        self.getRadius, self.setRadius = kInt(self, "radius", radius)
        self.getAngle, self.setAngle = kInt(self, "angle", angle)

        self._angle = 1
        self.setAngle(angle)

    def draw(self):
        the_max = int(self._radius)
        self._pixmap = QPixmap(2 * the_max, 2 * the_max)
        self._pixmap.fill(Qt.transparent)

        if not self._ready:
            return 
            
        self._setPainter()
        self._setTransform(the_max)
        
        rect = QRect(0, 0, 2 * self._radius, 2 * self._radius)
        self._painter.drawPie(rect, 0, -self._angle * 16)

    def getRadius(self): pass
    def setRadius(self, radius): pass
    def getAngle(self): pass
    def setAngle(self, angle): pass

    def contains(self, x, y):
        local_x = x - self._pos[0]
        local_y = y - self._pos[1]

        rot_radians = math.radians(self._rot+self._angle//2)
        cos_theta = math.cos(rot_radians)
        sin_theta = math.sin(rot_radians)
        rotated_x = local_x * cos_theta + local_y * sin_theta
        rotated_y = -local_x * sin_theta + local_y * cos_theta

        distance_squared = rotated_x ** 2 + rotated_y ** 2
        if distance_squared > self._radius ** 2:
            return False

        point_angle = math.degrees(math.atan2(rotated_y, rotated_x))
        half_angle = self._angle / 2
        return -half_angle <= point_angle <= half_angle

class kLine(kShape):
    def __init__(self, *size):
        super().__init__()
        self.getSize, self.setSize, self.getWidth, self.setWidth, self.getHeight, self.setHeight = kVec2(self, "size", size)

        self._size[0] = 1
        self._size[1] = 1
        self.setSize(size)

    def _setPainter(self):
        
        painter = QPainter(self._pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(*self._lineColor), self._lineWidth, Qt.SolidLine))
        self._painter = painter

    def draw(self):
        the_max = max(self._size[0], self._size[1])
        the_max = int(1.42*the_max)
        self._pixmap = QPixmap(2*the_max, 2*the_max)
        self._pixmap.fill(Qt.transparent)

        if not self._ready:
            return 
            
        self._setPainter()
        self._setTransform(the_max)

        self._painter.drawLine(the_max, the_max, the_max + self._size[0], the_max + self._size[1])
        self._painter.end()

    def getWidth(self): pass
    def setWidth(self, width): pass
    def getHeight(self): pass
    def setHeight(self, height): pass
    def getSize(self): pass
    def setSize(self, *size): pass

    def contains(self, x, y):
        local_x = x - self._pos[0]
        local_y = y - self._pos[1]

        line_angle = math.atan2(self._size[0], self._size[1])

        total_rot = line_angle + math.radians(self._rot)
        cos_theta = math.cos(total_rot)
        sin_theta = math.sin(total_rot)
        rotated_x = local_x * cos_theta + local_y * sin_theta
        rotated_y = -local_x * sin_theta + local_y * cos_theta

        line_length = math.sqrt(self._size[0] ** 2 + self._size[1] ** 2)

        if 0 <= rotated_x <= line_length:
            return abs(rotated_y) <= self._lineWidth / 2

        return False

class kVector(kLine):
    def _setPainter(self):
        painter = QPainter(self._pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(*self._fillColor), Qt.SolidPattern))
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(*self._lineColor), self._lineWidth, Qt.SolidLine))

        self._painter = painter

    def draw(self):
        the_max = max(self._size[0], self._size[1])
        the_max = int(1.42*the_max)
        self._pixmap = QPixmap(2*the_max, 2*the_max)
        self._pixmap.fill(Qt.transparent)

        if not self._ready:
            return 
            
        self._setPainter()
        self._setTransform(the_max)

        start_point = QPoint(the_max, the_max)
        end_point = QPoint(the_max + self._size[0], the_max + self._size[1])
        self._painter.drawLine(start_point, end_point)

        # Calculate the arrowhead points
        arrow_size = self._lineWidth*5

        angle = math.atan2(end_point.y() - start_point.y(), end_point.x() - start_point.x())-math.pi/2

        arrow_p1 = end_point + QPoint(int(math.sin(angle - math.pi / 6) * arrow_size),
                                      int(-math.cos(angle - math.pi / 6) * arrow_size))
        arrow_p2 = end_point + QPoint(int(math.sin(angle + math.pi / 6) * arrow_size),
                                      int(-math.cos(angle + math.pi / 6) * arrow_size))

        # Draw the filled triangle arrowhead
        arrow_head = [end_point, arrow_p1, arrow_p2]
        self._painter.setBrush(QBrush(QColor(*self._lineColor), Qt.SolidPattern))
        self._painter.drawPolygon(*arrow_head)

        self._painter.end()

class kButton(kRoundedRect):
    def __init__(self, handler, label=""):
        super().__init__(200, 50, 25)

        self.getHandler, self.setHandler = kValue(self, "handler", handler)
        self.getLabel, self.setLabel = kValue(self, "label", label)
        self.getFontSize, self.setFontSize = kInt(self, "fontSize", kstore.fontSize)
        self.getFontColor, self.setFontColor = kColor(self, "fontColor", kstore.fontColor)
        self.getHoverColor, self.setHoverColor = kColor(self, "hoverColor", kstore.fillColor)
        passiveColor = list([int(0.25*c) for c in kstore.fillColor])
        passiveColor[3] = 255
        self.getPassiveColor, self.setPassivecolor = kColor(self, "passiveColor", passiveColor)

        self.initLine(True)
        self.initFillColor(passiveColor)
        self.initOnClick(self._onButtonClick)
        self.initOnMouseEnter(self._onButtonMouseEnter)
        self.initOnMouseExit(self._onButtonMouseExit)

    def getFontColor(self): pass
    def setFontColor(self, *rgb): pass
    def getFontSize(self): pass
    def setFontSize(self, size): pass
    def getHandler(self): pass
    def setHandler(self, handler): pass
    def getLabel(self): pass
    def setLabel(self, label): pass

    def _onButtonClick(self, x, y, button):
        self._handler()

    def _onButtonMouseEnter(self):
        self.setFillColor(self.hoverColor)
    
    def _onButtonMouseExit(self):
        self.setFillColor(self.passiveColor)

    def draw(self):            
        the_max = max(self._size[0], self._size[1])
        the_max = int(1.42 * the_max)
        self._pixmap = QPixmap(2 * the_max, 2 * the_max)
        self._pixmap.fill(Qt.transparent)

        if not self._ready:
            return 

        self._setPainter()
        self._setTransform(the_max)

        self.rect = QRect(the_max, the_max, self._size[0], self._size[1])
        self._painter.drawRoundedRect(self.rect, self._radius, self._radius)

        self._painter.save()
        self._painter.translate(the_max + self._size[0] / 2, the_max + self._size[1] / 2)
        self._painter.scale(1, -1)  # Flip vertically
        self._painter.translate(-(the_max + self._size[0] / 2), -(the_max + self._size[1] / 2))

        self._painter.setPen(QColor(*self._fontColor))
        font = QFont()
        font.setPointSize(self._fontSize)
        self._painter.setFont(font)
        text_rect = QRect(the_max, the_max, self._size[0], self._size[1])
        self._painter.drawText(text_rect, Qt.AlignCenter, self.label)
        
        self._painter.restore()
        self._painter.end()

class kLabel(kRoundedRect):
    def __init__(self, text=""):
        super().__init__(200, 50, 5)
        self.getPadding, self.setPadding = kInt(self, "padding", 5)
        self.getAlignX, self.setAlignX = kValue(self, "alignX", "left")
        self.getAlignY, self.setAlignY = kValue(self, "alignY", "center")
        self.getOverflow, self.setOverflow = kValue(self, "overflow", "wrap")
        self.getText, self.setText = kValue(self, "text", text)
        self.getFontSize, self.setFontSize = kInt(self, "fontSize", kstore.fontSize)
        self.getFontColor, self.setFontColor = kColor(self, "fontColor", kstore.fontColor)

        self.initLine(True)
        self.initLineColor(kstore.getLineColor())
        self.initFillColor(kstore.backgroundColor)

    def getText(self): pass
    def setText(self, text): pass
    def getAlignX(self): pass
    def setAlignX(self, align): pass
    def getAlignY(self): pass
    def setAlignY(self, align): pass
    def getPadding(self): pass
    def setPadding(self, padding): pass

    def getFontColor(self): pass
    def setFontColor(self, *rgba): pass
    def getFontSize(self): pass
    def setFontSize(self, size): pass

    def getOverflow(self): pass 
    def setOverflow(self, value): pass 

    def _setFont(self):
        self._font = QFont()
        self._font.setPointSize(self._fontSize)
        self._painter.setFont(self._font)
        self._font_metrics = QFontMetrics(self._font)

    def draw(self):
        the_max = max(self._size[0], self._size[1])
        the_max = int(1.42 * the_max)
        self._pixmap = QPixmap(2 * the_max, 2 * the_max)
        self._pixmap.fill(Qt.transparent)

        if not self._ready:
            return

        self._setPainter()
        self._setTransform(the_max)
            
        rect = QRect(the_max, the_max, self._size[0], self._size[1])
        self._painter.drawRoundedRect(rect, self._radius, self._radius)

        self._painter.translate(the_max + self._size[0] / 2, the_max + self._size[1] / 2)
        self._painter.scale(1, -1)  # Flip vertically
        self._painter.translate(-(the_max + self._size[0] / 2), -(the_max + self._size[1] / 2))

        self._setFont()
        self._painter.setPen(QColor(*self._fontColor))

        text_rect = QRect(the_max+self._padding, the_max+self._padding, self._size[0]-2*self._padding, self._size[1]-2*self._padding)

        # Determine horizontal alignment
        if self._alignX == "left":
            h_align = Qt.AlignLeft
        elif self._alignX == "center":
            h_align = Qt.AlignHCenter
        else:  # "right"
            h_align = Qt.AlignRight

        # Determine vertical alignment
        if self._alignY == "top":
            v_align = Qt.AlignTop
        elif self._alignY == "center":
            v_align = Qt.AlignVCenter
        else:  # "bottom"
            v_align = Qt.AlignBottom
        
        the_text = replaceLatex(self._text)
        if self._overflow == "clip":
            self._painter.drawText(text_rect, h_align | v_align, the_text)
        elif self._overflow == "wrap":
            wrapped_text = "\n".join(self._wrapText(the_text, text_rect.width()))
            
            self._painter.drawText(text_rect, h_align | v_align, wrapped_text)
        self._painter.end()
            
    def _wrapText(self, text, width):
        word = ""
        words = []
        for c in text:
            if c == " ":
                if len(word) > 0:
                    words.append(word)
                words.append(c)
                word = ""
            else:
                word += c 

        if len(word) > 0:
            words.append(word)

        lines = []
        current_line = ""
        for word in words:
            if self._font_metrics.width(current_line + word) <= width:
                current_line += word if current_line else word
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        if len(lines) == 0:
            lines.append("")

        return lines

class kInput(kLabel):
    def __init__(self, handler=None, label=""):
        super().__init__(label)

        self.getHandler, self.setHandler = kValue(self, "handler", handler)
        self.getFontsize, self.setFontSize = kInt(self, "fontSize", kstore.fontSize)
        self.getLabel, self.setLabel = kValue(self, "label", label)
        self.getText, self.setText = kValue(self, "text", "")
        self.getAlignX, self.setAlignX = kValue(self, "alignX", "left")
        self.getAlignY, self.setAlignY = kValue(self, "alignY", "center")
        self.getOverflow, self.setOverflow = kValue(self, "overflow", "clip")
        self.getFontColor, self.setFontColor = kColor(self, "fontColor", kstore.fontColor)
        focusColor = list([int(0.25*c) for c in kstore.fillColor])
        focusColor[3] = 255
        self.getFocusColor, self.setFocusColor = kColor(self, "focusColor", focusColor)
        self.getPassiveColor, self.setPassiveColor = kColor(self, "passiveColor", kstore.backgroundColor)

        self.initLine(True)
        self.initFillColor(self._passiveColor)
        self.initLineColor(kstore.getLineColor())
        
        self._onClick = self._onInputClick

        self._cursor_position = len(self._text)
        self._cursor_visible = True

        self._blink_timer = QTimer()
        self._blink_timer.timeout.connect(self._toggle_cursor_visibility)
        self._blink_timer.start(500)

        input_buffer.append(self)

        self._focused = False

    def getHandler(self): pass 
    def setHandler(self, handler): pass
    def getFontsize(self): pass
    def setFontSize(self, size): pass
    def getLabel(self): pass
    def setLabel(self, label): pass
    def getOverflow(self): pass 
    def setOverflow(self, value): pass 
    def getFontColor(self): pass 
    def setFontColor(self, *rgb): pass

    def _toggle_cursor_visibility(self):
        self._cursor_visible = not self._cursor_visible
        if self._ready:
            self.draw()

    def _onInputClick(self, x, y, button):
        self._focused = True
        self.setFillColor(self._focusColor)

    def _onInputRelease(self, x, y, button):
        self._focused = False
        self.setFillColor(self._passiveColor)

    def _emit(self):
        if self._handler:
            self._handler(self._text)
            self._onInputRelease(0,0,0)
    
    def _keyPressEvent(self, event):
        key = event.key()

        if self._focused:
            if key == Qt.Key_Return:
                self._emit()
            elif key == Qt.Key_Backspace:
                if self._cursor_position > 0:
                    self._text = self._text[:self._cursor_position - 1] + self._text[self._cursor_position:]
                    self._cursor_position -= 1
                    self._setText(self._text)
            elif key == Qt.Key_Delete:
                if self._cursor_position < len(self._text):
                    self._text = self._text[:self._cursor_position] + self._text[self._cursor_position + 1:]
                    self._setText(self._text)
            elif key == Qt.Key_Left:
                if self._cursor_position > 0:
                    self._cursor_position -= 1
                    self._cursor_visible = True
                    self.draw()
            elif key == Qt.Key_Right:
                if self._cursor_position < len(self._text):
                    self._cursor_position += 1
                    self._cursor_visible = True
                    self.draw()
            else:  
                new_text = self._text[:self._cursor_position] + event.text() + self._text[self._cursor_position:]
                if self._overflow == "clip":
                    if self._font_metrics.width(new_text) <= self._size[0] - 2 * self._padding:
                        self.text = new_text
                        self._cursor_position += 1
                        self._setText(new_text)
                elif self._overflow == "wrap":
                    lines = self._wrapText(new_text, self._size[0] - 2*self._padding)
                    if len(lines)*self._font_metrics.height() < self._size[1] - 2*self._padding:
                        self.text = new_text
                        self._cursor_position += 1
                        self._setText(new_text)

    def draw(self):
        super().draw()
        self._setPainter()
        self._setFont()
        if self._focused and self._cursor_visible:
            self._draw_cursor()

        self._draw_label()
        self._painter.end()

    def _draw_label(self):
        the_label = "  " + self._label + "  "
        the_max = max(self._size[0], self._size[1])

        font = QFont()
        font.setPointSize(int(self._fontSize*0.7))
        font.setWeight(QFont.Bold)  # Set the font weight to bold
        self._painter.setFont(font)
        font_metrics = QFontMetrics(font)

        width = font_metrics.width(the_label)
        height = font_metrics.height()

        x = 1.41 * the_max + self._radius + 2 * self._padding
        y = 1.41 * the_max + self._size[1] - height/1.3
        
        rect = QRect(int(x), int(y), int(width), int(height))
        line_rect = QRect(int(x), int(y+height*0.65+self._lineWidth), int(width), int(self._lineWidth+1))
        self._painter.setCompositionMode(QPainter.CompositionMode_Clear)
        self._painter.fillRect(line_rect, QColor(255, 255, 0, 255))
        self._painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        self._painter.fillRect(rect, Qt.transparent)
        self._painter.setPen(QColor(*self._lineColor))

        self._painter.translate(x, y + height/1.3)
        self._painter.scale(1, -1)  # Flip vertically
        self._painter.translate(-x, -y - height/1.3)

        self._painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, the_label)


    def _getCursorXY(self, lines):
        line = 0
        delta = self._cursor_position
        width = 0

        while delta > 0:
            if line >= len(lines):
                delta = 0
                width = self._font_metrics.width(lines[-1])
                line -= 1
            elif len(lines[line]) < delta:
                delta -= len(lines[line])
                line += 1
            else:
                width = self._font_metrics.width(lines[line][:delta])
                delta = 0

        # Horizontal alignment with padding
        if self._alignX == "left":
            x = self._padding + width
        elif self._alignX == "center":
            x = (self._size[0] - self._font_metrics.width(lines[line])) // 2 + width
        elif self._alignX == "right":
            x = self._size[0] - self._font_metrics.width(lines[line]) - 2*self._padding + width

        # Vertical alignment with padding
        if self._alignY == "top":
            y = self._padding + line * self._font_metrics.height()
        elif self._alignY == "center":
            y = (self._size[1] - max(len(lines),1) * self._font_metrics.height()) // 2 + line * self._font_metrics.height()
        elif self._alignY == "bottom":
            y = self._size[1] - max(len(lines), 1) * self._font_metrics.height() - self._padding + line * self._font_metrics.height()

        return x, y

    def _draw_cursor(self):
        if self._cursor_visible:
            the_max = int(1.42 * max(self._size[0], self._size[1]))

            if self._overflow == "clip":
                cursor_x, cursor_y = self._getCursorXY([self._text])
                # Ensure the cursor stays within the visible area
                cursor_x = min(cursor_x, self._size[0] - self._padding)
            elif self._overflow == "wrap":
                left_text = self._text
                lines = self._wrapText(left_text, self._size[0] - 2 * self._padding)
                cursor_x, cursor_y = self._getCursorXY(lines)
                # cursor_y = min(cursor_y, self._size[1] - self._padding)

            self._painter.setPen(QColor(*self._fontColor))
            cursor_x += the_max + self._padding
            cursor_y = -cursor_y + the_max + self._size[1] - self._font_metrics.height()
            self._painter.drawLine(cursor_x, cursor_y, cursor_x, cursor_y + self._font_metrics.height())


class kPolygon(kShape):
    def __init__(self, points):
        super().__init__()
        self.points = points
        self._points = points
        self._fillColor.setA(1)
        self.setFillColorA(self.fillColor[3])

    def _setTransform(self, cx, cy):
        transform = QTransform()
        transform.translate(cx, cy)
        transform.rotate(self.rot)
        transform.translate(-cx, -cy)

        self._painter.setTransform(transform)

    def draw(self):
        self._pixmap = QPixmap(kstore.size[0], kstore.size[1])
        self._pixmap.fill(Qt.transparent)
        if not self._ready:
            return 
            
        self._setPainter()

        cx = sum([x for x,y in self._points])/len(self._points)
        cy = sum([y for x,y in self._points])/len(self._points)

        self._setTransform(cx, cy)

        translated_points = [QPoint(int(point[0]), int(point[1])) for point in self._points]
        self._painter.drawPolygon(QPolygon(translated_points))
        self._painter.end()

    def _setPoints(self, points):
        the_points = []
        for point in points:
            the_points.append([int(point[0]), int(point[1])])

        self._points = the_points
        self.draw()

    def getPoints(self):
        return self.points

    def _getPoints(self):
        return self._points 
    
    def setPoints(self, points):
        if len(self.points) > len(points):
            action_queue.add(kSetter(self._setPoints, self.points[:len(points)]))
            action_queue.add(kInterpolator(points, self._getPoints, self._setPoints))
        elif len(self.points) < len(points):
            action_queue.add(kInterpolator(points[:len(self.points)], self._getPoints, self._setPoints))
            action_queue.add(kSetter(self._setPoints, points))

        self.points = points

    def contains(self, x, y):
        cx = sum([px for px, py in self._points]) / len(self._points)
        cy = sum([py for px, py in self._points]) / len(self._points)

        angle = math.radians(self._rot)
        cos_theta = math.cos(angle)
        sin_theta = math.sin(angle)

        local_x = (x - cx) * cos_theta + (y - cy) * sin_theta + cx
        local_y = -(x - cx) * sin_theta + (y - cy) * cos_theta + cy

        n = len(self._points)
        inside = False
        p1x, p1y = self._points[0]
        for i in range(n + 1):
            p2x, p2y = self._points[i % n]
            if local_y > min(p1y, p2y):
                if local_y <= max(p1y, p2y):
                    if local_x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (local_y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or local_x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

class kGrid:
    def __init__(self, window, width, height, scale_factor):
        self._size = [width, height]
        self._scale_factor = scale_factor
        self._label_fontSize = 14
        self._window = window
        self._xlabels = []
        self._ylabels = []
        self._xlabel = None
        self._ylabel = None
        self._pixmap = QPixmap(self._size[0], self._size[1])
        self._pixmap.fill(Qt.transparent)

        self._createLabels()
        self._drawLines()

    def resize(self, width, height):
        self._size[0] = width
        self._size[1] = height
        self._scale_factor = 1
        self.clear()
        self._createLabels()
        self._drawLines()

    def clear(self):
        self._pixmap = QPixmap(self._size[0], self._size[1])
        self._pixmap.fill(Qt.transparent)

        if len(self._xlabels) > 0:
            for label in self._xlabels:
                label.deleteLater()
            for label in self._ylabels:
                label.deleteLater()
            self._xlabel.deleteLater()
            self._ylabel.deleteLater()

            self._xlabels = []
            self._ylabels = []
            self._xlabel = None 
            self._ylabel = None 

        self._createLabels()
        self._drawLines()
        
    def _createLabels(self):
        if not kstore.show_grid:
            return 

        for x in range(0, int(self._size[0]), 100):
            label = QLabel(str(x), self._window)
            label.setStyleSheet(f"color: rgb(200, 200, 200); font-size: {self._label_fontSize}px;")
            label.move(int(x * self._scale_factor), int((self._size[1] - 40) * self._scale_factor))
            label.show()
            self._xlabels.append(label)

        for y in range(0, int(self._size[1]), 100):
            label = QLabel(str(y), self._window)
            label.setStyleSheet(f"color: rgb(200, 200, 200); font-size: {self._label_fontSize}px;")
            label.move(int(20 * self._scale_factor), int((1000 - y) * self._scale_factor))
            label.show()
            self._ylabels.append(label)

        self._xlabel = QLabel("x", self._window)
        self._xlabel.setStyleSheet(f"color: rgb(200, 200, 200); font-size: {self._label_fontSize}px;")
        self._xlabel.move(int((self._size[0] - 20) * self._scale_factor), int((self._size[1] - 40) * self._scale_factor))
        self._xlabel.show()

        self._ylabel = QLabel("y", self._window)
        self._ylabel.setStyleSheet(f"color: rgb(200, 200, 200); font-size: {self._label_fontSize}px;")
        self._ylabel.move(int(20 * self._scale_factor), int(0 * self._scale_factor))
        self._ylabel.show()

    def _drawLines(self):
        if not kstore.show_grid:
            return 

        painter = QPainter(self._pixmap)
        pen = QPen(QColor(200, 200, 200, 50))
        pen.setWidth(1)
        painter.setPen(pen)

        for x in range(100, int(self._size[0]), 100):
            painter.drawLine(x, 0, x, self._size[1])

        for y in range(100, int(self._size[1]), 100):
            painter.drawLine(0, y, self._size[0], y)
        painter.end()
    
# ==================================== MAIN WINDOW CONTROL ===========================================

class kMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ksbg Zeichenfläche")

        self.fps_buffer = []
        self.fps_label = QLabel(self)
        self.fps_label.setStyleSheet("color: white; background-color: black; font-size: 16px;")
        self.fps_label.resize(100, 30)
        self.fps_label.move(900, 10)
        self.fps_label.show()

        self.setSize(kstore.size[0], kstore.size[1])

        kstore.elapsed_timer = QElapsedTimer()
        kstore.grid = kGrid(self, kstore.size[0], kstore.size[1], self.scale_factor)

        self.record = False 
        self.frames = []

        self.key_store = set()
        self.button_store = set()
        self.setMouseTracking(True)
        self.mouse_pos = [0,0]

        kstore.cursor = kCursor()
        kstore.cursor.draw()

    def setSize(self, width, height):
        kstore.size[0] = width
        kstore.size[1] = height
        self.resize(width, height)
        self.setGeometry(0, 0, width,height)
        self.scale_factor = 1
        self.center()
        self.pixmap = QPixmap(kstore.size[0], kstore.size[1])
        self.pixmap.fill(QColor(*kstore.backgroundColor))
        self.fps_label.move(width - 100, 10)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def scaleContent(self):
        screen = QDesktopWidget().availableGeometry()
        self.scale_factor = min((screen.width()-200) / 1000, (screen.height()-200) / 1000)

        self.resize(int(1000 * self.scale_factor), int(1000 * self.scale_factor))

    def paintEvent(self, event):
        self.pixmap.fill(QColor(*kstore.backgroundColor))
        painter = QPainter(self)
        
        transform = QTransform()
        transform.scale(self.scale_factor, -self.scale_factor)  # Flip the y-axis
        transform.translate(0, -kstore.size[1])  # Move the origin to the bottom-left corner
        painter.setTransform(transform)
        
        painter.drawPixmap(0, 0, self.pixmap)
        painter.drawPixmap(0, 0, kstore.grid._pixmap)
        current_time = kstore.elapsed_timer.elapsed()
        if len(self.fps_buffer) > 0:
            elapsed_time = current_time - self.fps_buffer[-1]
            fps = 1000 / elapsed_time if elapsed_time > 0 else 0
            self.fps_buffer.append(current_time)
            if len(self.fps_buffer) > 100:
                self.fps_buffer.pop(0)
            average_fps = sum([1000 / (self.fps_buffer[i] - self.fps_buffer[i - 1]) for i in range(1, len(self.fps_buffer))]) / len(self.fps_buffer)
            self.fps_label.setText(f"fps {average_fps:.2f}")
        else:
            self.fps_buffer.append(current_time)


        for shape in shape_buffer:
            if shape.ready:
                painter.drawPixmap(shape._pos[0]-shape._pixmap.width()//2, shape._pos[1]-shape._pixmap.height()//2, shape._pixmap)

        if kstore.draw_cursor:
            shape = kstore.cursor
            painter.drawPixmap(shape._pos[0]-shape._pixmap.width()//2, shape._pos[1]-shape._pixmap.height()//2, shape._pixmap)

        painter.end()
            
        if self.record:
            self.frames.append(self.captureFrame().toImage())

    def setRecord(self, value):
        self.record = value

    def captureFrame(self):
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(self.winId())
        return screenshot

    def saveAsPng(self, filename):
        screenshot = self.captureFrame()
        screenshot.save(filename + ".png", 'png')

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        
        key_text = event.text()
        for input in input_buffer:
            input._keyPressEvent(event)

        self.key_store.add(key_text)
        for handler in on_key_pressed_handlers:
            if handler[1] == key_text:
                handler[0](key_text)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        
        key_text = event.text()
        if key_text in self.key_store:
            self.key_store.remove(key_text)
        for handler in on_key_released_handlers:
            if handler[1] == key_text:
                handler[0](key_text)

    def isKeyPressed(self, key):
        return key in self.key_store

    def getButtonText(self, button):
        if button == Qt.LeftButton:
            button_text = "left"
        elif button == Qt.RightButton:
            button_text = "right"
        elif button == Qt.MiddleButton:
            button_text = "middle"
        else:
            button_text = "unknown"

        return button_text
    
    def mousePressEvent(self, event):
        button = event.button()
        button_text = self.getButtonText(button)
        pos = event.pos()
        pos = self.translateMousePos([pos.x(), pos.y()])

        for input in input_buffer:
            if input.contains(*pos):
                input._onClick(*pos, button_text)

        for shape in shape_buffer:
            if shape._onClick and shape.contains(*pos):
                shape._onClick(*pos, button_text)

        self.button_store.add(button_text)
        for handler in on_mouse_pressed_handlers:
            if handler[1] == button_text:
                handler[0](*pos, button_text)

    def mouseReleaseEvent(self, event):
        button = event.button()
        button_text = self.getButtonText(button)
        pos = event.pos()
        pos = self.translateMousePos([pos.x(), pos.y()])
                
        for shape in shape_buffer:
            if shape._onRelease:
                shape._onRelease(*pos, button_text)
                
        self.button_store.remove(button_text)
        for handler in on_mouse_pressed_handlers:
            if handler[1] == button_text:
                pos = event.pos()
                handler[0](*self.translateMousePos([x, y]), button_text)

    def translateMousePos(self, pos):
        x = pos[0]
        y = pos[1]
        return [int(x/self.scale_factor), int(kstore.size[1] - y-self.scale_factor)]
    
    def mouseMoveEvent(self, event):
        pos = event.pos()
        pos = self.translateMousePos([pos.x(), pos.y()])
        self.mouse_pos = pos 

        for shape in shape_buffer:
            if not shape._onMouseEnter and not shape._onMouseExit:
                continue 

            contains = shape.contains(*pos)
            if contains and not shape._mouse_over:
                shape._mouse_over = True 
                if shape._onMouseEnter:
                    shape._onMouseEnter()
            elif not contains and shape._mouse_over:
                shape._mouse_over = False 
                if shape._onMouseExit:
                    shape._onMouseExit()

        for handler in on_mouse_moved_handlers:
            handler(*pos)

    def isButtonPressed(self, button):
        return button in self.button_store
    
    def getMousePos(self):
        return self.mouse_pos
# ==================================== PUBLIC INTERFACE ===========================================

# pip install PyQt5

def exception_hook(exctype, value, tb):
    tb_info = traceback.extract_tb(tb)
    for frame in tb_info:
        filename, lineno, funcname, text = frame
        lineno_str = f"{lineno}".ljust(10)
        funcname_str = f"{funcname}".ljust(20)
        print(f"line {lineno_str} {funcname_str} >>> {text}")    
    print(f"Exception: {exctype}, Value: {value}")
    sys.exit(1)

def createWindow():
    sys.excepthook = exception_hook

    kstore.app = QApplication(sys.argv)
    kstore.window = kMainWindow()
    kstore.window.show()
        
    kstore.main_timer = QTimer()
    kstore.main_timer.timeout.connect(lambda: action_queue.process())
    kstore.main_timer.timeout.connect(lambda: kstore.window.update())
    kstore.main_timer.start(kstore.dt)  # Process the queue every 100 ms

    kstore.elapsed_timer.start()

def _grid(value):
    kstore.show_grid = value 
    kstore.grid.clear()

def showGrid():
    action_queue.add(kSetter(_grid, True))

def hideGrid():
    action_queue.add(kSetter(_grid, False))

def maximizeWindow():
    screen = QDesktopWidget().availableGeometry()
    setWindowSize(screen.width(), screen.height())

def setWindowWidth(width):
    setWindowSize(width, getWindowHeight())

def getWindowWidth():
    return kstore.window.width() 

def setWindowHeight(height):
    setWindowSize(getWindowWidth(), height)

def getWindowHeight():
    return kstore.window.height() 

def setWindowSize(*size):
    size = toIntList(size)
    width = size[0]
    height = size[1]
    kstore.width = width
    kstore.height = height
    kstore.window.pixmap = QPixmap(kstore.width, kstore.height)
    kstore.window.setSize(width, height)
    kstore.grid.resize(width, height)
    kstore.window.center()

def run():
    kstore.elapsed_timer.start()
    sys.exit(kstore.app.exec_())

def drawEllipse(a, b):
    ellipse = kEllipse(a, b)
    ellipse.draw()
    return ellipse 

def drawCircle(radius):
    circle = kCircle(radius)
    circle.draw()
    return circle

def drawRect(width, height):
    rect = kRect(width, height)
    rect.draw()
    return rect

def drawLine(width, height):
    line = kLine(width, height)
    line.draw()
    return line

def drawVector(width, height):
    vector = kVector(width, height)
    vector.draw()
    return vector

def drawTriangle(length):
    triangle = kTriangle(length)
    triangle.draw()
    return triangle

def drawRoundedRect(width, height, radius=20):
    rect = kRoundedRect(width, height, radius)
    rect.draw()
    return rect

def drawArc(radius, angle):
    arc = kArc(radius, angle)
    arc.draw()
    return arc 

def drawPolygon(points):
    polygon = kPolygon(points)
    polygon.draw()
    return polygon

def setAnim(milliseconds):
    kstore.animation = milliseconds

def setDelay(milliseconds):
    kstore.delay = milliseconds

def setAnimDelay(milliseconds):
    setAnim(milliseconds)
    setDelay(milliseconds)

def getAnim(milliseconds):
    return kstore.animation

def delay(milliseconds):
    kstore.milliseconds += milliseconds

def setPos(*point):
    pos = toIntList(point)
    kstore.setPos(pos)

def getPos(x,y):
    return kstore.getPos() 

def setX(x):
    kstore.setX(int(x))

def getX():
    return kstore.getX()

def setY(y):
    kstore.setY(int(y))

def getY():
    return kstore.getY()

def move(*distance):
    delta = toIntList(distance)
    pos = kstore.getPos()
    pos[0] += int(delta[0])
    pos[1] += int(delta[1])

    kstore.setPos(pos)

def forward(distance):
    angle = kstore.rot*math.pi/180
    dx = math.cos(angle)*distance
    dy = math.sin(angle)*distance
    setPos(getX() + int(dx), getY() + int(dy))

def backward(distance):
    angle = kstore.rot*math.pi/180
    dx = math.cos(angle)*distance
    dy = math.sin(angle)*distance
    setPos(getX() - int(dx), getY() - int(dy))

def left(angle):
    rotate(angle)

def right(angle):
    rotate(-angle)

def rotate(angle):
    angle = int(angle)
    old_angle = kstore.getRot()
    new_angle = old_angle + angle 
    kstore.setRot(new_angle)

def setRot(angle):
    """
        - set rotation angle in degrees (counterclockwise)
        - 0 degrees points to the right

        usage example:
        - setRot(60)
    """

    kstore.setRot(int(angle))

def getRot():
    kstore.getRot()

def setLine(value):
    kstore.line = value 

def setFill(value):
    kstore.fill = value 

def setColor(*rgb):
    kstore.setColor(*rgb)

def getColor():
    return kstore.getColor()

def setFillColor(*rgb):
    kstore.setFillColor(*rgb)

def getFillColor():
    return kstore.getFillColor()

def setLineColor(*rgb):
    kstore.setLineColor(*rgb)

def getLineColor():
    return kstore.getLineColor()

def setBackgroundColor(*rgba):
    kstore.backgroundColor = toColor(rgba)

def getBackgroundColor():
    return kstore.backgroundColor

def setLineWidth(value):
    kstore.lineWidth = value 

def saveAsPng(filename):
    action_queue.add(kSetter(kstore.window.saveAsPng, filename))

def onTick(tick_function, milliseconds):
    action_queue.add(kLoop(tick_function, milliseconds))

on_key_pressed_handlers = []
on_key_released_handlers = []
on_mouse_pressed_handlers = []
onMouseReleased_handlers = []
on_mouse_moved_handlers = []

def onKeyPressed(handler, key=None):
    def submit(the_key):
        if key != None and the_key == key:                  
            handler()
        elif key == None:
            handler(the_key)

    on_key_pressed_handlers.append((submit, key))

def onKeyReleased(handler, key=None):
    def submit(the_key):
        if key != None and the_key == key:                  
            handler()
        elif key == None:
            handler(the_key)

    on_key_released_handlers.append((submit, key))

def onMousePressedEvent(handler, button):
    def submit(x, y, the_button):
        if button != None and the_button == button:                  
            handler(x, y)
        elif button == None:
            handler(x, y, the_button)

    on_mouse_pressed_handlers.append((submit, button))

def onMouseReleasedEvent(handler, button):
    def submit(x, y, the_button):
        if button != None and the_button == button:                  
            handler(x,y)
        elif button == None:
            handler(x, y, the_button)
            
    onMouseReleased_handlers.append((submit, button))

def onMouseMovedEvent(handler):
    on_mouse_moved_handlers.append(handler)


def isKeyPressed(key):
    return kstore.window.isKeyPressed(key)

def isMousePressed(button):
    return kstore.window.isButtonPressed(button)

def getMousePos():
    return kstore.window.getMousePos()

def getMouseX():
    return kstore.window.getMousePos()[0]

def getMouseY():
    return kstore.window.getMousePos()[1]

def drawInput(handler=None, label=""):
    input = kInput(handler, label)
    input.draw()
    return input 

def drawLabel(text):
    label = kLabel(text)
    label.draw()
    return label 

def drawText(text):
    label = kLabel(text)
    label._fill = False 
    label.fill = False 
    label._line = False 
    label.line = False 
    label._width = kstore.size[0] 
    label.width = kstore.size[0]
    label._overflow = "clip"
    label.overflow = "clip"
    label._alignY = "bottom"
    label.alignY = "bottom"

    label.draw()
    return label 

def drawButton(handler, text=""):
    button = kButton(handler, text)
    button.draw()
    return button

def setFontSize(size):
    kstore.setFontsize(size)

def getFontSize():
    return kstore.getFontSize()

def setFontColor(*rgb):
    kstore.setFontColor(rgb)

def getFontColor():
    return kstore.getFontColor()

# def beginRecording():
#     action_queue.add(kSetter(kstore.window.setRecord, True))

# def endRecording():
#     action_queue.add(kSetter(kstore.window.setRecord, False))

# def saveAsMp4(filename, fps):
#     action_queue.add(kSetter(kstore.window.saveAsMp4, filename, fps))

# def saveAsGif(filename, fps):
#     action_queue.add(kSetter(kstore.window.saveAsGif, filename, fps))

def setAnimationType(type):
    global INTERPOLATION_FUNCTION

    if type == "linear":
        INTERPOLATION_FUNCTION = linear
    elif type == "smooth":
        INTERPOLATION_FUNCTION = smooth_interpolation
    else:
        raise ValueError("unknown inteprolation function")

def show(shape):
    for the_shape in shape_buffer:
        if shape == the_shape:
            the_shape.show()

def hide(shape):
    for the_shape in shape_buffer:
        if shape == the_shape:
            the_shape.hide()

def showCursor():
    kstore.cursor.show()

def hideCursor():
    kstore.cursor.hide()

def _clear():
    i = 0
    while i < len(shape_buffer):
        shape = shape_buffer[i]
        if shape.ready:
            shape_buffer.pop(i)
        else:
            i = i + 1

    kstore.window.update()

def clear():
    action_queue.add(kAction(_clear))
# ==================================== TEST CODE ===========================================

if __name__ == "__main__":
    createWindow()

    drawText("hello world!")

    setPos(500,300)
    
    def handler(text):
        print(text, "emit")
    i = drawInput(handler, "abc "*3)
    i.setOverflow("wrap")
    i.setAlignX("right")
    run()

    