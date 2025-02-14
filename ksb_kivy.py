# pip install kivy
# pip install kivy_garden.graph

import os
import sys 
import random 
import pip
if __name__ != "__main__":
    os.environ["KCFG_KIVY_LOG_LEVEL"] = "warning"

import platform
osystem = platform.system()

if osystem == "Windows":
    os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

def _install(name, version):
    print("x"*100)
    print("Einmalige Installation von " + name)
    print("x"*100)

    pip.main(['install', name+version])

    print("✔"*100)
    print(name + " erfolgreich installiert")
    print("✔"*100)
             
try:
    import kivy
    kivy.require('2.3.0') # replace with your current kivy version!
except ImportError:
    _install("kivy[base]", "==2.3.0") # alternatively: base, sdl2, angle
    import kivy
    kivy.require('2.3.0')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.slider import Slider
from kivy.graphics import Canvas, Color, Rectangle, Ellipse, Triangle, Line,Bezier, Translate, Rotate, PushMatrix, PopMatrix, Mesh
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.config import Config
from kivy.metrics import dp
from kivy.core.window import Keyboard
from kivy.graphics.texture import Texture
from kivy.graphics import Callback
import shutil 

try:
    from PIL import Image 
except ImportError:
    _install("Pillow", "==9.5.0")
    from PIL import Image 

try:
    from kivy_garden.graph import Graph, MeshLinePlot, LinePlot
except ImportError:
    _install("kivy_garden.graph", "==0.4.0")
    from kivy_garden.graph import Graph, MeshLinePlot, LinePlot

import time 
import math 

__all__ = ["getMousePos", "getMouseX", "getMouseY", "createWindow", "setWindowSize", "setWindowHeight", "setWindowWidth", "showGrid", "getWindowSize", "getWindowWidth", "getWindowHeight", "addEvent", "addLoop", "drawInput", "drawButton", "drawSwitch", "drawLabel", "drawSlider", "setLineWidth", "setLineColor", "setFillColor", "setColor", "setFontSize", "setFontColor", "drawLine", "drawLineTo", "remove", "clear", "drawRect", "drawCircle", "drawEllipse", "drawArc", "drawList", "run", "setPos", "getPos", "setX", "setY", "getX", "getY", "centerPos", "move", "onMouseMoved", "onMousePressed", "onMouseReleased", "onKeyPressed", "onKeyReleased", "isKeyPressed", "isMousePressed", "hasMouseMoved", "drawGraph", "drawPoly", "makeTurtle", "record", "save", "getSample", "setScale", "getScale"]

Config.set('graphics', 'fullscreen', 'auto')
Config.set('graphics', 'position', 'auto')
Config.set('graphics', 'multisamples', '0')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

old_dp = dp

scale_factor = 0.8

def dp(value):
    return old_dp(value)*scale_factor

def dpp(point):
    return (dp(point[0]), dp(point[1]))

def setScale(value):
    """
        - Skalierungsfaktor (default 0.8)
    """
    global scale_factor
    scale_factor = value 

def getScale():
    """
        - Skalierungsfaktor (default 0.8)
    """
    return scale_factor

class kTurtle:
    def __init__(self):
        self._x = getWindowWidth()//2
        self._y = getWindowHeight()//2
        self._angle = 0
        self._speed = 100
        self._line_width = 1
        self._line_color = kstore.line_color
        self._fill_color = kstore.fill_color
        self._fill = False
        self._pause = False
        self._queue = []
        # initial draw of turtle object
        self._shapes = []
        self._loop = addLoop(self._update, 0.01)
        self._base_speed = 5*800
        self._base_turn = 6*360
        self._fill_store = []
        self._poly_store = []
        self._turtle = drawPoly(self._getHead(), True, True)
        self._turtle.setLineColor(self._line_color)
        self._turtle.setFillColor(self._fill_color)
        self._pendown = True
        self._index = 0

    def _getHead(self):
        x = self._x
        y = self._y
        d = 5*self._line_width+2
        a = self._angle/180*math.pi
        c = math.cos(a)
        s = math.sin(a)
        p1 = (d, 0)
        p2 = (0, +0.4*d)
        p3 = (0, -0.4*d)

        def rot(point):
            px = point[0]
            py = point[1]
            return (x+(px*c - py*s), y+(py*c+px*s))
        
        p1 = rot(p1)
        p2 = rot(p2)
        p3 = rot(p3)

        return (p1, p2, p3)
    
    def goTo(self, x,y):
        self._dispatch("goto", (x,y))

    def _goTo(self, point):
        x = point[0]
        y = point[1]

        dx = x - self._x 
        dy = y - self._y 

        if abs(dx) < 1 and abs(dy) < 1:
            return

        if abs(dx) < 1 and y > self._y:
            target_angle = 90
        elif abs(dx) < 1:
            target_angle = -90
        elif x > self._x:
            target_angle = math.atan(dy/dx)/math.pi*180
        else:
            target_angle = math.atan(dy/dx)/math.pi*180+180

        distance = (dx**2 + dy**2)**0.5

        if distance > 0:
            self._dispatch("forward", distance, True)

        delta_angle = target_angle - self._angle 
        if delta_angle > 0:
            self._dispatch("left", delta_angle, True)
        elif delta_angle < 0:
            self._dispatch("right", -delta_angle, True)  
        
    def _setSpeed(self, speed):
        if speed > 255:
            speed = 255
        elif speed < 0:
            speed = 999999999
        self._speed = speed

    def setSpeed(self, speed):
        self._dispatch("speed", speed)

    def _dispatch(self, key, value, first = False):
        if first:
            self._queue.insert(0, [key, value, self._index, True])
        else:
            self._queue.append([key, value, self._index, True])
        self._index += 1

    def forward(self, distance):
        self._dispatch("forward", distance)

    def backward(self, distance):
        self._dispatch("backward", distance)

    def left(self, angle):
        self._dispatch("left", angle)

    def right(self, angle):
        self._dispatch("right", angle)

    def setLineColor(self, r:int|list|str,g:int=None,b:int=None,a:int=None):
        self._dispatch("line_color", sanitizeColor(r,g,b,a))

    def setLineWidth(self, line_width):
        self._dispatch("line_width", line_width)

    def setFillColor(self, r:int|list|str,g:int=None,b:int=None,a:int=None):
        self._dispatch("fill_color", sanitizeColor(r,g,b,a))

    def setColor(self, r:int|list|str,g:int=None,b:int=None,a:int=None):
        self.setLineColor(r,g,b,a)
        self.setFillColor(r,g,b,a)

    def beginFill(self):
        self._dispatch("fill", True)

    def endFill(self):
        self._dispatch("fill", False)
    
    def setPause(self, value):
        self._pause = value 

    def penUp(self):
        self._dispatch("penup", True)

    def penDown(self):
        self._dispatch("pendown", False)

    def delay(self, value):
        self._dispatch("delay", value)
    
    def stop(self):
        self._queue = []

    def clear(self):
        self._dispatch("clear", True)

    def reset(self):
        self._queue = []
        self.clear()
        self._turtle.remove()
        self.__init__()

    def _drawTurtle(self):
        self._turtle.setPoints(self._getHead())
        self._turtle.setFillColor(self._line_color)

    def _update(self, dt):
        def newLine():
            line = drawPoly([(self._x, self._y)], False, False)
            line.setLineWidth(self._line_width)
            line.setLineColor(self._line_color)
            self._shapes.append(line)
            return line 
        
        def moveLine(forward, value):
            line = self._shapes[-1]
            
            dx = self._speed/255*dt*self._base_speed*math.cos(self._angle/180*math.pi)
            dy = self._speed/255*dt*self._base_speed*math.sin(self._angle/180*math.pi)

            d = (dx*dx + dy*dy)**0.5
            dnew = min(value, d)

            self._x += forward*dx*dnew/d
            self._y += forward*dy*dnew/d
            if self._fill and self._pendown:
                self._fill_store.append((self._x, self._y))
            if self._pendown:
                line.addPoint(self._x, self._y)

            self._drawTurtle()
            return dnew
        
        def turnLine(left, value):
            d = self._base_turn*self._speed/255*dt
            d = min(d, value)
            self._angle += left*d
            self._drawTurtle()
            return d
                
        if len(self._queue) > 0 and not self._pause:
            action, value, index, first = self._queue[0]
            if action == "forward":
                if first:
                    newLine()

                d = moveLine(1, value)
                value = value - d
                if value == 0:
                    self._queue.pop(0)
                else:
                    self._queue[0][1] = value
                    self._queue[0][3] = False
            elif action == "backward":
                if first:
                    newLine()

                d = moveLine(-1, value)
                value = value - d
                if value == 0:
                    self._queue.pop(0)
                else:
                    self._queue[0][1] = value
                    self._queue[0][3] = False
            elif action == "left":
                d = turnLine(1, value)
                value = value - d
                if value == 0:
                    self._queue.pop(0)
                else:
                    self._queue[0][1] = value
                    self._queue[0][3] = False
            elif action == "right":
                d = turnLine(-1, value)
                value = value - d
                if value == 0:
                    self._queue.pop(0)
                else:
                    self._queue[0][1] = value
                    self._queue[0][3] = False
            elif action == "line_color":
                self._line_color = value
                newLine()
                self._turtle.setLineColor(self._line_color)
                self._queue.pop(0)
            elif action == "line_width":
                self._line_width = value
                newLine()
                self._queue.pop(0)
            elif action == "fill_color":
                self._fill_color = value
                self._queue.pop(0)
            elif action == "fill":
                if value == True:
                    self._fill = True
                elif self._fill:
                    poly = drawPoly(self._fill_store, True,True)
                    poly.setFillColor(self._fill_color)
                    self._fill_store = []
                    self._poly_store.append(poly)
                    self._drawTurtle()
                    self._turtle = drawPoly(self._getHead(), True, True)
                    self._turtle.setLineColor(self._line_color)
                    self._fill=False
                self._queue.pop(0)
            elif action == "delay":
                value -= dt
                if value <= 0:
                    self._queue.pop(0)
                else:
                    self._queue[0][1] = value
                    self._queue[0][3] = False
            elif action == "clear":
                for shape in self._shapes:
                    shape.remove()
                self._shapes = []

                for poly in self._poly_store:
                    poly.remove()
                self._poly_store = []
                self._queue.pop(0)
            elif action == "speed":
                self._setSpeed(value)
                self._queue.pop(0)
            elif action == "penup":
                newLine()
                self._pendown = False
                self._fill = False
                self._fill_store = []
                self._queue.pop(0)
            elif action == "pendown":
                self._pendown = True
                self._queue.pop(0)
            elif action == "goto":
                self._queue.pop(0)
                self._goTo(value)

class Kstore:
    def __init__(self):
        self.root = None
        self.canvas = None
        self.size = [800,800]
        self.top = Window.top
        self.left = Window.left 
        self.pos = [400,400]
        self.angle = 0
        self.fill_color = [100, 100, 100, 255]
        self.line_color = [200,200,200,255]
        self.line_width = 1
        self.font_size = 18
        self.font_color = [200,200,200,255]
        self.font_name = 'DejaVuSans.ttf'
        self.grid = None    
        self.stack = []
        self.ready = False
        self.save = False

    def copyFirstToSecond(self, one, the_other):
        the_other.size = one.size
        the_other.top = one.top
        the_other.left = one.left 
        the_other.pos = one.pos
        the_other.fill_color = one.fill_color
        the_other.line_color = one.line_color
        the_other.line_width = one.line_width
        the_other.font_size = one.font_size
        the_other.font_color = one.font_color
        the_other.font_name = one.font_name
        the_other.grid = one.grid      
        the_other.save= one.save
        the_other.ready = one.ready

    def setPos(self,x:int|list,y:int=None):
        self.pos = sanitizeXY(x,y)

    def getPos(self):
        return self.pos

    def push(self):
        other = Kstore()
        self.copyFirstToSecond(self, other)
        self.stack.append(other)

    def pop(self):
        if len(self.stack) > 0:
            other = self.stack[-1]
            self.copyFirstToSecond(other, self)
            del self.stack[-1]

kstore = Kstore()

class kPlot:
    def __init__(self, kgraph, color):
        self._line_color = color
        self._points = []
        self._line_width = kstore.line_width
        self._kgraph = kgraph

        plot = LinePlot(color=translateColor(self._line_color), line_width = dp(self._line_width))
        plot.points = self._points
        self._plot = plot
        self._update()

    def _update(self):
        data_points = self._points
        sorted_data_points = sorted(data_points, key=lambda x: x[0])
        self._plot.points = sorted_data_points

        self._kgraph._update()

    def setPoints(self, points):
        self._points = points 
        self._update()

    def addPoints(self, points):
        self._points.extend(points)
        self._update()

    def addPoint(self, point):
        self._points.append(point)
        self._update()

    def getPoints(self):
        return self._points

    def setLineColor(self, r:int|list|str,g:int=None,b:int=None,a:int=None):
        self._line_color = sanitizeColor(r,g,b,a)
        self._plot._gcolor = translateColor(self._line_color)
        self._plot.color = translateColor(self._line_color)
        self._plot._color = translateColor(self._line_color)

    def getLineColor(self):
        return self._line_color
    
    def setLineWidth(self, width):
        self._line_width = width 
        self._plot.line_width = dp(self._line_width)

    def getLineWidth(self):
        return self._line_width
    
    def setLineAlpha(self, a):
        self._line_color = sanitizeColor(self._line_color)
        self._line_color[3] = a
        self._plot.color = translateColor(self._line_color)
    
    def getLineAlpha(self):
        return self._line_color[3]

class kGraph:
    def __init__(self, width=800, height=800):
        if kstore.root == None:
            raise Exception("createWindow() first")
        
        self._root = kstore.root
        self._pos = kstore.getPos()
        self._fill_color = kstore.fill_color
        self._line_color = kstore.line_color
        self._line_width = kstore.line_width
        self._width = width
        self._height = height
        self._xmin = None 
        self._xmax = None 
        self._ymin = None 
        self._ymax = None 
        self._auto = True
        self._xlabel = 'x'
        self._ylabel = 'y' 
        self._padding = 5
        self._plots = []
        
        graph = Graph(xlabel=self._xlabel, ylabel=self._ylabel, y_grid_label=True, x_grid_label=True, padding=dp(self._padding),
        x_grid=True, y_grid=True, width=dp(width), height=dp(height), pos=dpp(self._pos))

        self._graph = graph
        self.addPlot(kstore.line_color)

    def addPlot(self, r:int|list|str=kstore.line_color,g:int=None,b:int=None,a:int=None):
        color = sanitizeColor(r,g,b,a)
        plot = kPlot(self, color)
        self._plots.append(plot)
        self._graph.add_plot(plot._plot)
        return plot

    def setAuto(self, auto):
        self._auto = auto 

    def _draw(self):
        self._root.add_widget(self._graph)

    def _update(self):
        if self._auto:
            self.setRangeX(self._xmin, self._xmax)
            self.setRangeY(self._ymin, self._ymax)
        self._graph._redraw_all()

    # def _sort(self):
    #     data_points = self._plot._points
    #     sorted_data_points = sorted(data_points, key=lambda x: x[0])
    #     self._plot._points = sorted_data_points

    def setPoints(self, points):
        self._plots[0].setPoints(points) 
        self._update()

    def addPoints(self, points):
        self._plots[0].addPoints(points)
        self._update()

    def addPoint(self, point):
        self._plots[0].addPoint(point)
        self._update()

    def getPoints(self):
        return self._plots[0].getPoints()

    def setPos(self, x:int|list, y:int=None):
        self._pos = sanitizeXY(x,y)
        self._graph.pos = dpp(x,y)
    
    def getPos(self):
        return self._pos
    
    def setRangeX(self, minimum, maximum):
        self._xmin = minimum
        self._xmax = maximum

        points = []
        for plot in self._plots:
            points.extend(plot.getPoints())
        x = list([x for (x,y) in points])

        if self._xmin == None:
            if len(x) > 0:
                minimum = min(x)*1.2
            else:
                minimum = 0
        else:
            minimum = self._xmin 
        
        if self._xmax == None:
            if len(x) > 0:
                maximum = max(x)*1.2
            else:
                maximum = 100
        else:
            maximum = self._xmax 
       
        if maximum == minimum:
            maximum = minimum + 1

        x_ticks_major = abs(maximum-minimum)/5
        x_ticks_minor = 5

        self._graph.xmin = minimum 
        self._graph.xmax = maximum
        self._graph.x_ticks_major = x_ticks_major
        self._graph.x_ticks_minor = x_ticks_minor
    
    def getRangeX(self):
        return (self._xmin, self._xmax)
    
    def setMinX(self, minimum):
        self._xmin = minimum
        self.setRangeX(self._xmin, self._xmax)

    def getMinX(self):
        return self._xmin
    
    def setMaxX(self, maximum):
        self._xmax = maximum
        self.setRangeX(self._xmin, self._xmax)

    def getMaxX(self):
        return self._xmax 
    
    def setRangeY(self, minimum, maximum):
        self._ymin = minimum
        self._ymax = maximum

        points = []
        for plot in self._plots:
            points.extend(plot.getPoints())

        y = list([y for (x,y) in points])

        if self._ymin == None:
            if len(y) > 0:
                minimum = min(y)*1.2
            else:
                minimum = 0
        else:
            minimum = self._ymin 
        
        if self._ymax == None:
            if len(y) > 0:
                maximum = max(y)*1.2
            else:
                maximum = 100
        else:
            maximum = self._ymax 

        if maximum == minimum:
            maximum = minimum + 1
        
        y_ticks_major = abs(maximum-minimum)/5
        y_ticks_minor = 5

        self._graph.ymin = minimum 
        self._graph.ymax = maximum
        self._graph.y_ticks_major = y_ticks_major
        self._graph.y_ticks_minor = y_ticks_minor

    def getRangeY(self):
        return (self._ymin, self._ymax)
    
    def setMinY(self, minimum):
        self._ymin = minimum 
        self.setRangeY(self._ymin, self._ymax)

    def getMinY(self):
        return self._ymin 
    
    def setMaxY(self, maximum):
        self._ymax = maximum 
        self.setRangeY(self._ymin, self._ymax)
    
    def getMaxY(self):
        return self._ymax 
    
    def setLabelX(self, label):
        self._xlabel = label
        self._graph.xlabel = label

    def getLabelX(self):
        return self._xlabel 
    
    def setLabelY(self, label):
        self._ylabel = label 
        self._graph.ylabel = label 

    def getLabelY(self):
        return self._ylabel 

    def setWidth(self, width):
        self._width = width
        self._graph.width = dp(self._width)
        # self.background.setWidth(width)

    def getWidth(self):
        return self._width 
    
    def setHeight(self, height):
        self._height = height
        self._graph.height = dp(self._height)
        # self.background.setHeight(height)

    def getHeight(self):
        return self._height 
    
    def setSize(self, width, height):
        self.setWidth(width)
        self.setHeight(height)
        # self.background.setSize(width, height)

    def getSize(self):
        return (self._width, self._height)
    
    # def setFillColor(self, r:int|list,g:int=None,b:int=None,a:int=None):
    #     self.fill_color = sanitizeColor(r,g,b,a)
        # self.background.setFillColor(r,g,b,a)

    # def getFillColor(self):
    #     return self.fill_color
        # return self.background.getFillColor()
    
    def setLineColor(self, r:int|list|str,g:int=None,b:int=None,a:int=None):
        self._plots[0].setLineColor(r,g,b,a)
        
    def getLineColor(self):
        return self._plots[0].getLineColor()
    
    def setLineAlpha(self, a):
        self._plots[0].setLineAlpha(a)

    def getLineAlpha(self):
        return self._plots[0].getLineAlpha()
    
    def setLineWidth(self, line_width):
        self._plots[0].setLineWidth(line_width)

    def getLineWidth(self):
        return self._plots[0].getLineWidth()
    
    def setPadding(self, padding):
        self._padding = padding
        self._graph.padding = dp(padding)
    
class kShape:
    def __init__(self):
        if kstore.root == None:
            raise Exception("createWindow() first")

        self._canvas = kstore.root.canvas
        self._pos = kstore.getPos()
        self._angle = kstore.angle
        self._rot = Rotate(angle = self._angle, origin=self._pos)
        self._size = [0,0]
        self._fill_color = kstore.fill_color
        self._line_color = kstore.line_color
        self._line_width = kstore.line_width
        self._alive = True
        self._fill = False
        self._shape = None
        self._color = None 
        self._hidden = False

    def setPos(self, x:int|list, y:int=None):
        self._pos = sanitizeXY(x,y)
        self._shape.pos = dpp(self._pos)

    def getPos(self):
        return (self.getX(), self.getY()) 
    
    def setRot(self, angle):
        self._angle = angle
        self.rot.angle = Rotate(angle=angle)

    def getRot(self):
        return self._angle 
    
    def setX(self, x):
        self.setPos(x, self._pos[1])
    
    def getX(self):
        return self._pos[0]
    
    def setY(self, y):
        self.setPos(self._pos[0], y)
    
    def getY(self):
        return self._pos[1]
    
    def setColor(self, r:int|list|str, g:int=None, b:int=None, a:int=None):
        self.setFillColor(r,g,b,a)
        self.setLineColor(r,g,b,a)

    def setFillColor(self, r:int|list|str,g:int=None,b:int=None,a:int=None):
        self._fill_color = sanitizeColor(r,g,b,a)
        if self._fill:
            self._color.rgba = translateColor(self._fill_color)
        
    def getFillColor(self):
        return self._fill_color
    
    def getColor(self):
        if self._fill:
            return self._fill_color
        else:
            return self._line_color
        
    def setLineColor(self, r:int|list|str,g:int=None,b:int=None,a:int=None):
        self._line_color = sanitizeColor(r,g,b,a)
        if not self._fill:
            self._color.rgba = translateColor(self._line_color)

    def getLineColor(self):
        return self._line_color
    
    def setLineAlpha(self, a):
        self._line_color = sanitizeColor(self._line_color)
        self._line_color[3] = a
        if not self._fill:
            self._color.rgba = translateColor(self._line_color)
    
    def getLineAlpha(self):
        return self._line_color[3]
    
    def setFillAlpha(self, a):
        self._fill_color = sanitizeColor(self._fill_color)
        self._fill_color[3] = a
        self._fill_color = translateColor(self._fill_color)
    
    def getFillAlpha(self):
        return self._fill_color[3]

    def setAlpha(self, a):
        self.setLineAlpha(a)
        self.setFillAlpha(a)
        
    def setLineWidth(self, line_width):
        self._line_width = line_width
        if not self._fill:
            self._shape.width = max(0.5,self._line_width)

    def getLineWidth(self):
        return self._line_width
    
    def setFill(self, fill):
        if self._fill == fill:
            return
        
        self._fill = fill
        self._canvas.remove(self._shape)
        self._draw()

    def getFill(self):
        return self._fill 
    
    def setWidth(self, width):
        self._size[0] = width

    def getWidth(self):
        return self._size[0]
    
    def setHeight(self, height):
        self._size[1] = height

    def getHeight(self):
        return self._size[1]
        
    def setSize(self, width:int|list, height:int=None):
        self._size = sanitizeXY(width, height)
    
    def getSize(self):
        return self._size
    
    def remove(self):
        if self._shape == None:
            return 
        
        self._alive = False

        try:
            self._canvas.before.remove(self._shape)
        except Exception as e:
            pass

        try:
            self._canvas.remove(self._shape)
        except Exception as e:
            pass

    def isDead(self):
        return not self._alive 
    
    def isAlive(self):
        return self._alive
    
    def hide(self):
        self._hidden = True
        self._canvas.remove(self._shape)
    
    def show(self):
        if self._hidden and self._alive:
            self._hidden = False
            with self._canvas:
                if self._fill:
                    self._color = Color(*translateColor(self._fill_color), mode="rgba")
                else:
                    self._color = Color(*translateColor(self._line_color), mode="rgba")

                self._canvas.add(self._shape)

class kLine(kShape):
    def __init__(self, x:int|list, y:int=None, background=False):
        super().__init__()
        self._end_point = sanitizeXY(x,y)
        self._width = self._pos[0] - self._end_point[0]
        self._height = self._pos[1] - self._end_point[1]
        self._background = background
        self._fill = False 

    def setPos(self, x:int|list, y:int=None):
        new_pos = sanitizeXY(x,y)
        self._end_point = (self._end_point[0] - self._pos[0] + new_pos[0], self._end_point[1] - self._pos[1] + new_pos[1])
        self._pos = new_pos
        self._update()

    def setEndPoint(self, x:int|list, y:int=None):        
        self._end_point = sanitizeXY(x,y)
        self._width = self._end_point[0] - self._pos[0]
        self._height = self._end_point[1] - self._pos[1]
        self._update()

    def getEndPoint(self):
        return self._end_point
    
    def _update(self):
        if not self._alive:
            return 
        self._shape.points = (*dpp(self._pos), *dpp(self._end_point))      

    def _draw(self):
        self.remove()
        if not self._alive:
            return

        if self._background:
            with self._canvas.before:
                self._color = Color(*translateColor(self._line_color), mode="rgba")
                begin = dpp(self._pos)
                end = dpp(self._end_point)
                self._shape = Line(width=max(0.5,dp(self._line_width)), points=(*begin, *end)) 
        else:
            with self._canvas:
                self._color = Color(*translateColor(self._line_color), mode="rgba")
                begin = dpp(self._pos)
                end = dpp(self._end_point)
                self._shape = Line(width=max(0.5,dp(self._line_width)), points=(*begin, *end)) 
    

    def setWidth(self, width):
        self.setSize(width, self._size[1])

    def setHeight(self, height):
        self.setSize(self._size[0], height)

    def setSize(self, width:int|list, height:int=None):
        self._size = sanitizeXY(width, height)
        self._end_point = [self._pos[0] + self._size[0], self._pos[1] + self._size[1]]
        self._update()

class kRect(kShape):
    def __init__(self, width:int|list, height:int=None, fill=False):
        super().__init__()
        self._size = sanitizeXY(width, height)
        self._fill = fill
        self._end_point = (self._pos[0] + self._size[0], self._pos[1] + self._size[1])

    def setPos(self, x:int|list, y:int=None):
        new_pos = sanitizeXY(x,y)
        self._end_point = (self._end_point[0] - self._pos[0] + new_pos[0], self._end_point[1] - self._pos[1] + new_pos[1])
        self._pos = new_pos
        self._update()

    def setEndPoint(self, x:int|list, y:int=None):
        self._end_point = sanitizeXY(x,y)
        self._size = [self._end_point[0] - self._pos[0], self._end_point[1] - self._pos[1]]
        self._update()

    def getEndPoint(self):
        return self._end_point
    
    def _update(self):
        if self._fill:
            self._shape.pos = dpp(self._pos)
            self._shape.size = dpp(self._size)
        else:
            self._shape.rectangle = (*dpp(self._pos), *dpp(self._size))      

    def _draw(self):
        self.remove()

        if not self._alive:
            return
        
        with self._canvas:
            x = self._pos[0]
            y = self._pos[1]
            width = self._size[0]
            height = self._size[1]

            if not self._fill:
                x += self._line_width
                y += self._line_width 

                width -= 2*self._line_width 
                height -= 2*self._line_width

            if self._fill:
                self._color = Color(*translateColor(self._fill_color), mode="rgba")
                self._shape = Rectangle(pos=dpp((x,y)), size=dpp((width, height)))
            else:
                self._color = Color(*translateColor(self._line_color), mode="rgba")
                self._shape = Line(width=max(1,dp(self._line_width)), rectangle=(dp(x),dp(y),dp(width),dp(height)))
                    
    def setWidth(self, width):
        self.setSize(width, self._size[1])

    def setHeight(self, height):
        self.setSize(self._size[0], height)

    def setSize(self, width:int|list, height:int=None):
        self._size = sanitizeXY(width,height)
        self._end_point = [self._pos[0] + self._size[0], self._pos[1] + self._size[1]]
        self._update()

class kEllipse(kShape):
    def __init__(self, a, b, start=0, end=360, fill=False):
        super().__init__()
        self._a = a
        width = 2*self._a
        self._b = b
        height = 2*self._b
        self._size = [width, height]
        self._start = start
        self._end = end
        self._fill = fill

    def setPos(self, x:int|list, y:int=None):
        new_pos = sanitizeXY(x,y)
        self._pos = new_pos
        self._update()
    
    def _update(self):
        x = self._pos[0] - self._a
        y = self._pos[1] - self._b

        if self._fill:
            self._shape.pos = dpp((x,y))
            self._shape.size = dpp(self._size)
        else:
            self._shape.ellipse = (dp(x), dp(y), dp(self._size[0]), dp(self._size[1]))      

    
    def _draw(self):
        self.remove()

        # if not self._alive:
        #     return
        
        with self._canvas:
            x = self._pos[0] - self._a
            y = self._pos[1] - self._b

            angle_max = 90-self._start+360
            angle_min = 90-self._end+360
            
            if self._fill:
                self._color = Color(*translateColor(self._fill_color), mode="rgba")
                self._shape = Ellipse(pos=dpp((x,y)), size=dpp(self._size), angle_start=angle_min, angle_end=angle_max)
            else:  
                self._color = Color(*translateColor(self._line_color), mode="rgba")
                self._shape = Line(width=max(1,dp(self._line_width)), ellipse=(dp(x),dp(y),dp(self._size[0]),dp(self._size[1]), angle_min, angle_max)) 
        
    def setWidth(self, width):
        self._size[0] = width
        self._a = width/2
        self._update()

    def setHeight(self, height):
        self._size[1] = height
        self._b = height/2
        self._update()

    def setA(self, a):
        self._a = a
        self._size[0] = 2*self._a
        self._update()

    def getA(self):
        return self._a
    
    def setB(self, b):
        self._b = b
        self._size[1] = 2*self._b
        self._update()

    def getB(self):
        return self._b 
    
    def setRadius(self, r):
        self._a = r
        self._b = self._a
        self._size = [2*self._a, 2*self._b]
        self._update()

    def setSize(self, width:int|list, height:int=None):
        self._size = sanitizeXY(width, height)
        self._a = self._size[0]/2
        self._b = self._size[1]/2
        self._update()

    def getRadius(self):
        return (self._a + self._b)/2
    
    def setStartAngle(self, start):
        self._start = start 
        self._shape.angle_start = 90-self._start+360

    def getStartAngle(self):
        return self._start
    
    def setEndAngle(self, end):
        self._end = end 
        self._shape.angle_end = 90-self._end+360

    def getEndAngle(self):
        return self._end

class kPoly(kShape):
    def __init__(self, points:list, fill:bool=False, cyclic:bool=True):
        super().__init__()
        self._fill = fill
        self._cyclic = cyclic
        self._points = list(points)
        self._convertToVertices()

    def _convertToVertices(self):
        if len(self._points) == 0:
            return

        xs = list(x for (x,y) in self._points)
        ys = list(y for (x,y) in self._points)

        xmin = min(xs)
        xmax = max(xs)
        dx = xmax - xmin
        ymin = min(ys)
        ymax = max(ys)
        dy = ymax - ymin 

        def getUV(x,y):
            if dx == 0:
                u = 1
            else:
                u = (x-xmin)/dx
            if dy == 0:
                v = 1
            else:
                v = (y-ymin)/dy
            return (u,v)

        uv = tuple((dp(x),dp(y), *getUV(x,y)) for (x,y) in self._points)
        if self._fill:
            self._vertices =tuple(item for tup in uv for item in tup)
        else:
            self._vertices = list(dp(item) for tup in self._points for item in tup)
            if self._cyclic:
                self._vertices.append(dp(self._points[0][0]))
                self._vertices.append(dp(self._points[0][1]))

        self._indices = tuple(i for i in range(len(self._points)))

    def move(self, x,y):
        self._points = tuple((p1+x, p2+y) for (p1,p2) in self._points)
        self._convertToVertices()
        self._redraw()

    def _draw(self):
        self.remove()

        if not self._alive:
            return
        
        if self._fill: 
            with self._canvas:
                mode = "triangle_fan" 
                self._color = Color(*translateColor(self._fill_color))
                self._shape = Mesh(vertices=self._vertices,indices=self._indices, mode=mode) 
        else:
            with self._canvas:
                self._color = Color(*translateColor(self._line_color))
                self._shape = Line(points=self._vertices, width = max(1,dp(self._line_width)))

    def _redraw(self):
        if self._fill:
            self._shape.vertices = self._vertices 
        else:
            self._shape.points = self._vertices

    def setFill(self, fill):
        self._fill = fill
        self._convertToVertices()
        self.remove()
        self._draw()

    def addPoint(self, x, y):
        self._points.append((x,y))
        self._convertToVertices()
        self._redraw()

    def setPoints(self, points):
        self._points = points
        self._convertToVertices()
        self._redraw()

class kUIElement:
    def __init__(self):
        if kstore.root == None:
            raise Exception("createWindow() first")
        self._element = None
        self._size = [200,50]
        self._pos = kstore.getPos()
        self._root = kstore.root
        self._fill_color = kstore.fill_color
        self._line_color = kstore.line_color
        self._line_width = kstore.line_width
        self._font_size = kstore.font_size
        self._font_color = kstore.font_color
        self._alive = True
        self._submit = None 
        self._font_name = kstore.font_name
        self._hidden = False 

    def setWidth(self, width):
        self.setSize(width, self._size[1])

    def getWidth(self):
        return self._size[0]

    def setHeight(self, height):
        self.setSize(self._size[0], height)
    
    def getHeight(self):
        return self._size[1] 
    
    def setSize(self, width:int|list, height:int=None):
        self._size = sanitizeXY(width, height)

        self._element.size = dpp(self._size)

    def getSize(self):
        return self._size

    def setText(self, text):
        self._text = str(text) 
        self._element.text = self._text 
    
    def getText(self):
        self._text = self._element.text
        return self._element.text
    
    def setPos(self, x:int|list, y:int=None):
        self._pos = sanitizeXY(x,y)
        self._element.pos = dpp(self._pos)
    
    def getPos(self):
        return (self.getX(), self.getY())
    
    def setX(self, x):
        self.setPos(x, self._pos[1])

    def getX(self):
        return self._pos[0]
    
    def setY(self, y):
        self.setPos(self._pos[0], y)

    def getY(self):
        return self._pos[1]
    
    def _rebind(self):
        pass 

    def setHandler(self, handler):
        self._handler = handler
        self._rebind()

    def getHandler(self):
        return self._handler
    
    def setFontSize(self, size):
        self._font_size = size
        self._element.font_size = int(dp(self._font_size))

    def getFontSize(self):
        return self._font_size
    
    def setFontColor(self, r:int|list|str,g:int=None,b:int=None,a:int=None):
        self._font_color = sanitizeColor(r,g,b,a)
        self._element.color = translateColor(self._font_color)
         
    def getFontColor(self):
        return self._font_color

    def setColor(self, r:int|list|str,g:int=None,b:int=None,a:int=None):
        self.setFillColor(r,g,b,a)
        
    def setFillColor(self, r:int|list|str,g:int=None,b:int=None,a:int=None):
        self._fill_color = sanitizeColor(r,g,b,a)
        self._element.background_color = translateColor(self._fill_color)
    
    def getFillColor(self):
        return self._fill_color
    
    def getColor(self):
        return self._fill_color

    def setAlpha(self, a):
        self.setFillAlpha(a)

    def setFillAlpha(self, a):
        self._fill_color = sanitizeColor(self._fill_color)
        self._fill_color[3] = a
        self._element.background_color = translateColor(self._fill_color)
    
    def getFillAlpha(self):
        return self._fill_color[3]
    
    def hide(self):
        if not self._hidden:
            self._root.remove_widget(self._element)
            self._hidden = True

    def show(self):
        if self._hidden and self._alive:
            self._root.add_widget(self._element)
            self._hidden = False
    
    def remove(self):
        if self._element == None:
            return 
        
        self._alive = False

        try:
            self._root.remove_widget(self._element)
        except:
            pass 

    def isDead(self):
        return not self._alive 
    
    def isAlive(self):
        return self._alive
    
class kButton(kUIElement):
    def __init__(self, handler, text=""):
        super().__init__()
        self._handler = handler 
        self._text = text 

    def _rebind(self):
        if self._submit != None:
            self._element.unbind(on_press=self._submit)
        
        def submit(instance):
            self._handler()

        self._submit = submit
        self._element.bind(on_press=submit)

    def _draw(self):
        self.remove()

        if not self._alive:
            return
        
        self._element = Button(text=self._text,size=dpp(self._size), pos=dpp(self._pos), font_name=self._font_name, font_size=dp(self._font_size))
        self._rebind()
        self._root.add_widget(self._element)

class kInput(kUIElement):
    def __init__(self, handler, text="", clear=False):
        super().__init__()
        self._handler = handler 
        self._text = str(text) 
        self._clear = clear
        self._padding = 5
    
    def _rebind(self):
        if self._submit != None:
            Window.unbind(on_keyboard=self._submit)
        
        def submit(window, key, *args, **kwargs):
            textfield = self._element
            if textfield.focus and key == 13 and textfield.focus and not 'shift' in args[2]:
                textfield.focus = False
                if self._handler:
                    self._handler(self._element.text[:-1])
                if self._clear:
                    self._text = ""
                    self._element.text = ""
                else:
                    self._element.text = self._element.text[:-1]
                return True

        self._submit = submit
        Window.bind(on_keyboard=submit)
        

    def _draw(self):
        self.remove()

        if not self._alive:
            return
        
        self._element = TextInput(size=dpp(self._size), text=self._text, multiline=True, size_hint=(None, None), pos=dpp(self._pos), padding=dp(self._padding), font_name=self._font_name, font_size=dp(self._font_size))
        # self.element.bind(on_text_validate=self.submit)
        self._rebind()
        self._root.add_widget(self._element)
        
    def setClear(self, clear):
        self._clear = clear

    def setFillColor(self, r:int|list|str,g:int=None,b:int=None,a:int=None):
        super().setFontColor(r, g, b, a)
        self._cursor_color = translateColor(self._font_color)

    def setPadding(self, padding):
        self._padding = padding 
        self._element.padding = dp(self._padding)
    
    def getPadding(self):
        return self._padding

class kSlider(kUIElement):
    def __init__(self, minimum, value, maximum, handler):
        super().__init__()
        self._minimum = minimum
        self._maximum = maximum
        self._value = value 
        self._handler = handler 

    def _rebind(self):
        if self._submit != None:
            self._element.unbind(value=self._submit)
        
        def submit(instance, value):
            self._handler(value)

        self._submit = submit
        self._element.bind(value=submit)

    def _draw(self):
        self.remove()
        
        if not self._alive:
            return
        
        self._step = (self._maximum - self._minimum)/10

        slider = Slider(min=self._minimum, max=self._maximum, value = self._value, pos=dpp(self._pos), size=dpp(self._size), step = self._step)
        self._root.add_widget(slider)
        self._element = slider 
        self._rebind()

    def setMin(self, minimum):
        self._minimum = minimum 
        self._step = (self._maximum - self._minimum)/10
        self._element._step = self._step
        self._element._min = self._minimum 

    def getMin(self):
        return self._minimum 
    
    def setMax(self, maximum):
        self._maximum = maximum 
        self._step = (self._maximum - self._minimum)/10
        self._element.step = self._step
        self._element.max = maximum 
    
    def getMax(self):
        return self._maximum 
    
    def setValue(self, value):
        self._value = min(self._maximum, max(self._minimum, value))
        self._element.value = self._value
    
    def getValue(self):
        return self._element.value 

class kSwitch(kUIElement):
    def __init__(self, handler, value=0):
        super().__init__()
        if value:
            value = 1
            self._text = "An"
        else:
            value = 0
            self._text = "Aus"
        
        self._value = value
        self._handler = handler 
    
    def _rebind(self):
        if self._submit != None:
            self._element.unbind(on_press=self._submit)
        
        def submit(instance):
            if self._value:
                self._value = 0
                self._text = "Aus"
                self._element.text = self._text
            else:
                self._value = 1
                self._text = "An"
                self._element.text = self._text

            self._handler(self._value)

        self._submit = submit
        self._element.bind(on_press=submit)

    def _draw(self):
        self.remove()
        
        if not self._alive:
            return
        
        if self._value:
            state = "down"
        else:
            state = "normal"

        self._element = ToggleButton(text=self._text,size=dpp(self._size), pos=dpp(self._pos), font_name=self._font_name, font_size=dp(self._font_size), state=state)
        
        self._rebind()
        self._root.add_widget(self._element)

    def setValue(self, value):
        if value:
            value = 1
            self._text = "An"
            state = "down"

        else:
            value = 0
            self._text = "Aus"
            state = "normal"

        self._value = value 
        self._element.state = state
        self._element.text = self._text

    def getValue(self):
        value = 1

        if self._element.state == "normal":
            value = 0
        return value 
    
    def setPos(self, x:int|list, y:int=None):
        self._pos = sanitizeXY(x,y)
        self._element.pos = dpp((self._pos[0], self._pos[1]))

class kLabel(kUIElement):
    def __init__(self, text, xalign="center", yalign="center"):
        super().__init__()
        self._text = str(text)
        self._padding = 5
        self._xalign = xalign
        self._yalign = yalign
        self._fill = True 
        self._border = True 
        self._rect = None 
        self._line = None 

    def setPos(self, x:int|list, y:int=None):
        super().setPos(x,y)
        self._rect.setPos(self.getPos())
        self._line.setPos(self.getPos())

    def _draw(self):
        self.remove()
        
        if not self._alive:
            return
        
        self._rect = drawRect(self._size[0], self._size[1], True)
        if not self._fill:
            self._rect.hide()

        self._line = drawRect(self._size[0], self._size[1], False)
        if not self._border:
            self._line.hide()

        self._element = Label(text=self._text, pos=dpp(self._pos), size=dpp(self._size), text_size=dpp((self._size[0]-2*self._padding, self._size[1]-2*self._padding)), size_hint=(1.0, 1.0), halign=self._xalign, valign=self._yalign, color=translateColor(self._font_color), font_size=dp(self._font_size), padding=dpp((self._padding, self._padding)), markup=True, font_name=self._font_name)
        self._root.add_widget(self._element)

    def setSize(self, width:int|list, height:int=None):
        self._size = sanitizeXY(width, height)

        self._rect.setSize(self._size)
        self._line.setSize(self._size)
        self._element.size = dpp(self._size)
        self._element.text_size = dpp((self._size[0] -2*self._padding, self._size[1] - 2*self._padding))
        
    def setWidth(self, width):
        self.setSize(width, self._size[1])

    def setHeight(self, height):
        self.setSize(self._size[0], height)

    def setFillColor(self, r:int|list|str,g:int=None,b:int=None,a:int=None):
        super().setFillColor(r, g, b, a)
        self._rect.setFillColor(self._fill_color)

    def setLineColor(self, r:int|list|str,g:int=None,b:int=None,a:int=None):
        super().setLineColor(r,g,b,a)
        self._line.setLineColor(self._line_color)

    def setXalign(self, xalign):
        self._xalign = xalign
        self._element.halign = self._xalign
    
    def getXalign(self):
        return self._xalign
    
    def setYalign(self, yalign):
        self._yalign = yalign
        self._element.valign = self._yalign

    def getYalign(self):
        return self._yalign 
    
    def setAlign(self, align):
        self.setXalign(align)
        self.setYalign(align)

    def getAlign(self):
        return (self._xalign, self._yalign)
    
    def setPadding(self, padding):
        self._padding = padding
        self.setSize(self._size)

    def getPadding(self):
        return self._padding
    
    def setFill(self, fill):
        self._fill = fill
        if fill:
            self._rect.show()
        else:
            self._rect.hide()

    def getFill(self):
        return self._fill 
    
    def setBorder(self, border):
        self._border = border 
        if border:
            self._line.show()
        else:
            self._line.hide()

    def getBorder(self):
        return self._border

    def hide(self):
        if not self._hidden:
            if self._rect:
                self._rect.hide()
            if self._line:
                self._line.hide()
            super().hide()

    def show(self):
        if self._hidden:
            if self._rect:
                self._rect.show()
            if self._line:
                self._line.show()
            super().show()

    def remove(self):
        super().remove()
        if self._rect:
            self._rect.remove()
        if self._line:
            self._line.remove()

class DrawingWidget(Widget):
    def __init__(self):
        super(DrawingWidget, self).__init__()       
                
class DrawingApp(App):
    def __init__(self):
        super(DrawingApp, self).__init__()
        kstore.root = DrawingWidget()


    def build(self):
        return kstore.root
    
    def start(self):
        self.run()

key_store = set()
mouse_button_store = set()
mouse_position = (0,0)
mouse_moved_store = False 

def addKeyToStore(key):
    key_store.add(key)

def removeKeyFromStore(key):
    try:
        key_store.remove(key)
    except:
        pass

def addMouseButtonToStore(x,y,button):
    mouse_button_store.add(button)

def removeMouseButtonFromStore(x,y,button):
    mouse_button_store.remove(button)

def updateMouseMoved(dt):
    global mouse_moved_store, mouse_position

    new_mouse_position = Window.mouse_pos
    
    if new_mouse_position[0] == mouse_position[0] and new_mouse_position[1] == mouse_position[1]:
        mouse_moved_store = False 
    else:
        mouse_moved_store = True 
    
    mouse_position = new_mouse_position

color_dict = {
    "red": (255, 0, 0, 255),
    "green": (0, 255, 0, 255),
    "blue": (0, 0, 255, 255),
    "yellow": (255, 255, 0, 255),
    "orange": (255, 165, 0, 255),
    "purple": (128, 0, 128, 255),
    "pink": (255, 192, 203, 255),
    "brown": (139, 69, 19, 255),
    "gray": (128, 128, 128, 255),
    "white": (255, 255, 255, 255),
    "black": (0, 0, 0, 255),
}


def sanitizeColor(r,g=None,b=None,a=None):
    if isinstance(r, (list, tuple)):
        g = r[1]
        b = r[2]

        if len(r) > 3:
            a = r[3]
        else:
            a = 255

        r = r[0]
    elif isinstance(r, (str)):
        try:
            return color_dict[r]
        except:
            colors = color_dict.keys()
            raise ValueError("Color '" + r + "' unknown. Choose from " + str(colors))
    elif a == None:
        a = 255

    return [r,g,b,a]

def translateColor(color):
    factor = 1/255
    return list((c*factor for c in color))
    
def screenCoordinates(point):
    factor = dp(1)
    return (point[0]/factor, point[1]/factor)
# ============================================================================

def getMousePos():
    """
        - gibt Mausposition als Liste [x,y] zurück
        - x nach rechts (0 an linken Fensterrand)
        - y nach oben (0 am unteren Fensterrand)
    """
    return list([value/dp(1) for value in mouse_position])

def getMouseX():
    """
        - Mausposition in Pixel
        - x nach rechts (0 an linken Fensterrand)
    """
    return mouse_position[0]/dp(1)

def getMouseY():
    """
        - Mausposition in Pixel
        - y nach oben (0 am unteren Fensterrand)
    """
    return mouse_position[1]/dp(1)


def setReady():
    kstore.ready = True

def createWindow():
    """
        - muss als erste Funktion im Programm aufgerufen werden
        - Koordinate x nach rechts
        - Koordinate y nach oben
        - Ursprung (0,0) unten links
        - 800x800 Fenster
    """
    kstore.app = DrawingApp()
    Window.multisamples = 4
    setWindowSize(800,800)
    onKeyPressed(addKeyToStore)
    onKeyReleased(removeKeyFromStore)
    onMousePressed(addMouseButtonToStore)
    onMouseReleased(removeMouseButtonFromStore)
    addEvent(setReady, 1.5)
    addLoop(updateMouseMoved, 0.01)
    return kstore.app
    
def maximizeWindow():
    """
        - maximiere Fenstergrösse
    """
    old_left = Window.left
    old_top = Window.top 
    old_width = Window.size[0]
    old_height = Window.size[1]

    # in screen coordinates
    screen_width = old_width + 2*old_dp(1)*old_left
    screen_height = old_height + 2*old_dp(1)*old_top

    setWindowSize(screen_width/old_dp(1)/scale_factor, screen_height/old_dp(1)/scale_factor, True)
    

def setWindowSize(width, height, debug=False):
    """
        - setze Fenstergrösse in Pixel
        - Breite width
        - Höhe height
    """
    new_width = dp(width)
    new_height = dp(height)

    old_left = Window.left
    old_top = Window.top 
    old_width = Window.size[0]
    old_height = Window.size[1]

    # in screen coordinates
    screen_width = old_width + 2*old_dp(1)*old_left
    screen_height = old_height + 2*old_dp(1)*old_top
    
    new_left = (screen_width - new_width)/2
    new_top = (screen_height - new_height)/2

    new_width /= old_dp(1)
    new_height /= old_dp(1)
    new_left /= old_dp(1)
    new_top /= old_dp(1)

    # must be in dp coordinates (meaning half of screen coordinates)
    Window.size = (new_width, new_height)
    
    # this as well
    Window.left = new_left
    Window.top = new_top

    kstore.left = new_left 
    kstore.top = new_top

    kstore.width = new_width/scale_factor
    kstore.height = new_height/scale_factor

    if kstore.grid != None:
        kstore.grid._draw()

    if debug:
        print('scale: ', scale_factor)
        print("1dp: ", old_dp(1))
        print("order: width, height, left, top, screen_width, screen_height")
        print("old: ", old_width, old_height, old_left, old_top, old_width + 4*old_left, old_height + 4*old_top)
        print("new: ", new_width, new_height, new_left, new_top, new_width+2*new_left, new_height + 2*new_top)
        print("screen: ", screen_width, screen_height)

def setWindowHeight(height):
    """
        - setze Fensterhöhe in Pixel
    """
    setWindowSize(kstore.width, height)

def setWindowWidth(width):
    """
        - setze Fensterbreite in Pixel
    """
    setWindowSize(width, kstore.height)

class kGrid:
    def __init__(self):
        self._width = kstore.width
        self._height = kstore.height  
        self._label_font_size = 14
        self._xlines = []
        self._ylines = []
        self._xlabels = []
        self._ylabels = []
        self._xlabel=None 
        self._ylabel=None

    def _reset(self):
        for line in self._xlines:
            line.remove()
        self._xlines = []

        for line in self._ylines:
            line.remove()
        self._ylines = []

        for label in self._xlabels:
            label.remove()
        self._xlabels = []

        for label in self._ylabels:
            label.remove()
        self._ylabels = []

        if self._xlabel != None:
            self._xlabel.remove()
        
        if self._ylabel != None:
            self._ylabel.remove()

    def _draw(self):
        if len(self._xlines) > 0 or len(self._ylines) > 0:
            self._reset()

        self._width = kstore.width
        self._height = kstore.height  

        self.xlines = []
        self.ylines = []
        self.xlabels = []
        self.ylabels = []

        kstore.push()
        
        for x in range(0, int(self._width), 100):
            setPos(x, 0)
            line = drawGridLine(0, self._height)
            line.setLineAlpha(50)
            line.setLineWidth(1)
            self._xlines.append(line)
            label = drawLabel(str(x), "left", "bottom")
            label.setSize(100,100)
            label.setFill(False)
            label.setBorder(False)
            label.setFontSize(self._label_font_size)
            label.setFontColor(200,200,200)
            self._xlabels.append(label)
       
        setPos(int(self._width) - 50, 0)
        label = drawLabel(int(self._width), "left", "bottom")
        label.setSize(100,100)
        label.setFill(False)
        label.setBorder(False)
        label.setFontSize(self._label_font_size)
        label.setFontColor(200,200,200)
        self._xlabels.append(label)

        setPos(45,0)
        xlabel = drawLabel("x", "left", "bottom")
        xlabel.setSize(100,100)
        xlabel.setFill(False)
        xlabel.setBorder(False)
        xlabel.setFontSize(self._label_font_size)
        self._xlabel = xlabel

        for y in range(0, int(self._height), 100):
            setPos(0, y)
            line = drawGridLine(self._width, 0)
            self._ylines.append(line)
            line.setLineAlpha(50)
            line.setLineWidth(1)
            label = drawLabel(str(y), "left", "bottom")
            label.setSize(100,100)
            label.setFill(False)
            label.setBorder(False)
            label.setFontSize(self._label_font_size)
            label.setFontColor(200,200,200)
            self._xlabels.append(label)
        
        setPos(0, int(self._height) - 50)
        label = drawLabel(int(self._height), "left", "bottom")
        label.setSize(100,100)
        label.setFill(False)
        label.setBorder(False)
        label.setFontSize(self._label_font_size)
        label.setFontColor(200,200,200)
        self._ylabels.append(label)

        setPos(0,45)
        ylabel = drawLabel("y", "left", "bottom")
        ylabel.setSize(100,100)
        ylabel.setFill(False)
        ylabel.setBorder(False)
        ylabel.setFontSize(self._label_font_size)
        self._ylabel = ylabel 

        kstore.pop()

def makeTurtle():
    """
        - gibt ein Turtle Objekt zurück
        - steuere Turtle wie gewohnt
    """   
    return kTurtle()

def showGrid(value=True):
    """
    - blende Koordinatengitter ein
    - x nach rechts
    - y nach oben
    - Ursprung (0,0) unten links
    - 800x800 Gitter
    """
    if kstore.root == None:
        raise Exception(" > du hast vermutlich ein createWindow() vergessen")

    if value:
        if kstore.grid != None:
            return kstore.grid
                
        kstore.grid = kGrid()
        kstore.grid._draw()
        return kstore.grid
    elif kstore.grid != None:
            kstore.grid._reset()
            kstore.grid = None

def getWindowSize():
    """
        - gibt Fenstergrösse in Pixel als Liste [width,height] zurück
    """
    return [getWindowWidth(), getWindowHeight()]

def getWindowWidth():
    """
        - gibt Fensterbreite in Pixel zurück
    """
    return kstore.width

def getWindowHeight():
    """
        - gibt Fensterhöhe in Pixel zurück
    """
    return kstore.height

def addEvent(handler, delay=0):
    """
        - Das Event wird nur einmal abgefeuert.

        - Die Funktion handler() muss diese Form haben (ohne Argument):

            def handler():
                ...

        - delay ist eine optionale Verzögerung
    """
    clock = Clock.schedule_once(lambda dt: handler(), delay)

def addLoop(handler, delta_time=0.01):
    """
        - Das Event wird in regelmässigen Zeitabständen abgefeuert.
        - Die Funktion handler(dt) muss diese Form haben:

            def handler(dt):
                ...
        
        - delta_time (in s) ist lediglich eine Wunschzeit; kann auch langsamer sein
    """
    if delta_time < 0.01:
        delta_time = 0.01

    def the_handler(dt):
        if kstore.ready:
            handler(dt)

    clock = Clock.schedule_interval(the_handler, delta_time)

    return clock

def drawInput(handler = None, text = "", clear=False):
    """
        - zeichnet ein Textfeld
        - handler muss genau ein Argument text aufweisen (def handler(text): ...)
        - wird handler weggelassen, kann der Text mit input.getText() gelesen werden
        - text ist optional
        - wenn clear True ist, wird das Feld bei Enter gelöscht
    """
    input = kInput(handler, text, clear)
    input._draw()
    return input 

def drawButton(handler, text=""):
    """
       - zeichnet einen Button
       - handler() darf kein Argument aufweisen (def handler(): ...)
       - text ist optional
    """
    button = kButton(handler, text)
    button._draw()
    return button 

def drawSwitch(handler, value=False):
    """
        - zeichnet einen Schalter
        - handler muss genau ein Argument aufweisen (def handler(value):...)
        - default value ist 0
    """
    switch = kSwitch(handler, value)
    switch._draw()
    return switch

def drawLabel(text, xalign="center", yalign="center"):
    """
        - zeichnet einen Text (string)
        - zulässige Werte für xalign: "left", "center", "right"
        - zulässige Werte für yalign: "top", "center", "bottom"
    """
    label = kLabel(text, xalign, yalign)
    label._draw()
    return label

def drawSlider(minimum, maximum, handler, value=None):
    """
        - zeichnet einen Schieberegler
        - Die zulässigen Slider Werte befinden sich zwischen minimum und maximum
        - handler muss genau ein Argument aufweisen (def handler(value):...)
        - Wird value weggelassen, ist der Defaultwert das Minimum.
    """
    if value == None:
        value = minimum 

    slider = kSlider(minimum, value, maximum, handler)
    slider._draw()
    return slider
    
def setLineWidth(width:int):
    """
        - Liniendicke in Pixel
    """
    kstore.line_width = width

def setLineColor(r:int|list|str,g:int=None,b:int=None,a:int=None):
    """
        - alle Farbwerte sind zwischen 0 und 255
        - optionales Argument a: Transparenz zwischen 0 (transparnet) und 255 (sichtbar)

        Verwendung
        - entweder setLineColor(r,g,b,a=None)
        - oder setLineColor(string) (z. Bsp. "red")
        - oder setLineColor([r,g,b]) als Liste
        - oder setLineColor([r,g,b,a]) als Liste
    """
    kstore.line_color = sanitizeColor(r,g,b,a)

def setFillColor(r:int|list|str,g:int=None,b:int=None,a:int=None):
    """
        - alle Farbwerte sind zwischen 0 und 255
        - optionales Argument a: Transparenz zwischen 0 (transparnet) und 255 (sichtbar)

        Verwendung
        - entweder setFillColor(r,g,b,a=None)
        - oder setFillColor(string) (z. Bsp. "red")
        - oder setFillColor([r,g,b]) als Liste
        - oder setFillColor([r,g,b,a]) als Liste
    """
    kstore.fill_color = sanitizeColor(r,g,b,a)

def setColor(r:int|list|str,g:int=None,b:int=None,a:int=None):
    """
        - setzt die FillColor und LineColor gleichzeitig
        - alle Farbwerte sind zwischen 0 und 255
        - optionales Argument a: Transparenz zwischen 0 (transparnet) und 255 (sichtbar)

        Verwendung
        - entweder setColor(r,g,b,a=None)
        - oder setColor(string) (z. Bsp. "red")
        - oder setColor([r,g,b]) als Liste
        - oder setColor([r,g,b,a]) als Liste
    """
    kstore.fill_color = sanitizeColor(r,g,b,a)
    kstore.line_color = sanitizeColor(r,g,b,a)

def setFontSize(size:int):
    """
        - Schriftgrösse in Pixel
    """
    kstore.font_size = size

def setFontColor(r:int|list|str,g:int=None,b:int=None,a:int=None):
    """
        - alle Farbwerte sind zwischen 0 und 255
        - optionales Argument a: Transparenz zwischen 0 (transparnet) und 255 (sichtbar)

        Verwendung
        - entweder setFontColor(r,g,b,a=None)
        - oder setFontColor(string) (z. Bsp. "red")
        - oder setFontColor([r,g,b]) als Liste
        - oder setFontColor([r,g,b,a]) als Liste

    """
    kstore.font_color = sanitizeColor(r,g,b,a)

class kList(kShape):
    def __init__(self, the_list, width=None):
        super().__init__()
        self._the_list = list(the_list)
        self._normify()
        self._indices = False
        self._fill = True
        self._font_size = kstore.font_size
        self._font_color = kstore.font_color
        
        if width == None:
            self._width = 50*len(the_list)
        else:
            self._width = width
        self._cell_width = self._width/len(list(the_list))
        self._cell_height = 50
        self._hlines = []
        self._vlines = []
        self._labels = []
        self._rects = []
        self._xindices = []
        self._yindices = []
        self._line_width = 1

    def _normify(self):
        for i in range(len(self._the_list)):
            row = self._the_list[i]
            if not hasattr(row, '__iter__'):
                self._the_list[i] = [row]

    def setPos(self, x:int|list, y:int=None):
        old_pos = self.getPos()
        self._pos = sanitizeXY(x,y)
        
        delta_x = self._pos[0] - old_pos[0]
        delta_y = self._pos[1] - old_pos[1]

        for line in self._hlines:
            pos = line.getPos()
            line.setPos(pos[0]+delta_x, pos[1]+delta_y)
        
        for line in self._vlines:
            pos = line.getPos()
            line.setPos(pos[0]+delta_x, pos[1]+delta_y)

        for row in self._labels:
            for label in row:
                pos = label.getPos()
                label.setPos(pos[0]+delta_x, pos[1]+delta_y)

        for row in self._rects:
            for rect in row:
                pos = rect.getPos()
                rect.setPos(pos[0]+delta_x,pos[1]+delta_y)

        for index in self._xindices:
            pos = index.getPos()
            index.setPos(pos[0]+delta_x, pos[1]+delta_y)
        
        for index in self._yindices:
            pos = index.getPos()
            index.setPos(pos[0]+delta_x, pos[1]+delta_y)

    def setList(self, the_list):
        old_list = self._the_list
        self._the_list = list(the_list)
        self._normify()
        self._draw()

        for i in range(len(self._the_list)):
            row = list(self._the_list[i])
            for j in range(len(row)):
                cell = row[j]
                try:
                    old_value = old_list[i][j]
                except:
                    old_value = 999999999999999

                if cell != old_value:
                    self._labels[i][j].setFillColor(100,100,200)
                else:
                    self._labels[i][j].setFillColor(self._fill_color)

    def getList(self):
        return self._the_list
    
    def _update(self):
        for i in range(len(self._the_list)):
            row = list(self._the_list[i])
            for j in range(len(row)):
                cell = row[j]
                if cell != self._labels[i][j]:
                    self._labels[i][j].setFillColor(100,100,200)
                else:
                    self._labels[i][j].setFillColor(self.fill_color)
                self._labels[i][j].setText(cell)
                

    def setFill(self, fill):
        self._fill = fill 
        self._draw()

    def getFill(self):
        return self._fill

    def setWidth(self, width):
        self._width = width
        self._draw()

    def getWidth(self):
        return self._width

    def setCellWidth(self, width):
        self._cell_width = width 
        self._draw()

    def getCellWidth(self):
        return self._cell_width
    
    def setCellHeight(self, height):
        self._cell_height = height
        self._draw()

    def getCellHeight(self):
        return self._cell_height
    
    def setLineColor(self, r:int|list|str,g:int=None,b:int=None,a:int=None):
        self._line_color = sanitizeColor(r,g,b,a)
        for line in self._hlines:
            line.setLineColor(self._line_color)
        for line in self._vlines:
            line.setLineColor(self._line_color)

    def setFillColor(self, r:int|list|str,g:int=None,b:int=None,a:int=None):
        self._fill_color = sanitizeColor(r,g,b,a)
        for row in self._rects:
            for rect in row:
                rect.setFillColor(self._fill_color)
    
    def setFontColor(self, r:int|list|str,g:int=None,b:int=None,a:int=None):
        self._font_color = sanitizeColor(r,g,b,a)

        for row in self._labels:
            for label in row:
                label.setFontColor(self._font_color)

        for index in self._xindices:
            index.setFontColor(self._font_color)
        
        for index in self._yindices:
            index.setFontColor(self._font_color)

    def setFontSize(self, size):
        self._font_size = size
        for row in self._labels:
            for label in row:
                label.setFontSize(self._font_size)

        for index in self._xindices:
            index.setFontSize(self._font_size)
        
        for index in self._yindices:
            index.setFontSize(self._font_size)

    def getFontSize(self):
        return self._font_size
    
    def _draw(self):
        delta_x = self._cell_width
        delta_y = self._cell_height

        x = self.getX()
        len_x = len(self._the_list)

        for line in self._hlines:
            line.remove()

        for line in self._vlines:
            line.remove()

        for row in self._labels:
            for label in row:
                label.remove()

        for row in self._rects:
            for rect in row:
                rect.remove()

        for index in self._xindices:
            index.remove()
        
        for index in self._yindices:
            index.remove()

        self.vlines = []
        self.hlines = []
        self.labels = []
        self.rects = []
        self.xindices = []
        self.yindices = []

        for i in range(len_x):
            row = list(self._the_list[i])

            y = self.getY() - delta_y

            len_y = len(row)

            column_labels = []
            column_rects = []

            if self._indices:
                new_xindex = drawLabel(i)
                new_xindex.setSize(delta_x, delta_y)
                new_xindex.setPos(x, self.getY()+20 + delta_y/2 - delta_y)
                new_xindex.setFontSize(int(self.getFontSize()*3/4))
                new_xindex.setFontColor(self._font_color)
                new_xindex.setFill(False)
                new_xindex.setBorder(False)
                self._xindices.append(new_xindex)

            for j in range(len_y):
                cell = str(row[j])
                    
                new_rect = drawRect(delta_x, delta_y, self._fill)
                new_rect.setPos(x,y)
                new_rect.setLineAlpha(0)
                new_rect.setFillColor(self.getFillColor())
                column_rects.append(new_rect)

                new_label = drawLabel(cell)
                new_label.setFill(False)
                new_label.setSize(delta_x, delta_y)
                new_label.setPos(x,y)
                new_label.setFontSize(self.getFontSize())
                new_label.setFontColor(self._font_color)
                new_label.setBorder(False)

                column_labels.append(new_label)
                
                if i != len_x - 1: # last column
                    column_line = drawLine(0, delta_y)
                    column_line.setPos(x+delta_x,y)
                    column_line.setLineWidth(self.getLineWidth())
                    column_line.setLineColor(self.getLineColor())
                    self._vlines.append(column_line)
                
                if j != len_y - 1: # last row
                    row_line = drawLine(delta_x, 0)
                    row_line.setPos(x,y)
                    row_line.setLineWidth(self.getLineWidth())
                    row_line.setLineColor(self.getLineColor())
                    self._hlines.append(row_line)

                if self._indices and len(self._yindices) < j+1 and j > 0:
                    if j == 1:
                        zindex = drawLabel(0)
                        zindex.setSize(delta_x, delta_y)
                        zindex.setPos(self.getX()-20-delta_x/2, self.getY() - delta_y)
                        zindex.setFontSize(int(self.getFontSize()*3/4))
                        zindex.setFontColor(self._font_color)
                        zindex.setFill(False)
                        zindex.setBorder(False)

                        self._yindices.append(zindex)

                    new_yindex = drawLabel(j)
                    new_yindex.setSize(delta_x, delta_y)
                    new_yindex.setPos(self.getX()-20- delta_x/2, y)
                    new_yindex.setFontSize(int(self._font_size*3/4))
                    new_yindex.setFontColor(self._font_color)
                    new_yindex.setFill(False)
                    new_yindex.setBorder(False)

                    self._yindices.append(new_yindex)
                y -= delta_y

            self._labels.append(column_labels)
            self._rects.append(column_rects)

            x += delta_x

    def showIndices(self):
        self._indices = True 
        self._draw()
    
    def hideIndices(self):
        self._indices = False 
        self._draw()

def drawList(the_list, width=None):
    """
        - zeichnet den Inhalt einer Liste
        - Die Liste ist eindimensional oder zweidimensional.
        - Der Cursor steht immer oben links.
        - Standardmässig Zellen der Dimension 50x50 Pixel
    """
    my_list = kList(the_list, width)
    my_list._draw()
    return my_list

def drawLine(width:int|list, height:int=None):
    """
        - zeichne Linie beginnend bei Cursor

        - width: Anzahl Pixel in x-Richtung
        - height: Anzahl Pixel in y-Richtung

        Verwendung
        - entweder drawLine(width,height)
        - oder drawLine([width,height])
    """
    pos = kstore.getPos()
    size = sanitizeXY(width, height)
    line = kLine(pos[0] + size[0],pos[1] + size[1])
    line._draw()
    return line 

def drawGridLine(width, height):
    pos = kstore.getPos()
    x = pos[0]
    y = pos[1]
    line = kLine(x+width,y+height, True)
    line._draw()
    return line 

def drawLineTo(x:int|list, y:int=None):
    """
        - zeichne Linie von Cursor zu Punkt [x,y]

        Verwendung
        - entweder drawLineTo(x,y)
        - oder drawLineTo([x,y])
    """
    end_point = sanitizeXY(x, y)
    line = kLine(end_point[0], end_point[1])
    line._draw()

    return line

def remove(element):
    """
        - entfernt das Element von der Zeichenfläche
    """
    element.remove()

def clear():
    """
        - lösche die Zeichenfläche
    """
    kstore.root.canvas.clear()

def drawRect(width, height, fill=True):
    """
        - zeichne Rechteck (Cursor untere linke Ecke)

        - Breite width
        - Hoehe height
        - optional fill (default True)
    """
    rect = kRect(width, height, fill)
    rect._draw()
    return rect
                    
def drawCircle(radius, fill=True):
    """
        - zeichne Kreis (Cursor im Mittelpunkt)

        - Radius radius
        - optional fill (default True)
    """
    circle = kEllipse(radius, radius, 0, 360, fill)
    circle._draw()
    return circle

def drawEllipse(a, b, fill=True):
    """
        - zeichne Ellipse (Cursor im Mittelpunkt)

        - horizontale Halbachse a
        - vertikale Halbachse b
        - optional fill (default True)
    """
    ellipse = kEllipse(a,b,0,360,fill)
    ellipse._draw()
    return ellipse

def drawArc(radius, begin_angle, end_angle, fill=True):
    """
        - zeichne Kreisbogen zwischen Winkel begin_angle und end_angle (Cursor im Mittelpunkt)

        - Radius radius in Pixeln
        - Winkel sind in Grad gemessen
        - 0 Grad zeigt nach rechts
        - positive Winkel zeigen im Gegenuhrzeigersinn, negative im Uhrzeigersinn
        - Startwinkel begin_angle, Endwinkel end_angle
        - optional fill (default True)
    """
    arc = kEllipse(radius, radius, begin_angle, end_angle, fill)
    arc._draw()
    return arc

def drawPoly(points:list, fill:bool=False, cyclic:bool=True):
    """
        - zeichne Polygon

        - Punkteliste points (jeder Punkt von der Form [x,y])
        - optional cyclic (default True) beschreibt, ob die Kurve automatisch geschlossen werden soll
    """
    polygon = kPoly(points, fill, cyclic)
    polygon._draw()
    return polygon 

def _save():
    filename = sys.argv[0][:-3] + ".png"

    kstore.root.export_to_png(filename)

def run():
    """
        - Diese Funktion muss zwingend als letztes im Programm aufgerufen werden.
    """
    if kstore.save:
        addEvent(_save, 0)

    kstore.app.run()

def sanitizeXY(x,y=None):
    if isinstance(x, (list, tuple)):
        return [x[0], x[1]]
    else:
        return [x,y]

def setPos(x:int|list, y:int=None):
    """
        - setze Cursor Position
        - x nach rechts zwischen 0 und 800
        - y nach oben zwischen 0 und 800

        Verwendung
        - setPos(x,y)
        - setPos([x,y]) als Liste
    """
    kstore.setPos(x,y)

def setX(x: int):
    """
        - setze Cursor x 
        - x von links nach rechts zwischen 0 und 800
    """
    kstore.setPos(x, kstore.getPos()[1])


def setY(y: int):
    """
        - setze Cursor y
        - y von unten nach oben zwischen 0 und 800
    """
    kstore.setPos(kstore.getPos()[0], y)

def getPos():
    """
        - erhalte Cursor Position als Liste [x,y]
        - siehe getX() und getY()
    """
    return kstore.getPos()

def getX():
    """
        - erhalte Cursor x
        - x von links 0 nach rechts 800
    """
    return kstore.getPos()[0]

def getY():
    """
        - erhalte Cursor y
        - y von unten 0 nach oben 800
    """
    return kstore.getPos()[1]

def setRot(angle):
    """
        - setze Rotationswinkel in Grad
        - positive Winkel im Gegenuhrzeigersinn
        - negative Winkel im Uhrzeigersinn 
    """
    kstore.angle = angle

def getRot():
    """
        - erhalte Rotationswinkel in Grad
        - positive Winkel im Gegenuhrzeigersinn
        - negative Winkel im Uhrzeigersinn 
    """
    return kstore.angle

def centerPos():
    """
        - positioniere den Cursor in der Fenstermitte
    """
    kstore.setPos(getWindowWidth()/2, getWindowHeight()/2)
    return kstore.getPos()

def move(x:int|list, y:int=None):
    """
        - bewege Cursor um x nach rechts/links und y nach oben/unten
        
        Beispiel 
        - move(50,-100) bewegt den Cursor um 50 nach rechts und 100 nach unten 

        Verwendung
        - entweder move(x,y)
        - oder move([x,y]) als Liste
    """
    delta = sanitizeXY(x,y)
    old_pos = kstore.getPos()
    setPos(old_pos[0]+delta[0], old_pos[1]+delta[1])


def onMouseMoved(handler):
    """
        - feuert handler(x,y) ab, falls die Maus im letzten Frame bewegt wurde
        - handler benötigt zwingend zwei Argumente (def handler(x,y): ...)
    """
    def submit(instance, touch):
        handler(*screenCoordinates(touch))

    Window.bind(mouse_pos=submit)

def onMousePressed(handler, button=None):
    """
        - feuert handler(x,y,button) ab, falls ein Mousebutton im letzten Frame gedrückt wurde
        - handler benötigt zwingend drei Argumente (def handler(x,y,button): ...)
        - wird button weggelassen, wird handler bei jedem Klick abgefeuert
        - button kann die Werte "left", "middle" und "right" annehmen
    """
    def submit(instance, touch):
        if button == None:
            handler(*screenCoordinates(touch.pos), touch.button)
        elif touch.button == button:
            handler(*screenCoordinates(touch.pos))


    kstore.root.bind(on_touch_down=submit)

def onMouseReleased(handler, button=None):
    """
        - feuert handler(x,h,button) ab, falls ein Mousebutton im letzten Frame losgelassen wurde
        - handler benötigt zwingend drei Argumente (def handler(x,y,button): ...)
        - wird button weggelassen, wird handler bei jedem Mouserelease abgefeuert
        - button kann die Werte "left", "middle" und "right" annehmen
    """
    def submit(instance, touch):
        if button == None:
            handler(*screenCoordinates(touch.pos), touch.button)
        elif touch.button == button:
            handler(*screenCoordinates(touch.pos))


    kstore.root.bind(on_touch_up=submit)
    
def onKeyPressed(handler, key=None):
    """
        - feuer handler(key) ab, falls eine Taste im letzten Fraem gedrückt wurde
        - handler benötigt zwingend ein Argument (def handler(key): ...)
        - wird key weggelassen, wird handler bei jedem Tastendruck abgefeuert
        - key kann Werte "left", "up", "a", "3", "lctrl", "spacebar", "backspace" annehmen
    """
    def submit(*args):
        keycode = args[1]

        try:
            the_key = keyboard.keycode_to_string(keycode)
        except:
            the_key = keycode

        if key != None and the_key == key:
            handler()
        elif key == None:
            handler(the_key)

    Window.bind(on_key_down=submit)

keyboard = Keyboard()

def onKeyReleased(handler, key=None):
    """
        - feuert handler(key) ab, falls eine Taste im letzten Frame losgelassen wurde
        - handler benötigt zwingend ein Argument (def handler(key): ...)
        - wird key weggelassen, wird handler bei jedem Tastenrelease abgefeuert
        - key kann Werte "left", "up", "a", "3", "lctrl", "spacebar", "backspace" annehmen
    """
    def submit(*args):
        keycode = args[1]

        try:
            the_key = keyboard.keycode_to_string(keycode)
        except:
            the_key = keycode      

        if key != None and the_key == key:                  
            handler()
        elif key == None:
            handler(the_key)

    Window.bind(on_key_up=submit)

def isKeyPressed(key):
    """
        - gibt True zurück, falls key im letzten Frame gedrückt wurde.
        - key kann Werte "left", "up", "a", "3", "lctrl", "spacebar", "backspace" annehmen
    """
    return key in key_store

def isMousePressed(button):
    """
        - gibt True zurück, falls button im letzten Frame gedrückt wurde
        - button kann die Werte "left", "middle" und "right" annehmen
    """
    return button in mouse_button_store

def hasMouseMoved():
    """
        - gibt True zurück, falls die Maus im letzten Frame bewegt wurde
    """
    return mouse_moved_store

def drawGraph(width=800, height=800):
    """
        - zeichnet ein Koordinatensystem (graph) mit Breite width und Höhe height
        - Standarddimension 800x800 Pixel
        - Cursorposition unten links
    """
    graph = kGraph(width, height)
    graph._draw()
    return graph


class Recorder:
    def __init__(self, begin, end, fps, file_name):
        """
            file_name: without .gif
        """ 
        self.begin = begin
        self.end = end
        self.counter = 0
        self.file_name = file_name
        self.frame_buffer = []
        self.canvas = kstore.root.canvas
        self.root = kstore.root 
        self.in_progress = False
        self.fps = fps
        self.active = True 
        self.start_time = 0

        os.makedirs(file_name, exist_ok=True)
        if os.path.isfile(file_name + ".gif"):
            os.remove(file_name + ".gif")
            
    def on_draw(self, instruction):
        if self.active and not self.in_progress and kstore.ready:
            self.in_progress = True

            if Clock.get_time() - self.start_time < self.end:
                file_name = f"{self.file_name}/frame_{self.counter}.png"
                self.root.export_to_png(file_name)
                self.frame_buffer.append(file_name)
            else:                                           
                duration = int(1000/self.fps)
                frames = []
                for frame in self.frame_buffer:
                    image = Image.open(frame)
                    image.info['duration'] = duration
                    frames.append(image)

                frames[0].save(self.file_name + ".gif", save_all=True, append_images=frames[1:], duration=duration, loop=0, disposal=2)
                print("recording saved to ", self.file_name + ".gif")
                shutil.rmtree(self.file_name)
                self.active = False
            
            self.counter += 1
            self.in_progress = False

        
    def arm(self):
        def _handler(dt):
            self.start_time = Clock.get_time()
            self.canvas.add(Callback(self.on_draw))

        self.clock = Clock.schedule_once(_handler, self.begin)

def record(begin, end, fps, file_name):
    """
        - produziert ein GIF file
        - begin: Startzeitpunkt in Sekunden
        - end: Endzeitpunkt in Sekunden
        - fps: frames per second (Bilder pro Sekunde)
        - file_name: gewünschter Name (Suffix .gif wird angehängt)
    """
    the_recorder = Recorder(begin, end, fps, file_name)
    the_recorder.arm()

def save():
    """
        - speichert ein Bild der Zeichenfläche unter dem Namen des Skripts (.png) ab, d.h. anstatt .py wird ein .png gespeichert.
    """
    kstore.save = True
    
def getSample(name):
    """
        - erhalte eine vordefinierte Liste zurück
        - name: Name der Liste
    """
    if name == "colors1":
        the_list = []
        for r in range(0,255,50):
            for g in range(0,255,50):
                for b in range(0,255,50):
                    the_list.append([r,g,b])
    elif name == "colors2":
        the_list = []
        for x in range(0,800, 1):
            x = math.exp(-x/300)*255
            y = math.sin(x*30/800)*math.exp(-x/300)*255
            z = math.cos(x*30/800)*math.exp(-x/300)*255
            the_list.append([x,y,z])
    elif name == "colorpalette1":
        the_list = [
            [255, 0, 0],   # Red
            [0, 255, 0],   # Green
            [0, 0, 255],   # Blue
            [255, 255, 0], # Yellow
            [255, 0, 255], # Magenta
            [0, 255, 255], # Cyan
            [128, 0, 128], # Purple
            [255, 165, 0], # Orange
            [0, 128, 0],   # Dark Green
            [0, 0, 128],   # Dark Blue
        ]
    elif name == "coords1":
        the_list = []
        for x in range(0,800, 1):
            y = math.sin(x*30/800)*math.exp(-x/300)*400 + 400
            the_list.append([x,y])
    elif name == "coords2":
        the_list = []
        for i in range(10):
            x = random.randint(0,800)
            y = random.randint(0,800)
            the_list.append([x,y])
    elif name == "coords3":
        the_list = []
        for x in range(0,800, 1):
            y = math.sin(x*20/800)*300 - x/2 + 100*(random.random()-0.5) + 600
            the_list.append([x,y])
    elif name == "coords4":
        the_list = []
        for a in range(0,360,1):
            radius = 255
            x = radius*math.cos(a/180*math.pi)
            y = radius*math.sin(a/180*math.pi)
            the_list.append([x,y])
    elif name == "circles1":
        the_list = []
        for r in range(0,400):
            h = r%50*5
            the_list.append([400-r,h])
    elif name == "strings1":
        the_list = ["Alice", "Bob", "Charlie", "Danita", "Erich", "Frederica", "Gian", "Hanna", "Ibn", "Jasmin", "Kevin", "Lisa", "Manuel", "Nora", "Oskar", "Petra", "Qasim", "Rihanna", "Sandro", "Theres", "Ulrich", "Vivienne", "Walter", "Xenia", "Yannes", "Zora"]
    elif name == "int1":
        the_list = list([random.randint(1,100) for x in range(0,10)])
    elif name == "int2":
        the_list = list([abs(x  - x**3) for x in range(0,10)])
    elif name == "int3":
        the_list = list([abs(x - x**2) for x in range(0,10)])
    elif name == "percentage1":
        the_list = [10,20,10,40,20]
    elif name == "percentage2":
        the_list = [30,20,10,40]
    elif name == "temperatures1": # average zearly temperatures southern switzerland
        the_list = [
        [1864, 2.81], [1865, 3.7], [1866, 3.76], [1867, 3.57], [1868, 4.08], [1869, 3.37], [1870, 2.91], [1871, 2.84],
        [1872, 3.74], [1873, 3.88], [1874, 3.28], [1875, 3.25], [1876, 3.55], [1877, 3.27], [1878, 3.02], [1879, 2.49],
        [1880, 3.94], [1881, 3.43], [1882, 3.57], [1883, 2.76], [1884, 3.51], [1885, 3.6], [1886, 3.24], [1887, 2.48],
        [1888, 2.71], [1889, 2.58], [1890, 2.68], [1891, 2.77], [1892, 3.26], [1893, 3.64], [1894, 3.41], [1895, 3.04],
        [1896, 2.82], [1897, 3.87], [1898, 4.27], [1899, 4.05], [1900, 3.79], [1901, 2.72], [1902, 3.29], [1903, 3.16],
        [1904, 3.95], [1905, 2.83], [1906, 3.26], [1907, 3.37], [1908, 3.34], [1909, 2.64], [1910, 2.84], [1911, 3.98],
        [1912, 3.04], [1913, 3.48], [1914, 3.33], [1915, 2.88], [1916, 3.25], [1917, 2.64], [1918, 3.61], [1919, 2.67],
        [1920, 4.37], [1921, 4.64], [1922, 3.22], [1923, 3.76], [1924, 3.67], [1925, 3.24], [1926, 4.1], [1927, 4.05],
        [1928, 4.06], [1929, 3.53], [1930, 3.84], [1931, 3.11], [1932, 3.5], [1933, 3.11], [1934, 4.29], [1935, 3.14],
        [1936, 3.46], [1937, 3.63], [1938, 3.72], [1939, 3.28], [1940, 2.95], [1941, 2.81], [1942, 3.89], [1943, 4.57],
        [1944, 3.17], [1945, 4.31], [1946, 3.98], [1947, 4.69], [1948, 4.75], [1949, 4.82], [1950, 4.27], [1951, 3.81],
        [1952, 3.5], [1953, 4.42], [1954, 3.33], [1955, 3.55], [1956, 2.56], [1957, 4.21], [1958, 4.13], [1959, 4.41],
        [1960, 3.24], [1961, 4.69], [1962, 3.07], [1963, 3.15], [1964, 4.32], [1965, 2.92], [1966, 3.68], [1967, 3.94],
        [1968, 3.44], [1969, 3.27], [1970, 3.31], [1971, 4.05], [1972, 3.42],
        [1973, 3.76], [1974, 3.59], [1975, 3.99], [1976, 3.75], [1977, 3.57],
        [1978, 3.47], [1979, 3.48], [1980, 3.22], [1981, 3.78], [1982, 4.3],
        [1983, 4.51], [1984, 3.11], [1985, 3.78], [1986, 3.83], [1987, 4.06],
        [1988, 4.51], [1989, 5.04], [1990, 4.84], [1991, 4.27], [1992, 4.9],
        [1993, 4.31], [1994, 5.39], [1995, 4.32], [1996, 3.89], [1997, 5.15],
        [1998, 4.62], [1999, 4.55], [2000, 4.96], [2001, 4.62], [2002, 5.14],
        [2003, 5.32], [2004, 4.64], [2005, 4.28], [2006, 5.13], [2007, 5.48],
        [2008, 4.76], [2009, 4.99], [2010, 3.82], [2011, 5.87], [2012, 5.18],
        [2013, 4.72], [2014, 5.41], [2015, 6.01], [2016, 5.36], [2017, 5.44],
        [2018, 5.78], [2019, 5.63], [2020, 5.8], [2021, 4.88], [2022, 6.45]
    ]
    else:
        return []
    
    return the_list 

def main(): # debug code (test cases)
    print(" > Installation abgeschlossen")

if __name__ == '__main__':
    main()
