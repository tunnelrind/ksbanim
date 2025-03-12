import sys, subprocess
import math
import traceback 
import random
import threading
import os
import struct
import copy 
from abc import ABC, abstractmethod
import pkg_resources, requests
from shapely.geometry import Polygon
import triangle as tr
import colorsys

def check_for_updates():
    package_name = 'ksbanim'
    try:
        current_version = pkg_resources.get_distribution(package_name).version
        response = requests.get(f'https://pypi.org/pypi/{package_name}/json')
        response.raise_for_status()
        latest_version = response.json()['info']['version']
        
        if current_version != latest_version:
            print(f"A new version of {package_name} is available ({latest_version}). You have {current_version}.")
            update = input("Would you like to update now? (enter yes/no): ").strip().lower()
            if update == 'yes':
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', package_name])
                print(f"{package_name} has been updated to version {latest_version}. Please restart the python program.")
                exit()
    except Exception as e:
        print(f"An error occurred while checking for updates: {e}")

check_for_updates()


from OpenGL.GL import *

from PyQt5.QtWidgets import QApplication, QLabel, QDesktopWidget, QDockWidget, QOpenGLWidget, QPushButton
from PyQt5.QtGui import QPainter, QBrush, QPen, QPixmap, QColor, QTransform, QFont, QFontMetrics, QSurfaceFormat, QOpenGLContext, QImage
from PyQt5.QtCore import Qt, QTimer, QElapsedTimer, QRect, QRectF, QBuffer

import imageio


QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

app = QApplication.instance()
if app is None:
    app = QApplication([])

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
        self.immediate = kstore.immediate
        if self.immediate:
            self.begin_time = kstore.elapsed_timer.elapsed()
        else:
            self.begin_time = kstore.milliseconds
        self.end_time = kstore.animation + self.begin_time
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
    
   
class kShapeMatcher:
    def __init__(self, end_value, getter, setter):
        self.immediate = kstore.immediate
        if self.immediate:
            self.begin_time = kstore.elapsed_timer.elapsed()
        else:
            self.begin_time = kstore.milliseconds
        self.end_time = kstore.animation + self.begin_time
        self.dt = self.end_time - self.begin_time
        self.end_value = end_value
        self.getter = getter
        self.setter = setter
        self.begin_value = getter()
            
    def resample(self, vertices, target_count):
        if not vertices:
            return [(0, 0)] * target_count

        if len(vertices) == target_count:
            return vertices
        
        total_length = 0
        distances = []
        for i in range(0, len(vertices)):
            dx = vertices[(i+1)%len(vertices)][0] - vertices[i][0]
            dy = vertices[(i+1)%len(vertices)][1] - vertices[i][1]
            d = math.sqrt(dx**2 + dy**2)
            total_length += d
            distances.append(d)

        interval_length = total_length / (target_count - 1)

        resampled = [vertices[0]]
        i = 0
        cumulative_length = interval_length

        while len(resampled) < target_count:
            if distances[i] <= cumulative_length:
                resampled.append(vertices[i+1])
                cumulative_length -= distances[i]
                i = i + 1
            else:
                cumulative_length += interval_length
                this = i
                next = (i+1)%len(vertices)
                if distances[i] == 0:
                    fraction = 0.01
                else:
                    fraction = cumulative_length/distances[i]

                x = (1-fraction)*vertices[this][0] + fraction*vertices[next][0]
                y = (1-fraction)*vertices[this][1] + fraction*vertices[next][1]
                resampled.append([x,y])

        return resampled

    def blend_vertices(self, begin_vertices, end_vertices, fraction):
        blended_vertices = []
        for bv, ev in zip(begin_vertices, end_vertices):
            blended_vertex = (
                self.interpolate_value(bv[0], ev[0], fraction),
                self.interpolate_value(bv[1], ev[1], fraction)
            )
            blended_vertices.append(blended_vertex)
        return blended_vertices

    def interpolate_value(self, start, end, fraction):
        return (1 - fraction) * start + fraction * end

    def find_best_shift(self, begin_vertices, end_vertices):
        min_total_distance = float('inf')
        best_shift = 0
        for shift in range(len(begin_vertices)):
            total_distance = 0
            for i in range(len(begin_vertices)):
                bv = begin_vertices[(i + shift) % len(begin_vertices)]
                ev = end_vertices[i]
                distance = math.sqrt((bv[0] - ev[0]) ** 2 + (bv[1] - ev[1]) ** 2)
                total_distance += distance
            if total_distance < min_total_distance:
                min_total_distance = total_distance
                best_shift = shift
        return best_shift

    def interpolate(self, fraction):
        begin_vertices = self.begin_value
        end_vertices = self.end_value
        
        if not begin_vertices:
            return end_vertices
        if not end_vertices:
            return begin_vertices
        
        max_vertices = max(len(begin_vertices), len(end_vertices))
        begin_vertices = self.resample(begin_vertices, max_vertices)
        end_vertices = self.resample(end_vertices, max_vertices)
        
        best_shift = self.find_best_shift(begin_vertices, end_vertices)
        begin_vertices = begin_vertices[best_shift:] + begin_vertices[:best_shift]
        
        interpolated_vertices = self.blend_vertices(begin_vertices, end_vertices, fraction)
        
        return interpolated_vertices

    def process(self, the_time):
        if the_time >= self.end_time:
            value = self.interpolate(1)
            self.setter(value)
            return -1 
        elif the_time < self.begin_time:
            self.begin_value = self.getter()
            return 0
        
        fraction = (the_time - self.begin_time) / self.dt
        value = self.interpolate(fraction)
        self.setter(value)
        return 1

class kLoop:
    def __init__(self, loop_function, milliseconds):
        self.immediate = kstore.immediate
        if self.immediate:
            self.begin_time = 0
        else:
            self.begin_time = kstore.milliseconds
        self.loop_function = loop_function 
        self.milliseconds = milliseconds

    def process(self, the_time):
        if self.begin_time <= the_time:
            if self.milliseconds == 0:
                self.begin_time = the_time 
            else:
                self.begin_time = the_time - the_time%self.milliseconds + self.milliseconds
            old_milliseconds = kstore.milliseconds
            kstore.milliseconds = self.begin_time
            self.loop_function()
            kstore.milliseconds = old_milliseconds
            return 1
        else:
            return 0

class kMessage:
    def __init__(self, message):
        self.message = message

        self.immediate = kstore.immediate
        if self.immediate:
            self.begin_time = kstore.elapsed_timer.elapsed()
        else:
            self.begin_time = kstore.milliseconds
            
    def process(self, the_time):
        if self.begin_time <= the_time:
            print(self.message)
            return -1
        else:
            return 0

class kAction:
    def __init__(self, action_function):
        self.immediate = kstore.immediate
        if self.immediate:
            self.begin_time = kstore.elapsed_timer.elapsed()
        else:
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
        self.immediate = kstore.immediate
        if self.immediate:
            self.begin_time = kstore.elapsed_timer.elapsed()
        else:
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

class kStore:
    def __init__(self):
        self.app = None 
        self.pixmap = None 
        self.size = [1000, 1000]
        self.scale_factor = 1
        self.pos = [500,500]
        self.rot = 0
        self.timer = None 
        self.dt = round(1000/60)
        self.milliseconds = 0
        self.delay = 250
        self.animation = 250
        self.anim_stack = []
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
        self.window = None 
        self.grid = None 
        self.immediate = False
        self.pendown = False 
        self.color_mixing = "subtractive"

    def setPos(self, *point):
        new_pos = toFloatList(point)
        old_pos = copy.deepcopy(self.pos)
        line = None
        if self.pendown:
            dx = new_pos[0] - old_pos[0]
            dy = new_pos[1] - old_pos[1]

            length = (dx**2 + dy**2)**0.5
            temp = kstore.milliseconds
            angle = math.atan2(dy,dx)
            old_rot = self.rot 
            self.rot = math.degrees(angle)
            line = drawLine(length)
            self.rot = old_rot
            self.pos = new_pos
            kstore.milliseconds = temp
            self.cursor.setPos(self.pos)
            kstore.milliseconds = temp + max(kstore.animation, kstore.delay)
        else:
            self.pos = toFloatList(point)
            self.scaleAnim(0)
            self.cursor.setPos(self.pos)
            self.unscaleAnim()
        return line 
        
    def getPos(self):
        return self.pos.copy()

    def setX(self, x):
        self.setPos(x, self.pos[1])
    
    def getX(self):
        return self.pos[0]
    
    def setY(self, y):
        self.setPos(self.pos[0], y)
    
    def getY(self):
        return self.pos[1]
    
    def setRot(self, angle):
        self.rot = angle
        if self.pendown:
            self.cursor.setRot(angle)
            kstore.milliseconds += max(kstore.delay, kstore.animation) - kstore.delay
        else:
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
    
    def setFontColor(self, *rgba):
        self.fontColor = toColor(rgba)

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
        self.anim_stack.append([self.animation, self.delay])
        self.animation = int(self.animation*factor)
        self.delay = int(self.delay*factor)

    def unscaleAnim(self):
        if len(self.anim_stack) == 0:
            return 

        latest = self.anim_stack.pop()

        self.animation = latest[0]
        self.delay = latest[1]

    def setPen(self, value):
        self.pendown = value 

kstore = kStore()

def printErrorGL(message = ""):
    err = glGetError()
    if err:
        print(message, " OpenGL error: ", err)
    elif message != "":
        print(message, " ok")


def tessellate(outer_contour, holes=[]):
    if len(outer_contour) < 3:
        return outer_contour

    poly = Polygon(outer_contour, holes)
    
    vertices = list(poly.exterior.coords)[:-1]  # Exclude the closing point
    segments = [[i, (i + 1) % len(vertices)] for i in range(len(vertices))]
    
    for hole in holes:
        hole_vertices = list(hole)[:-1]  # Exclude the closing point
        hole_segments = [[i + len(vertices), (i + 1) % len(hole_vertices) + len(vertices)] for i in range(len(hole_vertices))]
        vertices.extend(hole_vertices)
        segments.extend(hole_segments)
    
    poly_dict = {'vertices': vertices, 'segments': segments}
    
    triangulated = tr.triangulate(poly_dict, 'p')
    if 'triangles' not in triangulated:
        return []
    
    triangles = []
    for tri in triangulated['triangles']:
        for idx in tri:
            triangles.append(triangulated['vertices'][idx])
    
    return triangles
    
def kNumber(instance, name, initial_value, update=True):
    cast = float
    initial_value = cast(initial_value)

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
        setattr(instance, private_name, cast(value))
        if update:
            instance._updateShape()
        instance._draw()

    def public_getter():
        return getattr(instance, name, initial_value)

    def public_setter(value):
        value = cast(value)
        setattr(instance, name, value)
        action_queue.add(kInterpolator(value, private_getter, private_setter))

    setattr(instance, f"_{getter_name}", private_getter)
    setattr(instance, f"_{setter_name}", private_setter)
    setattr(instance, f"{getter_name}", public_getter)
    setattr(instance, f"{setter_name}", public_setter)

    def public_set_both(value):
        value = cast(value)
        setattr(instance, private_name, value)
        setattr(instance, name, value)

    setattr(instance, f"init{capitalized_name}", public_set_both)

    return (public_getter, public_setter)

def kValue(instance, name, initial_value, update=True):
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
        if update:
            instance._updateShape()
        instance._draw()

    def public_getter():
        return getattr(instance, name, initial_value)

    def public_setter(value):
        def public_setter_inner(the_value = value):
            setattr(instance, name, the_value)
            action_queue.add(kSetter(private_setter, the_value))
        return public_setter_inner()
    
    setattr(instance, f"_{getter_name}", private_getter)
    setattr(instance, f"_{setter_name}", private_setter)
    setattr(instance, f"{getter_name}", public_getter)
    setattr(instance, f"{setter_name}", public_setter)

    def public_set_both(value):
        setattr(instance, private_name, value)
        setattr(instance, name, value)

    setattr(instance, f"init{capitalized_name}", public_set_both)

    return (public_getter, public_setter)

def kVec2(instance, name, *initial_value, update=True):
    cast = float 

    name = name
    private_name = f"_{name}"
    capitalized_name = name[0].upper() + name[1:]
    getter_name = f"get{capitalized_name}"
    setter_name = f"set{capitalized_name}"

    setattr(instance, private_name, toFloatList(initial_value))
    setattr(instance, name, toFloatList(initial_value))

    # > (x,y)

    def private_getter():
        return getattr(instance, private_name)

    def private_setter(*value):
        setattr(instance, private_name, toFloatList(value))
        if update:
            instance._updateShape()
        instance._draw()

    def public_getter():
        return getattr(instance, name, initial_value)

    def public_setter(*value):
        setattr(instance, name, toFloatList(value))
        action_queue.add(kInterpolator(toFloatList(value), private_getter, private_setter))

    
    setattr(instance, f"_{getter_name}", private_getter)
    setattr(instance, f"_{setter_name}", private_setter)
    setattr(instance, f"{getter_name}", public_getter)
    setattr(instance, f"{setter_name}", public_setter)

    def public_set_both(value):
        setattr(instance, private_name, toFloatList(value))
        setattr(instance, name, toFloatList(value))

    setattr(instance, f"init{capitalized_name}", public_set_both)

    # > x

    def private_getter_x():
        value = private_getter()
        return value[0]

    def private_setter_x(value):
        old_value = private_getter()
        private_setter(cast(value), cast(old_value[1]))
    
    def public_getter_x():
        value = public_getter()
        return value[0]

    def public_setter_x(value):
        old_value = public_getter()
        old_value[0] = cast(value)
        setattr(instance, name, old_value)
        action_queue.add(kInterpolator(cast(value), private_getter_x, private_setter_x))

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
        private_setter(cast(old_value[0]), cast(value))
    
    def public_getter_y():
        value = public_getter()
        return value[1]

    def public_setter_y(value):
        old_value = public_getter()
        old_value[1] = cast(value)
        setattr(instance, name, old_value)
        action_queue.add(kInterpolator(cast(value), private_getter_y, private_setter_y))

    setattr(instance, f"_{getter_name}Y", private_getter_y)
    setattr(instance, f"_{setter_name}Y", private_setter_y)
    setattr(instance, f"{getter_name}Y", public_getter_y)
    setattr(instance, f"{setter_name}Y", public_setter_y)

    return (public_getter, public_setter, public_getter_x, public_setter_x, public_getter_y, public_setter_y)


def kVecN(instance, name, *initial_value, update=True):
    name = name
    private_name = f"_{name}"
    capitalized_name = name[0].upper() + name[1:]
    getter_name = f"get{capitalized_name}"
    setter_name = f"set{capitalized_name}"

    setattr(instance, private_name, toFloatList(initial_value))
    setattr(instance, name, toFloatList(initial_value))

    # > (x,y)

    def private_getter():
        return getattr(instance, private_name)

    def private_setter(*value):
        setattr(instance, private_name, toFloatList(value))
        if update:
            instance._updateShape()
        instance._draw()

    def public_getter():
        return getattr(instance, name, initial_value)

    def public_setter(*value):
        setattr(instance, name, toFloatList(value))
        action_queue.add(kInterpolator(toFloatList(value), private_getter, private_setter))

    
    setattr(instance, f"_{getter_name}", private_getter)
    setattr(instance, f"_{setter_name}", private_setter)
    setattr(instance, f"{getter_name}", public_getter)
    setattr(instance, f"{setter_name}", public_setter)

    def public_set_both(value):
        setattr(instance, private_name, toFloatList(value))
        setattr(instance, name, toFloatList(value))

    setattr(instance, f"init{capitalized_name}", public_set_both)

    return (public_getter, public_setter)

def kColor(instance, name, *args, update=True):
    name = name
    private_name = f"_{name}"
    capitalized_name = name[0].upper() + name[1:]
    getter_name = f"get{capitalized_name}"
    setter_name = f"set{capitalized_name}"

    initial_value_private = toColor(args)
    initial_value_public = toColor(args)

    setattr(instance, private_name, initial_value_private)
    setattr(instance, name, initial_value_public)

    # > rgba

    def private_getter():
        return getattr(instance, private_name, initial_value_private)

    def private_setter(*value):
        setattr(instance, private_name, toColor(value))
        if update:
            instance._updateShape()
        instance._draw()

    def public_getter():
        return getattr(instance, name, initial_value_public)

    def public_setter(*value):
        setattr(instance, name, toColor(value))
        action_queue.add(kInterpolator(toColor(value), private_getter, private_setter))

    setattr(instance, f"_{getter_name}", private_getter)
    setattr(instance, f"_{setter_name}", private_setter)
    setattr(instance, f"{getter_name}", public_setter)
    setattr(instance, f"{setter_name}", public_getter)

    def public_set_both(*value):
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
    setattr(instance, f"{getter_name}R", public_getter_r)
    setattr(instance, f"{setter_name}R", public_setter_r)
    
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
    setattr(instance, f"{getter_name}G", public_getter_g)
    setattr(instance, f"{setter_name}G", public_setter_g)
    
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
    setattr(instance, f"{getter_name}B", public_getter_b)
    setattr(instance, f"{setter_name}B", public_setter_b)

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


class kRainbow:
    def __init__(self, pieces):
        self.pieces = pieces
        self.i = 0
        self.brightness = 255
        self.saturation = 255
    
    def getBrighness(self):
        return self.brightness 

    def setBrightness(self, brightness):
        self.brightness = brightness

    def getSaturation(self):
        return self.saturation

    def setSaturation(self, saturation):
        self.saturation = saturation 
    
    def next(self):
        hue = (self.i / self.pieces) % 1.0
        rgb = colorsys.hsv_to_rgb(hue, min(self.saturation/255, 255), min(self.brightness/255, 255))
        self.i += 1
        return tuple(int(c * 255) for c in rgb)
    
    def reset(self):
        self.i = 0
    
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
        r'\\Omega': 'Ω',
        r'\\deg': '°',
        r'\\cdot': '·',
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

    return text    

def toFloatList(args):
    cast = float 
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        if not len(args[0]) > 1:
            raise ValueError("expected x and y, but got only x")
        return list([cast(a) for a in args[0]])
    else:
        if not len(args) > 1:
            raise ValueError("expected x and y, but got only x")
        return list([cast(a) for a in args])
    
def toColor(args):
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        if len(args[0]) == 3:
            r, g, b = args[0]
            a = 255
        elif len(args[0]) == 4:
            r, g, b, a = args[0]
        else:
            raise ValueError("color list must have 3 [r,g,b] or 4 [r,g,b,a] elements")
    elif len(args) == 3:
        r, g, b = args
        a = 255
    elif len(args) == 4:
        r, g, b, a = args
    else:
        raise ValueError("color must have 3 (rgb) or 4 (rgba) arguments" + str(args))

    return [int(r),int(g),int(b),int(a)]

# ==================================== SHAPES ===========================================

shape_buffer = []
ui_buffer = []

class kShape(ABC):
    counter = 0

    def __init__(self, shape = None):
        self.name = "kShape"
        self.id = kShape.counter
        kShape.counter += 1

        self.vertices = []
        self._vertices = []
        self._triangles = []
        self._fillMode = GL_TRIANGLE_FAN
        self._vbo = None 
        self._vbo_triangle = None
        self._idGL = None
        
        self._pixmap = None
        self._painter = None 
        self._transform = QTransform()
        
        self.getReady, self.setReady = kValue(self, "ready", False, update=False)

        self.getRot, self.setRot = kNumber(self, "rot", kstore.rot, update=False)
        self.getLineWidth, self.setLineWidth = kNumber(self, "lineWidth", kstore.lineWidth)

        self.getPos, self.setPos, self.getX, self.setX, self.getY, self.setY = kVec2(self, "pos", kstore.pos, update=False)

        self.getPivot, self.setPivot, self.getPivotX, self.setPivotX, self.getPivotY, self.setPivotY = kVec2(self, "pivot", [0,0], update=False)

        self.getFillColor, self.setFillColor = kColor(self, "fillColor", kstore.fillColor, update=False)
        self.getLineColor, self.setLineColor = kColor(self, "lineColor", kstore.lineColor, update=False)

        self.getFill, self.setFill = kValue(self, "fill", kstore.fill, update=False)
        self.getLine, self.setLine = kValue(self, "line", kstore.line, update=False)

        self.getOnClick, self.setOnClick = kValue(self, "onClick", None, update=False)
        self.getOnRelease, self.setOnRelease = kValue(self, "onRelease", None, update=False)
        self.getOnMouseEnter, self.setOnMouseEnter = kValue(self, "onMouseEnter", None, update=False)
        self.getOnMouseExit, self.setOnMouseExit = kValue(self, "onMouseExit", None, update=False)
        
        self._mouse_over = False

        if shape is not None:
            self.initRot(shape.rot)
            self.initLineWidth(shape.lineWidth)
            self.initPos(shape.pos)
            self.initFillColor(shape.fillColor)
            self.initLineColor(shape.lineColor)
            self.initFill(shape.fill)
            self.initLine(shape.line)
            self.initOnClick(shape.onClick)
            self.initOnRelease(shape.onRelease)
            self.initOnMouseEnter(shape.onMouseEnter)
            self.initOnMouseExit(shape.onMouseExit)
            self._vertices = shape._vertices 
            pivot_x = self.pivot[0] + shape.pivot[0]
            pivot_y = self.pivot[1] + shape.pivot[1]
            self.initPivot([pivot_x, pivot_y])
        
        kstore.scaleAnim(0)
        self.show()
        kstore.unscaleAnim()

        shape_buffer.append(self)

    def getPos(self): pass
    def setPos(self, *point): pass
    def getX(self): pass 
    def setX(self, x): pass 
    def getY(self): pass
    def setY(self, y): pass 
    def getRot(self): pass 
    def setRot(self, angle): pass
    def getPivot(self): pass 
    def setPivot(self, *point): pass
    def getPivotX(self): pass 
    def setPivotX(self, x): pass
    def getPivotY(self): pass
    def setPivotY(self, y): pass 
    def getFill(self): pass        
    def setFill(self, value): pass
    def getLine(self): pass         
    def setLine(self, value): pass
    def getFillColor(self): pass 
    def setFillColor(self, *rgb): pass
    def getLineColor(self): pass
    def setLineColor(self, *rgb): pass
    def getLineWidth(self): pass    
    def setLineWidth(self, value): pass

    def getName(self):
        return self.name + " (" + str(self.id) + ")"
    
    def print(self, *message):
        print("{:<15}".format(self.name) + "(" + str(self.id) + ") >           " , *message)

    def show(self):
        self.setReady(True)
    
    def hide(self):
        self.setReady(False)
    
    def _remove(self):
        self.hide()
        shape_buffer.remove(self)

    def remove(self):
        self.ready = False
        action_queue.add(kAction(self._remove))

    def move(self, *distance):
        distance = toFloatList(distance)
        self.pos[0] += distance[0]
        self.pos[1] += distance[1]
        action_queue.add(kInterpolator(self.pos, self._getPos, self._setPos))

    def forward(self, distance):
        angle = self.rot/180*math.pi
        self.pos[0] += math.cos(angle)*distance
        self.pos[1] += math.sin(angle)*distance 
        action_queue.add(kInterpolator(self.pos, self._getPos, self._setPos))

    def backward(self, distance):
        self.forward(-distance)

    def left(self, distance):
        self.setPos(self.getX()-distance, self.getY())

    def right(self, distance):
        self.setPos(self.getX()+distance, self.getY())

    def up(self, distance):
        self.setPos(self.getX(), self.getY()+distance)

    def down(self, distance):
        self.setPos(self.getX()-distance, self.getY()-distance)

    def rotate(self, angle):
        angle = angle
        self.rot += angle
        action_queue.add(kInterpolator(self.rot, self._getRot, self._setRot))

        return self.pos.copy()

    def _setColor(self, *rgba):
        color = toColor(rgba)
        self._lineColor = color
        self._fillColor = color
        self._draw()

    def getColor(self):
        return self.fillColor

    def _getColor(self):
        return self._fillColor
    
    def setColor(self, *rgba):
        color = toColor(rgba)
        self.lineColor = color
        self.fillColor = color
        action_queue.add(kInterpolator(color, self._getColor, self._setColor))

    def _generateVBO(self):
        flattened_vertices = [float(coord) for vertex in self._vertices for coord in vertex]
        vertex_data = struct.pack(f'{len(flattened_vertices)}f', *flattened_vertices)

        if self._vbo is not None:
            glDeleteBuffers(1, [self._vbo])
            self._vbo = None 
        
        self._vbo = glGenBuffers(1)

        glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
        glBufferData(GL_ARRAY_BUFFER, len(vertex_data), vertex_data, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        if self._fillMode == GL_TRIANGLES:
            self._triangles = tessellate(copy.deepcopy(self._vertices))
            
            flattened_triangles = [coord for vertex in self._triangles for coord in vertex]
            triangle_data = struct.pack(f'{len(flattened_triangles)}f', *flattened_triangles)

            if self._vbo_triangle is not None:
                glDeleteBuffers(1, [self._vbo_triangle])
                self._vbo_triangle = None 
            
            self._vbo_triangle = glGenBuffers(1)

            glBindBuffer(GL_ARRAY_BUFFER, self._vbo_triangle)
            glBufferData(GL_ARRAY_BUFFER, len(triangle_data), triangle_data, GL_DYNAMIC_DRAW)
            glBindBuffer(GL_ARRAY_BUFFER, 0)

    def _updateShape(self):
        self._vertices = self._generateVertices()
        self._generateVBO()

    def _draw(self):
        if not self._ready or self._vbo is None:
            return 
        
        if self._idGL is not None:
            glDeleteLists(self._idGL, 1)
            self._idGL = None

        idGL = glGenLists(1)
        glNewList(idGL, GL_COMPILE)
        glPushMatrix()

        glTranslatef(self._pos[0], self._pos[1], 0)
        glRotatef(self._rot, 0, 0, 1)
        glTranslatef(-self._pivot[0], -self._pivot[1], 0)

        if self._fill:
            if self._fillMode == GL_TRIANGLE_FAN:
                glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
                glEnableVertexAttribArray(0)
                glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, None)
                glColor4ub(*list([int(c) for c in self._fillColor]))
                glDrawArrays(GL_TRIANGLE_FAN, 0, len(self._vertices))
                glDisableVertexAttribArray(0)
                glBindBuffer(GL_ARRAY_BUFFER, 0)
            elif self._fillMode == GL_TRIANGLES:
                glBindBuffer(GL_ARRAY_BUFFER, self._vbo_triangle)
                glEnableVertexAttribArray(0)
                glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, None)
                glColor4ub(*list([int(c) for c in self._fillColor]))
                glDrawArrays(GL_TRIANGLES, 0, len(self._triangles))
                glDisableVertexAttribArray(0)
                glBindBuffer(GL_ARRAY_BUFFER, 0)

        if self._line:
            glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
            glEnableVertexAttribArray(0)
            glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, None)
            glColor4ub(*list([int(c) for c in self._lineColor]))
            glDrawArrays(GL_LINE_LOOP, 0, len(self._vertices))
            glDisableVertexAttribArray(0)
            glBindBuffer(GL_ARRAY_BUFFER, 0)

        glPopMatrix()
        glEndList()


        self._idGL = idGL

    def _drawGL(self):
        if self._idGL is None or not self._ready:
            return 
        
        glPushMatrix()
        glCallList(self._idGL)
        printErrorGL()
        glPopMatrix()

    def getOnMouseEnter(self): pass
    def setOnMouseEnter(self, handler): pass
    def getOnMouseExit(self): pass
    def setOnMouseExit(self, handler): pass 
    def getOnClick(self): pass
    def setOnClick(self, handler): pass 
    def getOnRelease(self): pass
    def setOnRelease(self, handler): pass


    @abstractmethod 
    def _generateVertices(self):
        pass 

    @abstractmethod
    def generateVertices(self):
        pass 

    @abstractmethod
    def copy(self):
        pass

    def _getVertices(self):
        return self._vertices
    
    def _setVertices(self, vertices):
        self._fillMode = GL_TRIANGLES
        self._vertices = copy.deepcopy(vertices)
        self._generateVBO()
        self._draw()

    def getVertices(self):
        return self.generateVertices()

    def setVertices(self, vertices):
        self.vertices = copy.deepcopy(vertices) 
        action_queue.add(kShapeMatcher(copy.deepcopy(vertices), self._getVertices, self._setVertices))
        
    def toRect(self, *size):
        kstore.scaleAnim(0)
        new_shape = kRect(*size, shape=self)
        new_shape._setVertices(self.generateVertices())
        self.hide()
        kstore.unscaleAnim()
        new_shape.setVertices(new_shape.generateVertices())
        return new_shape 

    def toCircle(self, radius):
        kstore.scaleAnim(0)
        new_shape = kCircle(radius, shape=self)
        new_shape._setVertices(self.generateVertices())            
        self.hide()
        kstore.unscaleAnim()
        new_shape.setVertices(new_shape.generateVertices())
        return new_shape 

    def toEllipse(self, *size):
        kstore.scaleAnim(0)
        new_shape = kEllipse(*size, shape=self)
        new_shape._setVertices(self.generateVertices())
        self.hide()
        kstore.unscaleAnim()
        new_shape.setVertices(new_shape.generateVertices())
        return new_shape 

    def toRoundedRect(self, width, height, radius):
        kstore.scaleAnim(0)
        new_shape = kRoundedRect(width, height, radius, shape=self)
        new_shape._setVertices(self.generateVertices())
        self.hide()
        kstore.unscaleAnim()
        new_shape.setVertices(new_shape.generateVertices())
        return new_shape 

    def toTriangle(self, length):
        kstore.scaleAnim(0)
        new_shape = kTriangle(length, shape=self)
        new_shape._setVertices(self.generateVertices())
        self.hide()
        kstore.unscaleAnim()
        new_shape.setVertices(new_shape.generateVertices())
        return new_shape 

    def toArc(self, radius, angle):
        kstore.scaleAnim(0)
        new_shape = kArc(radius, angle, shape=self)
        new_shape._setVertices(self.generateVertices())
        self.hide()
        kstore.unscaleAnim()
        new_shape.setVertices(new_shape.generateVertices())
        return new_shape 

    def toLine(self, *size):
        kstore.scaleAnim(0)
        new_shape = kLine(size, shape=self)
        new_shape._setVertices(self.generateVertices())
        self.hide()
        kstore.unscaleAnim()
        new_shape.setVertices(new_shape.generateVertices())
        return new_shape 

    def toVector(self, *size):
        kstore.scaleAnim(0)
        new_shape = kVector(*size, shape=self)
        new_shape._setVertices(self.generateVertices())
        new_shape.initFill(True)
        new_shape.initLine(False)
        self.hide()
        kstore.unscaleAnim()
        new_shape.setVertices(new_shape.generateVertices())
        return new_shape 

    def toPolygon(self, vertices):
        kstore.scaleAnim(0)
        new_shape = kPolygon(vertices, shape=self)
        new_shape._setVertices(self.generateVertices())
        self.hide()
        kstore.unscaleAnim()
        new_shape.setVertices(new_shape.generateVertices())
        return new_shape 

class kEllipse(kShape):
    def __init__(self, *size, shape=None):
        super().__init__(shape)
        self.name = "kEllipse"
        size = toFloatList(size)
        self.getSize, self.setSize, self.getA, self.setA, self.getB, self.setB = kVec2(self, "size", size)

        if shape is None:
            self.initSize([1,1])
            self.setSize(size)
    
    def getSize(self): pass 
    def setSize(self, *size): pass
    def getA(self): pass        
    def setA(self, a): pass
    def getB(self): pass 
    def setB(self, b): pass

    def copy(self):
        kstore.scaleAnim(0)
        the_copy = self.__class__(self.size[0], shape=self)
        the_copy._updateShape()
        the_copy._draw()
        the_copy.show()
        kstore.unscaleAnim()

        return the_copy

    def _calculateNumSegments(self, a, b):
        if a == 0 or b == 0:
            return 0
        
        h = ((a - b) ** 2) / ((a + b) ** 2)
        circumference = math.pi * (a + b) * (1 + (3 * h) / (10 + math.sqrt(4 - 3 * h)))

        num_segments = min(100, max(12, int(circumference / 5)))
        
        return num_segments

    def _generateVertices(self):
        self._fillMode = GL_TRIANGLE_FAN
        num_segments = self._calculateNumSegments(*self._size)
        vertices = []
        for i in range(num_segments):
            theta = 2.0 * math.pi * i / num_segments  # Angle in radians
            x = self._size[0] * math.cos(theta)  # X coordinate
            y = self._size[1] * math.sin(theta)  # Y coordinate
            vertices.append([x, y])
        
        return vertices

    def generateVertices(self):
        num_segments = self._calculateNumSegments(*self.size)
        vertices = []
        for i in range(num_segments):
            theta = 2.0 * math.pi * i / num_segments  # Angle in radians
            x = self.size[0] * math.cos(theta)  # X coordinate
            y = self.size[1] * math.sin(theta)  # Y coordinate
            vertices.append([x, y])
        
        return vertices

    def contains(self, *point):
        x, y = toFloatList(point)

        if self._size[0] == 0 or self._size[1] == 0:
            return False 
        
        center_x = self.pos[0]
        center_y = self.pos[1]
        
        angle_rad = math.radians(self._rot)

        translated_x = x - center_x
        translated_y = y - center_y

        rotated_x = translated_x * math.cos(angle_rad) + translated_y * math.sin(angle_rad) + self._pivot[0] - self._size[0]
        rotated_y = -translated_x * math.sin(angle_rad) + translated_y * math.cos(angle_rad) + self._pivot[1] - self._size[1]

        return (rotated_x / self._size[0]) ** 2 + (rotated_y / self._size[1]) ** 2 <= 1

class kCircle(kEllipse):
    def __init__(self, radius, *args, shape=None):
        super().__init__(radius, radius, shape=shape)
        self.name = "kCircle"

    def _getRadius(self):
        return self._size[0]
    
    def _setRadius(self, radius):
        self._setSize([radius, radius])

    def getRadius(self):
        return self.size[0]

    def setRadius(self, radius):
        self.setSize([radius, radius])

class kRect(kShape):
    def __init__(self, *size, shape=None):
        super().__init__(shape)
        self.name = "kRect"
        size = toFloatList(size)
        self.getSize, self.setSize, self.getWidth, self.setWidth, self.getHeight, self.setHeight = kVec2(self, "size", size)

        if shape is None:
            self.initSize([1,1])
            kstore.scaleAnim(0.5)
            self.setWidth(size[0])
            self.setHeight(size[1])
            kstore.unscaleAnim()

    def getWidth(self): pass    
    def setWidth(self, width): pass
    def getHeight(self): pass
    def setHeight(self, height): pass
    def getSize(self): pass
    def setSize(self, *size): pass

    def copy(self):
        kstore.scaleAnim(0)
        the_copy = self.__class__(self.size, shape=self)
        the_copy._updateShape()
        the_copy._draw()
        the_copy.show()
        kstore.unscaleAnim()

        return the_copy

    def _generateVertices(self):
        self._fillMode = GL_TRIANGLE_FAN

        vertices = [
            [0,0],
            [self._size[0], 0],
            [self._size[0], self._size[1]],
            [0, self._size[1]],
        ]

        for vertex in vertices:
            vertex[0] -= self._size[0]/2
            vertex[1] -= self._size[1]/2

        return vertices

    def generateVertices(self):
        vertices = [
            [0,0],
            [self.size[0], 0],
            [self.size[0], self.size[1]],
            [0, self.size[1]],
        ]

        for vertex in vertices:
            vertex[0] -= self.size[0]/2
            vertex[1] -= self.size[1]/2

        return vertices
    
    def contains(self, *point):
        x, y = toFloatList(point)
        
        local_x = x - self._pos[0]
        local_y = y - self._pos[1]

        angle = math.radians(self._rot)  
        cos_theta = math.cos(angle)
        sin_theta = math.sin(angle)
        rotated_x = local_x * cos_theta + local_y * sin_theta + self._pivot[0]
        rotated_y = -local_x * sin_theta + local_y * cos_theta + self._pivot[1]

        return (0 <= rotated_x <= self._size[0]) and (0 <= rotated_y <= self._size[1])

class kRoundedRect(kShape):
    def __init__(self, width, height, radius, *args, shape=None):
        super().__init__(shape)
        self.name = "kRoundedRect"

        self.getSize, self.setSize, self.getWidth, self.setWidth, self.getHeight, self.setHeight = kVec2(self, "size", [width, height])
        self.getRadius, self.setRadius = kNumber(self, "radius", radius)

        if shape is None:
            self.initSize([1,1])
            self.setSize([width, height])

    def getWidth(self): pass
    def setWidth(self, width): pass
    def getHeight(self): pass
    def setHeight(self, height): pass
    def getSize(self): pass
    def setSize(self, *size): pass
    def getRadius(self): pass
    def setRadius(self, radius): pass

    def copy(self):
        kstore.scaleAnim(0)
        the_copy = self.__class__(self.size[0], self.size[1], self.radius, shape=self)
        the_copy._updateShape()
        the_copy._draw()
        the_copy.show()
        kstore.unscaleAnim(0)

        return the_copy
    
    def _setCircle(self, radius):
        radius = radius
        self._size[0] = 2*radius
        self._size[1]= 2*radius
        self._radius = radius
        self._updateShape()
        self._draw()

    def setCircle(self, radius):
        self.radius = radius
        action_queue.add(kInterpolator(radius, self._getRadius, self._setCircle))
    
    def _generateVertices(self):
        self._fillMode = GL_TRIANGLE_FAN

        vertices = []
        num_segments = 16

        radius = min(self._size[0]/2, self._size[1]/2, self._radius)
        corners = [
            (radius, radius), 
            (self._size[0] - radius, radius),
            (self._size[0] - radius, self._size[1] - radius), 
            (radius, self._size[1] - radius)
        ]

        angles = [
            (math.pi, 1.5 * math.pi), 
            (1.5 * math.pi, 2 * math.pi),  
            (0, 0.5 * math.pi),  
            (0.5 * math.pi, math.pi)  
        ]

        for i in range(4):
            cx, cy = corners[i]
            start_angle, end_angle = angles[i]
            for j in range(num_segments + 1):
                theta = start_angle + (end_angle - start_angle) * j / num_segments
                x = cx + radius * math.cos(theta)
                y = cy + radius * math.sin(theta)
                vertices.append([x, y])

            if i == 0:
                vertices.append([self._size[0] - radius, 0])
            elif i == 1:
                vertices.append([self._size[0], self._size[1] - radius])
            elif i == 2:
                vertices.append([radius, self._size[1]])
            elif i == 3:
                vertices.append([0, radius])
        
        for vertex in vertices:
            vertex[0] -= self._size[0]/2
            vertex[1] -= self._size[1]/2
        return vertices 
    
    def generateVertices(self):
        vertices = []
        num_segments = 20

        corners = [
            (self.radius, self.radius), 
            (self.size[0] - self.radius, self.radius),
            (self.size[0] - self.radius, self.size[1] - self.radius), 
            (self.radius, self.size[1] - self.radius)
        ]

        angles = [
            (math.pi, 1.5 * math.pi), 
            (1.5 * math.pi, 2 * math.pi),  
            (0, 0.5 * math.pi),  
            (0.5 * math.pi, math.pi)  
        ]

        for i in range(4):
            cx, cy = corners[i]
            start_angle, end_angle = angles[i]
            for j in range(num_segments + 1):
                theta = start_angle + (end_angle - start_angle) * j / num_segments
                x = cx + self.radius * math.cos(theta)
                y = cy + self.radius * math.sin(theta)
                vertices.append([x, y])

            if i == 0:
                vertices.append([self.size[0] - self.radius, 0])
            elif i == 1:
                vertices.append([self.size[0], self.size[1] - self.radius])
            elif i == 2:
                vertices.append([self.radius, self.size[1]])
            elif i == 3:
                vertices.append([0, self.radius])
        
        for vertex in vertices:
            vertex[0] -= self.size[0]/2
            vertex[1] -= self.size[1]/2
        return vertices 

    def contains(self, *point):
        x, y = toFloatList(point)
        
        # Translate the point to the local coordinate system
        local_x = x - self._pos[0]
        local_y = y - self._pos[1]

        # Convert rotation angle to radians
        angle = math.radians(-self._rot)
        cos_theta = math.cos(angle)
        sin_theta = math.sin(angle)

        # Translate the point relative to the pivot
        translated_x = local_x
        translated_y = local_y

        # Rotate the point around the pivot
        rotated_x = translated_x * cos_theta - translated_y * sin_theta + self._pivot[0]
        rotated_y = translated_x * sin_theta + translated_y * cos_theta + self._pivot[1]

        # Check if the point is within the shape's bounding box
        if (self._radius <= rotated_x <= self._size[0] - self._radius) and (0 <= rotated_y <= self._size[1]):
            return True
        if (0 <= rotated_x <= self._size[0]) and (self._radius <= rotated_y <= self._size[1] - self._radius):
            return True

        # Check if the point is within the rounded corners
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

class kImage(kShape):
    def __init__(self, file_name, width):
        super().__init__()
        self.name = "kImage"
        self.file_name = file_name

        try:
            self.image = imageio.imread(file_name)
            self.image = self.image[::-1, :, :]  # Flip the image vertically
            if self.image.shape[2] == 4:
                self.image_format = GL_RGBA
            else:
                self.image_format = GL_RGB
            self.image_data = self.image.tobytes()
        except Exception:
            print("Image not found in workspace folder", file_name)

        height = int(self.image.shape[0] * (width / self.image.shape[1]))
        self.texture_id = None

        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, self.image_format, self.image.shape[1], self.image.shape[0], 0, self.image_format, GL_UNSIGNED_BYTE, self.image_data)
        glBindTexture(GL_TEXTURE_2D, 0)

        self.getSize, self.setSize, self.getWidth, self.setWidth, self.getHeight, self.setHeight = kVec2(self, "size", [width, height])

        if True:
            self.initSize([1,1])
            self.setSize([width, height])

    def getWidth(self): pass    
    def setWidth(self, width): pass
    def getHeight(self): pass
    def setHeight(self, height): pass

    def copy(self):
        kstore.scaleAnim(0)
        the_copy = self.__class__(self.file_name, self.width, shape=self)
        the_copy._updateShape()
        the_copy._draw()
        the_copy.show()
        kstore.unscaleAnim()

        return the_copy

    def _generateVertices(self):
        self._fillMode = GL_TRIANGLE_FAN

        vertices = [
            [0, 0],
            [self._size[0], 0],
            [self._size[0], self._size[1]],
            [0, self._size[1]]
        ]

        for vertex in vertices:
            vertex[0] -= self._size[0]/2
            vertex[1] -= self._size[1]/2

        return vertices

    def generateVertices(self):
        vertices = [
            [0, 0],
            [self.size[0], 0],
            [self.size[0], self.size[1]],
            [0, self.size[1]]
        ]

        for vertex in vertices:
            vertex[0] -= self.size[0]/2
            vertex[1] -= self.size[1]/2

        return vertices
    
    def _draw(self):
        if not self._ready:
            return 
        
        if self._idGL is not None:
            glDeleteLists(self._idGL, 1)
            self._idGL = None

        idGL = glGenLists(1)
        glNewList(idGL, GL_COMPILE)
        glPushMatrix()

        glTranslatef(self._pos[0], self._pos[1], 0)
        glTranslatef(self._pivot[0], self._pivot[1], 0)
        glRotatef(self._rot, 0, 0, 1)
        glTranslatef(-self._pivot[0], -self._pivot[1], 0)

        if self._fill:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.texture_id)

            glBegin(GL_TRIANGLE_FAN)
            glTexCoord2f(0.0, 0.0)
            glVertex2f(self._vertices[0][0], self._vertices[0][1])
            glTexCoord2f(1.0, 0.0)
            glVertex2f(self._vertices[1][0], self._vertices[1][1])
            glTexCoord2f(1.0, 1.0)
            glVertex2f(self._vertices[2][0], self._vertices[2][1])
            glTexCoord2f(0.0, 1.0)
            glVertex2f(self._vertices[3][0], self._vertices[3][1])
            glEnd()

            glDisable(GL_TEXTURE_2D)

        if self._line:
            glColor4ub(*list([int(c) for c in self._lineColor]))
            glBegin(GL_LINE_LOOP)
            for vertex in self._vertices:
                glVertex2f(vertex[0], vertex[1])
            glEnd()

        glPopMatrix()
        glEndList()

        self._idGL = idGL

    def contains(self, *point):
        x, y = toFloatList(point)
        
        local_x = x - self._pos[0]
        local_y = y - self._pos[1]

        angle = math.radians(self._rot)  
        cos_theta = math.cos(angle)
        sin_theta = math.sin(angle)
        rotated_x = local_x * cos_theta + local_y * sin_theta + self._pivot[0]
        rotated_y = -local_x * sin_theta + local_y * cos_theta + self._pivot[1]

        return (0 <= rotated_x <= self._size[0]) and (0 <= rotated_y <= self._size[1])
    
    
class kTriangle(kShape):
    def __init__(self, length, *args, shape=None):
        super().__init__(shape)
        self.name = "kTriangle"

        self.getLength, self.setLength = kNumber(self, "length", length)

        if shape is None:
            self.initLength(1)
            self.setLength(length)

    def getLength(self): pass
    def setLength(self, length): pass

    def getHeight(self):
        return (math.sqrt(3) / 2) * self.length

    def copy(self):
        kstore.scaleAnim(0)
        the_copy = self.__class__(self.length, shape=self)
        the_copy._updateShape()
        the_copy._draw()
        the_copy.show()
        kstore.unscaleAnim()

        return the_copy

    def _generateVertices(self):
        self._fillMode = GL_TRIANGLE_FAN
        height = (math.sqrt(3) / 2) * self._length

        vertices = [
            [0, 0],  
            [self._length, 0],  
            [self._length / 2, height], 
        ]

        for vertex in self.vertices:
            vertex[0] -= self._size[0]/2
            vertex[1] -= self._size[1]/2

        for vertex in vertices:
            vertex[0] -= self._length/2
            
        return vertices

    def generateVertices(self):
        height = (math.sqrt(3) / 2) * self.length

        vertices = [
            [0, 0],  
            [self.length, 0],  
            [self.length / 2, height], 
        ]

        for vertex in vertices:
            vertex[0] -= self.length/2

        return vertices

    def contains(self, *point):
        x, y = toFloatList(point)
        
        local_x = x - self._pos[0]
        local_y = y - self._pos[1]

        angle = math.radians(self._rot)
        cos_theta = math.cos(angle)
        sin_theta = math.sin(angle)
        rotated_x = local_x * cos_theta + local_y * sin_theta + self._pivot[0]
        rotated_y = -local_x * sin_theta + local_y * cos_theta + self._pivot[1]

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
        kstore.scaleAnim(0)
        super().__init__(12)
        self.name = "kCursor"

        shape_buffer.remove(self)

        self._line = True
        self._line_width = 2
        kstore.unscaleAnim()
    
    def _generateVertices(self):
        self._fillMode = GL_TRIANGLE_FAN
        half_side = self._length // 3
        height = self._length
        vertices = [
            [0, -half_side],
            [height, 0],
            [0, half_side],
            [0, -half_side]
        ]
        return vertices

    def generateVertices(self):
        half_side = self.length // 3
        height = self.length
        vertices = [
            [0, -half_side],
            [height, 0],
            [0, half_side],
            [0, -half_side]
        ]
        return vertices

class kArc(kShape):
    def __init__(self, radius, angle, *args, shape=None):
        super().__init__(shape)
        self.name = "kArc"

        self.getRadius, self.setRadius = kNumber(self, "radius", radius)
        self.getAngle, self.setAngle = kNumber(self, "angle", angle)


        if shape is None:
            self.initAngle(1)
            self.setAngle(angle)


    def getRadius(self): pass
    def setRadius(self, radius): pass
    def getAngle(self): pass
    def setAngle(self, angle): pass

    def copy(self):
        kstore.scaleAnim(0)
        the_copy = self.__class__(self.radius, self.angle, shape=self)
        the_copy._updateShape()
        the_copy._draw()
        the_copy.show()
        kstore.unscaleAnim()
        
        return the_copy
    
    
    def _calculateNumSegments(self, radius, angle):
        if radius == 0:
            return 1
        
        circumference = 2*math.pi*radius

        num_segments = min(100, max(12, int(circumference / 5*angle/360)))
        
        return num_segments
    
    def _generateVertices(self):
        self._fillMode = GL_TRIANGLE_FAN
        vertices = [[0,0]]
        num_segments = self._calculateNumSegments(self._radius, self._angle)

        angle_step = self._angle/180*math.pi / num_segments

        for i in range(num_segments+1):
            theta = angle_step * i
            x = self._radius * math.cos(theta)
            y = self._radius * math.sin(theta)
            vertices.append([x, y])

        return vertices

    def generateVertices(self):
        vertices = [[0,0]]
        num_segments = self._calculateNumSegments(self.radius, self.angle)

        angle_step = self.angle/180*math.pi / num_segments

        for i in range(num_segments+1):
            theta = angle_step * i
            x = self.radius * math.cos(theta)
            y = self.radius * math.sin(theta)
            vertices.append([x, y])

        return vertices

    def contains(self, *point):
        x, y = toFloatList(point)
        
        local_x = x - self._pos[0]
        local_y = y - self._pos[1]

        rot_radians = math.radians(self._rot)
        cos_theta = math.cos(rot_radians)
        sin_theta = math.sin(rot_radians)
        rotated_x = local_x * cos_theta + local_y * sin_theta+self._pivot[0] - self._radius
        rotated_y = -local_x * sin_theta + local_y * cos_theta+self._pivot[1]- self._radius

        distance_squared = rotated_x ** 2 + rotated_y ** 2
        if distance_squared > self._radius ** 2:
            return False

        point_angle = math.degrees(math.atan2(rotated_y, rotated_x))
        return 0 <= point_angle <= self._angle

class kLine(kShape):
    def __init__(self, *size, shape=None):
        super().__init__(shape) 
        self.name = "kLine"

        size = toFloatList(size)       
        self.getSize, self.setSize, self.getWidth, self.setWidth, self.getHeight, self.setHeight = kVec2(self, "size", size)

        if shape is None:
            length = math.sqrt(size[0]**2 + size[1]**2)

            if length == 0:
                x,y = [0,0]
            else:
                x,y = size[0]/length, size[1]/length

            self.initSize([x,y])
            self.setLength(length)

    def getWidth(self): pass
    def setWidth(self, width): pass
    def getHeight(self): pass
    def setHeight(self, height): pass
    def getSize(self): pass
    def setSize(self, *size): pass

    def copy(self):
        kstore.scaleAnim(0)
        the_copy = self.__class__(self.size, shape=self)
        the_copy._updateShape()
        the_copy._draw()
        the_copy.show()
        kstore.unscaleAnim()
        return the_copy

    def setLength(self, length):
        width = self.getWidth()
        height = self.getHeight()
        current_length = (width**2 + height**2)**0.5
        if current_length == 0:
            return 
        
        self.setSize(width*length/current_length, height*length/current_length)
    
    # def setAngle(self, angle):
    #     width = self.getWidth()
    #     height = self.getHeight()
    #     current_length = (width**2 + height**2)**0.5

    #     if current_length == 0:
    #         return 
        
    #     angle = angle/180*math.pi
    #     x = math.cos(angle)*current_length
    #     y = math.sin(angle)*current_length
    #     self.setSize(x,y)

    def _generateVertices(self):
        self._fillMode = GL_TRIANGLE_FAN
        vertices = []

        half_lineWidth = self._lineWidth / 2
        dx = self._size[0]
        dy = self._size[1]
        length = math.sqrt(dx**2 + dy**2)
        angle_rad = math.atan2(dy, dx) 

        unrotated_vertices = [
            [0, -half_lineWidth],  
            [length, -half_lineWidth], 
            [length, half_lineWidth],  
            [0, half_lineWidth],  
            [0, -half_lineWidth] 
        ]

        for vertex in unrotated_vertices:
            x, y = vertex
            rotated_x = x * math.cos(angle_rad) - y * math.sin(angle_rad)
            rotated_y = x * math.sin(angle_rad) + y * math.cos(angle_rad)
            vertices.append([rotated_x, rotated_y])
        self._fill = True
        self._line = False 
        return vertices 
    
    def generateVertices(self):
        vertices = []

        half_lineWidth = self.lineWidth / 2
        dx = self.size[0]
        dy = self.size[1]
        length = math.sqrt(dx**2 + dy**2)
        angle_rad = math.atan2(dy, dx) 

        unrotated_vertices = [
            [0, -half_lineWidth],  
            [length, -half_lineWidth], 
            [length, half_lineWidth],  
            [0, half_lineWidth],  
            [0, -half_lineWidth] 
        ]

        for vertex in unrotated_vertices:
            x, y = vertex
            rotated_x = x * math.cos(angle_rad) - y * math.sin(angle_rad)
            rotated_y = x * math.sin(angle_rad) + y * math.cos(angle_rad)
            vertices.append([rotated_x, rotated_y])
        self.fill = True
        self.line = False 
        return vertices 

    def contains(self, x, y):
        return False

class kPolygon(kShape):
    def __init__(self, vertices, *args, shape=None):
        super().__init__(shape)
        self.name = "kPolygon"
        self.vertices = copy.deepcopy(vertices)
        self._vertices = copy.deepcopy(vertices)

        if shape is None:
            self._setVertices([])
            length = len(vertices)
            if length > 0:
                kstore.scaleAnim(1/length)
                for i in range(1,len(vertices)):
                    self.setVertices(copy.deepcopy(vertices[:i+1]))
                kstore.unscaleAnim()
            self.vertices = copy.deepcopy(vertices)

    def copy(self):
        kstore.scaleAnim()
        the_copy = self.__class__(self.vertices, shape=self)
        the_copy._updateShape()
        the_copy._draw()
        the_copy.show()
        kstore.unscaleAnim()
        return the_copy
    
    def _generateVertices(self):
        self._fillMode = GL_TRIANGLES
        return copy.deepcopy(self._vertices)

    def generateVertices(self):
        return copy.deepcopy(self.vertices)

    def addVertex(self, *vertex):
        vertex = toFloatList(vertex)
        vertices = self.generateVertices()
        vertices.append(vertex)  
        self.setVertices(vertices)

    def contains(self, *point):
        x, y = toFloatList(point)
        
        local_x = x - self._pos[0]
        local_y = y - self._pos[1]
      
        angle = math.radians(self._rot)
        cos_theta = math.cos(angle)
        sin_theta = math.sin(angle)

        rotated_x = local_x * cos_theta + local_y * sin_theta + self._pivot[0]
        rotated_y = -local_x * sin_theta + local_y * cos_theta + self._pivot[1]

        n = len(self._vertices)
        inside = False
        p1x, p1y = self._vertices[0]
        for i in range(n + 1):
            p2x, p2y = self._vertices[i % n]
            if rotated_y > min(p1y, p2y):
                if rotated_y <= max(p1y, p2y):
                    if rotated_x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (rotated_y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or rotated_x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside
    
class kVector(kLine):
    def __init__(self, width, height, *args, shape=None):
        super().__init__(width, height, shape=shape)
        self.name = "kVector"

    def copy(self):
        kstore.scaleAnim(0)
        the_copy = self.__class__(self.width, self.height, shape=self)
        the_copy._updateShape()
        the_copy._draw()
        the_copy.show()
        kstore.unscaleAnim()

        return the_copy
    
    def _generateVertices(self):
        arrowhead_length = self._lineWidth * 6 
        arrowhead_width = self._lineWidth * 2
        half_lineWidth = self._lineWidth / 2

        dx = self._size[0]
        dy = self._size[1]
        length = math.sqrt(dx**2 + dy**2)
        angle_rad = math.atan2(dy, dx) 

        unrotated_vertices = [
            [0, -half_lineWidth],  
            [max(1, length-arrowhead_length), - half_lineWidth],
            [max(1, length-arrowhead_length), - half_lineWidth - arrowhead_width],
            [max(arrowhead_length, length), 0],
            [max(1, length - arrowhead_length), half_lineWidth + arrowhead_width], 
            [max(1, length - arrowhead_length), half_lineWidth],  
            [0, half_lineWidth],
        ]

        vertices = []
        for vertex in unrotated_vertices:
            x, y = vertex
            rotated_x = x * math.cos(angle_rad) - y * math.sin(angle_rad)
            rotated_y = x * math.sin(angle_rad) + y * math.cos(angle_rad)
            vertices.append([rotated_x, rotated_y])

        self._fill = True
        self._line = False 
        self._fillMode = GL_TRIANGLES

        return vertices
    
    def generateVertices(self):
        arrowhead_length = self.lineWidth * 6 
        arrowhead_width = self.lineWidth * 2
        half_lineWidth = self.lineWidth / 2

        dx = self.size[0]
        dy = self.size[1]
        length = math.sqrt(dx**2 + dy**2)
        angle_rad = math.atan2(dy, dx) 

        unrotated_vertices = [
            [0, -half_lineWidth],  
            [max(1, length-arrowhead_length), - half_lineWidth],
            [max(1, length-arrowhead_length), - half_lineWidth - arrowhead_width],
            [max(arrowhead_length, length), 0],
            [max(1, length - arrowhead_length), half_lineWidth + arrowhead_width], 
            [max(1, length - arrowhead_length), half_lineWidth],  
            [0, half_lineWidth],
        ]

        vertices = []
        for vertex in unrotated_vertices:
            x, y = vertex
            rotated_x = x * math.cos(angle_rad) - y * math.sin(angle_rad)
            rotated_y = x * math.sin(angle_rad) + y * math.cos(angle_rad)
            vertices.append([rotated_x, rotated_y])

        self.fill = True
        self.line = False 

        return vertices

class kUIElement:
    def __init__(self, scale):
        width = 200
        height = 50
        radius = 5

        self.name = "kUIElement"
        self.id = kShape.counter
        kShape.counter += 1

        self._pixmap = None 

        self.getReady, self.setReady = kValue(self, "ready", False)
        self.getSize, self.setSize, self.getWidth, self.setWidth, self.getHeight, self.setHeight = kVec2(self, "size", [width, height])
        self.getRadius, self.setRadius = kNumber(self, "radius", radius)

        self.getRot, self.setRot = kNumber(self, "rot", kstore.rot)
        self.getLineWidth, self.setLineWidth = kNumber(self, "lineWidth", kstore.lineWidth)

        self.getPos, self.setPos, self.getX, self.setX, self.getY, self.setY = kVec2(self, "pos", kstore.pos, update=False)

        self.getPivot, self.setPivot, self.getPivotX, self.setPivotX, self.getPivotY, self.setPivotY = kVec2(self, "pivot", [0,0], update=False)

        self.getFillColor, self.setFillColor = kColor(self, "fillColor", kstore.fillColor, update=False)
        self.getLineColor, self.setLineColor = kColor(self, "lineColor", kstore.lineColor, update=False)

        self.getFill, self.setFill = kValue(self, "fill", kstore.fill, update=False)
        self.getLine, self.setLine = kValue(self, "line", kstore.line, update=False)

        self.getOnClick, self.setOnClick = kValue(self, "onClick", None, update=False)
        self.getOnRelease, self.setOnRelease = kValue(self, "onRelease", None, update=False)
        self.getOnMouseEnter, self.setOnMouseEnter = kValue(self, "onMouseEnter", None, update=False)
        self.getOnMouseExit, self.setOnMouseExit = kValue(self, "onMouseExit", None, update=False)

        passiveColor = list([int(0.2*c) for c in kstore.fillColor])
        passiveColor[3] = 255

        hoverColor = list([int(0.4*c) for c in kstore.fillColor])
        hoverColor[3] = 255

        focusColor = list([int(0.6*c) for c in kstore.fillColor])
        focusColor[3] = 255

        self.passiveColor, self.setPassiveColor = kColor(self, "passiveColor", passiveColor)
        self.getHoverColor, self.setHoverColor = kColor(self, "hoverColor", hoverColor)
        self.getFocusColor, self.setFocusColor = kColor(self, "focusColor", focusColor)
        self.initFillColor(self._passiveColor)

        self._mouse_over = False 

        ui_buffer.append(self)

        self.setReady(True)
        if scale:
            self.initSize([1,1])

            kstore.scaleAnim(0.5)
            self.setWidth(width)
            self.setHeight(height)
            kstore.unscaleAnim()
    
    def getWidth(self): pass
    def setWidth(self, width): pass
    def getHeight(self): pass
    def setHeight(self, height): pass
    def getSize(self): pass
    def setSize(self, *size): pass
    def getRadius(self): pass
    def setRadius(self, radius): pass

    def getName(self):
        return self.name + " (" + str(self.id) + ")"
    
    def print(self, *message):
        print("{:<15}".format(self.name) + "(" + str(self.id) + ") >           " , *message)

    def _updateShape(self): 
        the_max = max(abs(self._size[0]), abs(self._size[1]))
        the_max = int(the_max)
        self._pixmap = QPixmap(2*the_max, 2*the_max)
        self._pixmap.fill(Qt.transparent)

        if not self._ready:
            return 

        if self._size[0] == 0 or self._size[1] == 0:
            return

        painter = QPainter(self._pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        if self._fill:
            painter.setBrush(QBrush(QColor(*self._fillColor), Qt.SolidPattern))
        else:
            painter.setBrush(Qt.NoBrush)
        
        if self._line:
            painter.setPen(QPen(QColor(*self._lineColor), self._lineWidth, Qt.SolidLine))
        else:
            painter.setPen(Qt.NoPen)

        transform = QTransform()
        transform.translate(the_max, the_max)
        transform.rotate(-self._rot)
        transform.translate(-the_max, -the_max)
        painter.setTransform(transform)
        painter.drawRoundedRect(
            QRectF(
                the_max - self._size[0]/2,
                the_max - self._size[1]/2,
                self._size[0],
                self._size[1]
            ),
            float(self._radius),
            float(self._radius)
        )
        painter.end()

    def _draw(self):
        pass
        
    def contains(self, *point):
        x, y = toFloatList(point)
        
        # Translate the point to the local coordinate system
        local_x = x - self._pos[0]
        local_y = y - self._pos[1]

        # Convert rotation angle to radians
        angle = math.radians(-self._rot)
        cos_theta = math.cos(angle)
        sin_theta = math.sin(angle)

        # Translate the point relative to the pivot
        translated_x = local_x 
        translated_y = local_y

        # Rotate the point around the pivot
        rotated_x = translated_x * cos_theta - translated_y * sin_theta + self._pivot[0] + self._size[0]/2
        rotated_y = translated_x * sin_theta + translated_y * cos_theta + self._pivot[1] + self._size[1]/2

        # Check if the point is within the shape's bounding box
        if (self._radius <= rotated_x <= self._size[0] - self._radius) and (0 <= rotated_y <= self._size[1]):
            return True
        if (0 <= rotated_x <= self._size[0]) and (self._radius <= rotated_y <= self._size[1] - self._radius):
            return True

        # Check if the point is within the rounded corners
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
    
class kLabel(kUIElement):
    def __init__(self, label="", text="", scale=True):
        super().__init__(scale)
        self.name = "kLabel"

        self.getLabel, self.setLabel = kValue(self, "label", "")
        self.getPadding, self.setPadding = kNumber(self, "padding", 5)
        self.getAlignX, self.setAlignX = kValue(self, "alignX", "left")
        self.getAlignY, self.setAlignY = kValue(self, "alignY", "center")
        self.getOverflow, self.setOverflow = kValue(self, "overflow", "wrap")
        self.getText, self.setText = kValue(self, "text", "")
        self.getFontSize, self.setFontSize = kNumber(self, "fontSize", kstore.fontSize)
        self.getFontColor, self.setFontColor = kColor(self, "fontColor", kstore.fontColor)

        self.initLine(True)
        
        kstore.scaleAnim(0)
        self.setText(text)
        self.setLabel(label)
        kstore.unscaleAnim()

    def getLabel(self): pass
    def setLabel(self, label): pass
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

    def _updateShape(self):
        super()._updateShape()
        self._drawText()
        if len(self._label) > 0:
            self._draw_label()
    
    def _drawText(self):
        the_max = max(self._size[0], self._size[1])
        the_max = int(the_max)

        painter = QPainter(self._pixmap)
        painter.setPen(QColor(*[int(c) for c in self._fontColor]))
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        transform = QTransform()
        transform.translate(the_max, the_max)
        transform.rotate(-self._rot)
        transform.translate(-the_max, -the_max)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setTransform(transform)

        font = QFont()
        font.setPointSize(int(self._fontSize))
        font.setHintingPreference(QFont.PreferFullHinting)

        painter.setFont(font)
        self._font_metrics = QFontMetrics(font)
        
        text_rect = QRect(the_max+int(self._padding - self._size[0]/2), the_max+int(self._padding - self._size[1]/2), int(self._size[0])-2*int(self._padding), int(self._size[1])-2*int(self._padding))

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
        if self._overflow == "clip" or self._overflow == "visible":
            painter.drawText(text_rect, h_align | v_align, the_text)
        elif self._overflow == "wrap":
            wrapped_text = "\n".join(self._wrapText(the_text, text_rect.width()))
            painter.drawText(text_rect, h_align | v_align, wrapped_text)
        
        painter.end()

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

    def _draw_label(self):
        if self._label == "":
            return 
        
        the_max = max(self._size[0], self._size[1])
        the_max = int(the_max)
        
        painter = QPainter(self._pixmap)
        painter.setPen(QColor(*[int(c) for c in self._fontColor]))

        transform = QTransform()
        transform.translate(the_max, the_max)
        transform.rotate(-self._rot)
        transform.translate(-the_max, -the_max)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setTransform(transform)

        font = QFont()
        font.setPointSize(int(self._fontSize*0.7))
        font.setWeight(QFont.Bold)  # Set the font weight to bold
        painter.setFont(font)
        font_metrics = QFontMetrics(font)

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        painter.setPen(QColor(*self._lineColor))
        painter.setBrush(QColor(*self._passiveColor))

        the_label = "  " + self._label + "  "
        the_max = max(self._size[0], self._size[1])

        width = font_metrics.width(the_label)
        height = font_metrics.height()

        x = the_max + self._radius + self._padding - self._size[0]/2
        y = the_max - height/2 - self._size[1]/2
        
        rect = QRect(int(x), int(y), int(width), int(height))
        
        painter.drawRoundedRect(rect, 5, 5)
        painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, the_label)
        painter.end()

class kText(kLabel):
    def __init__(self, text, *args, shape=None):
        kstore.scaleAnim(0)
        super().__init__("", text, False)
        self.name = "kText"
        kstore.unscaleAnim()

        self.initAlignX("center")
        self.initAlignY("center")
        self.initOverflow("visible")
        self.initFill(False)
        self.initLine(False)
        self.initSize([1000, 1000])

class kButton(kLabel):
    def __init__(self, text, handler):
        super().__init__("", text)
        self.name = "kButton"

        self.getHandler, self.setHandler = kValue(self, "handler", handler)

        self.initLine(True)
        self.initOnClick(self._onUIClick)
        self.initOnRelease(self._onUIRelease)
        self.initOnMouseEnter(self._onUIMouseEnter)
        self.initOnMouseExit(self._onUIMouseExit)
        self.initFocusColor(kstore.fillColor)
        self.initAlignX("center")
        self.initAlignY("center")

        self.initRadius(25)

    def getHandler(self): pass
    def setHandler(self, handler): pass

    def _onUIClick(self, x, y, button):
        self._fillColor = self._focusColor
        self._handler()
        self._updateShape()

    def _onUIRelease(self, x, y, button):
        if self.contains(x,y):
            self._onUIMouseEnter()
        else:
            self._onUIMouseExit()

    def _onUIMouseEnter(self):
        self._fillColor = self._hoverColor
        self._updateShape()

    def _onUIMouseExit(self):
        self._fillColor = self._passiveColor
        self._updateShape()

class kInput(kLabel):
    def __init__(self, label, handler=None):
        super().__init__(label, "")
        self.name = "kInput"

        self.getHandler, self.setHandler = kValue(self, "handler", handler)
        self.initOverflow("clip")
        self.initLine(True)
        self.initOnClick(self._onUIClick)
        self.initOnRelease(self._onUIRelease)
        self.initOnMouseEnter(self._onUIMouseEnter)
        self.initOnMouseExit(self._onUIMouseExit)

        self._focused = False 
        self._cursor_position = len(self._text)
        self._cursor_visible = True

        self._blink_timer = QTimer()
        self._blink_timer.timeout.connect(self._toggle_cursor_visibility)
        self._blink_timer.start(500)

    def getHandler(self): pass
    def setHandler(self, handler): pass
    def getLabel(self): pass
    def setLabel(self, label): pass 
    
    def _onUIClick(self, x, y, button):
        self._focused = True
        self._fillColor = self._focusColor
        self._cursor_position = len(self._text)
        self._updateShape()

    def _onUIMouseEnter(self):
        if not self._focused:
            self._fillColor = self._hoverColor
            self._updateShape()

    def _onUIMouseExit(self):
        if not self._focused:
            self._fillColor = self._passiveColor
            self._updateShape()

    def _toggle_cursor_visibility(self):
        self._cursor_visible = not self._cursor_visible
        if self._ready:
            self._updateShape()

    def _onUIRelease(self, x, y, button):
        if not self.contains(x,y):
            self._focused = False
            self._fillColor = self._passiveColor
            self._updateShape()

    def _emit(self):
        if self._handler:
            self._handler(self._text)
        
        self._focused = False 
        self._fillColor = self._passiveColor
        self._updateShape()

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
                    self.text = self._text
            elif key == Qt.Key_Delete:
                if self._cursor_position < len(self._text):
                    self._text = self._text[:self._cursor_position] + self._text[self._cursor_position + 1:]
                    self._setText(self._text)
                    self.text = self._text
            elif key == Qt.Key_Left:
                if self._cursor_position > 0:
                    self._cursor_position -= 1
                    self._cursor_visible = True
                    self._updateShape()
            elif key == Qt.Key_Right:
                if self._cursor_position < len(self._text):
                    self._cursor_position += 1
                    self._updateShape()
            else:  
                new_text = self._text[:self._cursor_position] + event.text() + self._text[self._cursor_position:]
                if self._overflow == "clip":
                    if self._font_metrics.width(new_text) <= self._size[0] - 2 * self._padding:
                        self.text = new_text
                        self._cursor_position += 1
                        self._setText(new_text)
                        self.text = self._text
                elif self._overflow == "visible":
                    self.text = new_text 
                    self._cursor_position += 1
                    self._setText(new_text)
                    self.text = self._text 
                elif self._overflow == "wrap":
                    lines = self._wrapText(new_text, self._size[0] - 2*self._padding)
                    if len(lines)*self._font_metrics.height() < self._size[1] - 2*self._padding:
                        self.text = new_text
                        self._cursor_position += 1
                        self._setText(new_text)
                        self.text = self._text

    def _updateShape(self):
        super()._updateShape()

        if self._focused and self._cursor_visible:
            self._draw_cursor()
            
    def _getCursorXY(self, lines, font_metrics):
        line = 0
        delta = self._cursor_position
        width = 0

        while delta > 0:
            if line >= len(lines):
                delta = 0
                width = font_metrics.width(lines[-1])
                line -= 1
            elif len(lines[line]) < delta:
                delta -= len(lines[line])
                line += 1
            else:
                width = font_metrics.width(lines[line][:delta])
                delta = 0

        # Horizontal alignment with padding
        if self._alignX == "left":
            x = self._padding + width
        elif self._alignX == "center":
            x = (self._size[0] - font_metrics.width(lines[line])) // 2 + width
        elif self._alignX == "right":
            x = self._size[0] - font_metrics.width(lines[line]) - self._padding + width
        else:
            x = self._padding + width 

        # Vertical alignment with padding
        if self._alignY == "top":
            y = self._padding + line * font_metrics.height()
        elif self._alignY == "center":
            y = (self._size[1] - max(len(lines),1) * font_metrics.height()) // 2 + line * font_metrics.height()
        elif self._alignY == "bottom":
            y = self._size[1] - max(len(lines), 1) * font_metrics.height() - self._padding + line * font_metrics.height()
        else:
            y = self._padding + line * font_metrics.height()

        return x, y

    def _draw_cursor(self):
        if self._cursor_visible:
            the_max = max(self._size[0], self._size[1])
            the_max = int(the_max)

            painter = QPainter(self._pixmap)
            painter.setPen(QColor(*[int(c) for c in self._fontColor]))

            transform = QTransform()
            transform.translate(the_max, the_max)
            transform.rotate(-self._rot)
            transform.translate(-the_max, -the_max)
            painter.setTransform(transform)

            font = QFont()
            font.setPointSize(int(self._fontSize))
            painter.setFont(font)
            font_metrics = QFontMetrics(font)
                    
            if self._overflow == "clip" or self._overflow == "visible":
                cursor_x, cursor_y = self._getCursorXY([self._text], font_metrics)
                cursor_x = min(cursor_x, self._size[0] - self._padding)
            elif self._overflow == "wrap":
                left_text = self._text
                lines = self._wrapText(left_text, self._size[0] - 2 * self._padding)
                cursor_x, cursor_y = self._getCursorXY(lines, font_metrics)
            
            painter.setPen(QColor(*[int(c) for c in self._fontColor]))
            cursor_x += the_max + 2-self._size[0]/2
            cursor_y = cursor_y + the_max - self._size[1]/2
            painter.drawLine(int(cursor_x), int(cursor_y), int(cursor_x), int(cursor_y + font_metrics.height()))
            painter.end()

class kList(kShape):
    def __init__(self, the_list, width, height, *args, shape=None):
        super().__init__(shape)
        self.name = "kList"

        self.getSize, self.setSize, self.getWidth, self.setWidth, self.getHeight, self.setHeight = kVec2(self, "size", [width, height])
        self.getList, self.setList = kVecN(self, "list", the_list)

    def getSize(self): pass 
    def setSize(self, *size): pass 
    def getWidth(self): pass 
    def setWidth(self, width): pass
    def getHeight(self): pass
    def setHeight(self, height): pass 
    def getList(self): pass 
    def setList(self, the_list): pass

    def _generateVBO(self):
        self._triangles = copy.deepcopy(self._vertices)
        self._vbo = -1

        flattened_triangles = [coord for vertex in self._triangles for coord in vertex]
        triangle_data = struct.pack(f'{len(flattened_triangles)}f', *flattened_triangles)

        if self._vbo_triangle is not None:
            glDeleteBuffers(1, [self._vbo_triangle])
            self._vbo_triangle = None 
        
        self._vbo_triangle = glGenBuffers(1)

        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_triangle)
        glBufferData(GL_ARRAY_BUFFER, len(triangle_data), triangle_data, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def copy(self):
        kstore.scaleAnim(0)
        the_copy = kList(self.list, self.width, self.height, shape=self)
        the_copy._updateShape()
        the_copy._draw()
        the_copy.show()
        kstore.unscaleAnim(0)

        return the_copy

    def _generateRect(self, x, y, width, height):
        rect = [
            [x,y],
            [x+width, y],
            [x+width, y+height],
            [x+width, y+height],
            [x, y+height],
            [x,y]
        ]

        return rect 
    
    def _generateVertices(self):
        self._fillMode = GL_TRIANGLES
        
        length = len(self._list)

        x = 0
        y = 0
        width = self._size[0]/length
        threshold = 2
        if width >= threshold:
            dx  = width - 1
        else:
            dx = width

        the_max = max(self.list)
        the_min = min(self.list)

        factor = self._size[1]/(the_max + abs(the_min))

        vertices = []

        for i in range(len(self._list)):
            dy = self._list[i]*factor
            rect = self._generateRect(x,y+abs(the_min*factor),dx,dy)
            x += dx
            if width >= threshold:
                x += 1
            vertices.extend(rect)
        
        for vertex in vertices:
            vertex[0] -= self._size[0]/2
            vertex[1] -= self._size[1]/2

        return vertices
    
    def generateVertices(self):
        return copy.deepcopy(self._list)

    def contains(self, *point):
        x, y = toFloatList(point)
        
        local_x = x - self._pos[0]
        local_y = y - self._pos[1]

        angle = math.radians(self._rot)  
        cos_theta = math.cos(angle)
        sin_theta = math.sin(angle)
        rotated_x = local_x * cos_theta + local_y * sin_theta + self._pivot[0]
        rotated_y = -local_x * sin_theta + local_y * cos_theta + self._pivot[1]

        return (0 <= rotated_x <= self._size[0]) and (0 <= rotated_y <= self._size[1])
        
class kGrid:
    def __init__(self, window, width, height, scale_factor):
        self._size = [int(width*scale_factor),int( height*scale_factor)]
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

    def resize(self, width, height, scale_factor):
        self._scale_factor = scale_factor
        self._size[0] = int(width*scale_factor)
        self._size[1] = int(height*scale_factor)
        self.clear()

    def clear(self):
        self._pixmap = QPixmap(self._size[0], self._size[1])
        self._pixmap.fill(Qt.transparent)

        if len(self._xlabels) > 0:
            for label in self._xlabels:
                label.deleteLater()
            for label in self._ylabels:
                label.deleteLater()

            self._xlabels = []
            self._ylabels = []

        if self._xlabel is not None:
            self._xlabel.deleteLater()
            self._xlabel = None 
        
        if self._ylabel is not None:
            self._ylabel.deleteLater()
            self._ylabel = None 

        self._createLabels()
        self._drawLines()
        
    def _createLabels(self):
        if not kstore.show_grid:
            return 
            
        for x in range(100, int(self._size[0]), 100):
            label = QLabel(str(x), self._window)
            label.setStyleSheet(f"color: rgb(200, 200, 200); font-size: {int(self._label_fontSize/self._scale_factor)}px;")
            label.move(int(x/self._scale_factor)+10, int(self._size[1]/self._scale_factor - 30))
            label.show()
            self._xlabels.append(label)

        for y in range(0, int(self._size[1]), 100):
            label = QLabel(str(y), self._window)
            label.setStyleSheet(f"color: rgb(200, 200, 200); font-size: {int(self._label_fontSize/self._scale_factor)}px;")
            label.move(int(10), int((self._size[1]/self._scale_factor - y/self._scale_factor) - 30))
            label.show()
            self._ylabels.append(label)

        self._xlabel = QLabel("x", self._window)
        self._xlabel.setStyleSheet(f"color: rgb(200, 200, 200); font-size: {int(self._label_fontSize/self._scale_factor)}px;")
        self._xlabel.move(int((self._size[0]/self._scale_factor - 20)), int((self._size[1]/self._scale_factor - 40) ))
        self._xlabel.show()

        self._ylabel = QLabel("y", self._window)
        self._ylabel.setStyleSheet(f"color: rgb(200, 200, 200); font-size: {int(self._label_fontSize/self._scale_factor)}px;")
        self._ylabel.move(int(20), 0)
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

def debugCallback(*args, **kwargs):
    print('args = {0}, kwargs = {1}'.format(args, kwargs))

class kMainWindow(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("ksbanim drawing surface")
        self.setWindowFlags(Qt.FramelessWindowHint)

        self.initFps()

        self.scale_factor = kstore.scale_factor 
        
        kstore.elapsed_timer = QElapsedTimer()
        kstore.grid = kGrid(self, kstore.size[0], kstore.size[1], kstore.scale_factor)

        self.record = False 
        self.frames = []

        self.key_store = set()
        self.button_store = set()
        self.setMouseTracking(True)
        self.mouse_pos = [0,0]

        kstore.cursor = kCursor()
        kstore.cursor._draw()

        self.closeButton = QPushButton("x", self)
        self.closeButton.setFixedSize(30, 30)
        self.closeButton.setStyleSheet("""
            QPushButton {
                background-color: #CC0000;
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #FF0000;
                font-weight: bolder;
            }
        """)        
        self.closeButton.clicked.connect(self.close)
        self.closeButton.setFocusPolicy(Qt.NoFocus)
        self.closeButton.show()

        self.setSize(kstore.size[0], kstore.size[1], kstore.scale_factor)

        format = QSurfaceFormat()
        format.setSamples(4)
        format.setAlphaBufferSize(8)  # Request an 8-bit alpha channel
        self.setFormat(format)

        self.center()
    
    def initFps(self):
        self.fps_buffer = []
        self.fps_label = QLabel(self)
        self.fps_label.setStyleSheet("color: white; background-color: black; font-size: 16px;")
        self.fps_label.resize(100, 30)
        self.fps_label.setText("fps --")
        self.fps_label.show()

    def updateFps(self):
        current_time = kstore.elapsed_timer.elapsed()
        
        if len(self.fps_buffer) > 59:
            self.fps_buffer.append(current_time)
            self.fps_buffer.pop(0)
            
            fps = 1000*len(self.fps_buffer)/(self.fps_buffer[-1] - self.fps_buffer[0])

            self.fps_label.setText(f"fps {fps:.0f}")
        else:
            self.fps_buffer.append(current_time)

    def activateAntialiasing(self):
        format = QSurfaceFormat()
        context = QOpenGLContext.currentContext()
        format.setSamples(4)
        format.setAlphaBufferSize(8)  # Request an 8-bit alpha channel
        context.setFormat(format)

    def initializeGL(self):
        self.activateAntialiasing()
        self.context().format().setSwapInterval(1)

        # self.enableDebugOutput()
        glShadeModel(GL_FLAT)
        glEnable(GL_POLYGON_SMOOTH)
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_MULTISAMPLE)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        if kstore.color_mixing == "additive":
            glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        else:
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.resizeGL(int(kstore.size[0]//2), int(kstore.size[1]//2))
        self.setBackgroundColorGL(kstore.backgroundColor)

    def enableDebugOutput(self):
        glEnable(GL_DEBUG_OUTPUT)
        glDebugMessageCallback(GLDEBUGPROC(debugCallback), None)

    def setBackgroundColorGL(self, color):
        glClearColor(*[c/255 for c in color])

    def customPaintGL(self):
        glShadeModel(GL_FLAT)
        glEnable(GL_POLYGON_SMOOTH)
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_MULTISAMPLE)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        if kstore.color_mixing == "additive":
            glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        else:
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.clearGL()
        glLoadIdentity()
        glTranslated(0, 0, 0)
        for shape in shape_buffer:
            if shape._drawGL is not None:
                shape._drawGL()

        if kstore.cursor:
            kstore.cursor._drawGL()

    
    def clearGL(self):
        glClearColor(*kstore.backgroundColor)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glLoadIdentity()
        glTranslated(0, 0, 0)
        
    def resizeGL(self, width, height): 
        glMatrixMode(GL_PROJECTION)   
        glLoadIdentity()
        glOrtho(0, kstore.size[0], 0, kstore.size[1], -10, 10)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        framebuffer_id = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, framebuffer_id)

        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texture_id, 0)

    def setSize(self, width, height, scale_factor):
        width = int(width)
        height = int(height)

        self.resize(width, height)
        self.setGeometry(0, 0, width,height)        
        self.center()
        self.pixmap = QPixmap(int(kstore.size[0]), int(kstore.size[1]))
        self.pixmap.fill(QColor(*kstore.backgroundColor))
        self.fps_label.move(width - 100, 0)
        self.closeButton.move(width-30, 0)

        if kstore.grid is not None:
            kstore.grid.resize(width, height, scale_factor)

        self.center()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def drawGrid(self, painter):
        if kstore.show_grid:              
            painter.drawPixmap(0, 0, kstore.grid._pixmap)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.beginNativePainting()
        glPushAttrib(GL_ALL_ATTRIB_BITS)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()

        self.customPaintGL()

        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glPopAttrib()
        painter.endNativePainting()

        painter.resetTransform()
        transform = QTransform()
        transform.scale(1/kstore.scale_factor, 1/kstore.scale_factor)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setTransform(transform)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        self.drawGrid(painter)
        
        for ui_element in ui_buffer:
            if ui_element._ready:
                painter.drawPixmap(
                    int(ui_element._pos[0] - ui_element._pixmap.width() // 2),
                    int(kstore.size[1] - ui_element._pos[1] - ui_element._pixmap.height() / 2),
                    ui_element._pixmap.scaled(ui_element._pixmap.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
        painter.resetTransform()
        self.updateFps()

        if self.record:
            the_time = kstore.elapsed_timer.elapsed()
            if len(self.frames) > 0:
                old_time = self.frames[-1][1]
            else:
                old_time = 0 
            
            dt = the_time - old_time 
            if dt > 10:
                self.frames.append((self.captureFrame(), the_time/1000))

    def setRecord(self, value):
        self.record = value

    def captureFrame(self):
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(self.winId())

        return screenshot.toImage()

    def saveAsPng(self, filename):
        screenshot = self.captureFrame()
        screenshot.save(filename + ".png", 'png')
        print(f" > png saved")

    def saveAsGif(self, file_name):
        temp_folder = "temp_screenshots"
        os.makedirs(temp_folder, exist_ok=True)

        def save_frames():
            total_time = (self.frames[-1][1] - self.frames[0][1])
            print(f" > begin saving GIF ({len(self.frames)} frames, duration {round(total_time * 10) / 10} s) - please keep the program running")

            dts = []
            images = []
            accumulated_duration = 0

            for i, (frame, duration) in enumerate(self.frames):
                if i < len(self.frames) - 1:
                    next_duration = self.frames[i + 1][1] - self.frames[i][1]
                    if next_duration + accumulated_duration < 0.02:
                        accumulated_duration += next_duration
                    else:
                        buffer = QBuffer()
                        buffer.open(QBuffer.ReadWrite)
                        frame.save(buffer, 'PNG')
                        buffer.seek(0)
                        images.append(imageio.imread(buffer.data().data()))
                        dts.append(next_duration + accumulated_duration)
                        accumulated_duration = 0
                else:
                    buffer = QBuffer()
                    buffer.open(QBuffer.ReadWrite)
                    frame.save(buffer, 'PNG')
                    buffer.seek(0)
                    images.append(imageio.imread(buffer.data().data()))
                    dts.append(kstore.dt/1000 + accumulated_duration)

            dts = [dt*1000 for dt in dts]
            imageio.mimsave(file_name + ".gif", images, quantizer='nq', duration=dts)
            print(" > GIF saved")

        threading.Thread(target=save_frames).start()

    def saveAsMp4(self, file_name):
        temp_folder = "temp_screenshots"
        os.makedirs(temp_folder, exist_ok=True)

        def save_frames():
            total_time = (self.frames[-1][1] - self.frames[0][1])
            print(f" > begin saving MP4 ({len(self.frames)} frames, duration {round(total_time * 10) / 10} s) - please keep the program running")

            dts = []
            images = []

            for i, (frame, duration) in enumerate(self.frames):
                buffer = QBuffer()
                buffer.open(QBuffer.ReadWrite)
                frame.save(buffer, 'PNG')
                buffer.seek(0)
                images.append(imageio.imread(buffer.data().data()))
                if i == len(self.frames) - 1:
                    dts.append(kstore.dt/1000)
                else:
                    dts.append(self.frames[i + 1][1] - self.frames[i][1])

            # Calculate the frame rate based on the average duration
            average_duration = sum(dts) / len(dts)
            fps = 1 / average_duration if average_duration > 0 else 30

            writer = imageio.get_writer(file_name + ".mp4", fps=fps, codec='libx264')

            for i, image in enumerate(images):
                duration = dts[i] if i < len(dts) else average_duration
                num_frames = int(round(duration * fps))
                for _ in range(num_frames):
                    writer.append_data(image)

            writer.close()
            print(" > MP4 saved")


        threading.Thread(target=save_frames).start()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        
        key_text = event.text()
        for ui_element in ui_buffer:
            if hasattr(ui_element, "_keyPressEvent"):
                ui_element._keyPressEvent(event)

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

        for ui_element in ui_buffer:
            if ui_element._onClick and ui_element.contains(*pos):
                ui_element._onClick(*pos, button_text)

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

        for ui_element in ui_buffer:
            if ui_element._onRelease:
                ui_element._onRelease(*pos, button_text)

        self.button_store.remove(button_text)
        for handler in on_mouse_pressed_handlers:
            if handler[1] == button_text:
                pos = event.pos()
                handler[0](*self.translateMousePos(*pos), button_text)

    def translateMousePos(self, pos):
        x = pos[0]
        y = pos[1]
        return [int(x*kstore.scale_factor), int(kstore.size[1] - y*kstore.scale_factor)]
    
    def mouseMoveEvent(self, event):    
        pos = event.pos()
        pos = self.translateMousePos([pos.x(), pos.y()])
        self.mouse_pos = pos 
        
        for ui_element in ui_buffer:
            if not ui_element._onMouseEnter and not ui_element._onMouseExit:
                continue 
            
            contains = ui_element.contains(*pos)

            if contains and not ui_element._mouse_over:
                ui_element._mouse_over = True 
                if ui_element._onMouseEnter:
                    ui_element._onMouseEnter()
            elif not contains and ui_element._mouse_over:
                ui_element._mouse_over = False 
                if ui_element._onMouseExit:
                    ui_element._onMouseExit()

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
            handler[0](*pos)

    def isButtonPressed(self, button):
        return button in self.button_store
    
    def getMousePos(self):
        return self.mouse_pos
    
def exception_hook(exctype, value, tb):
    tb_info = traceback.extract_tb(tb)
    for frame in tb_info:
        filename, lineno, funcname, text = frame
        lineno_str = f"{lineno}".ljust(10)
        funcname_str = f"{funcname}".ljust(20)
        print(f"line {lineno_str} {funcname_str} >>> {text}")    
    print(f"Exception: {exctype}, Value: {value}")
    sys.exit(1)

# ==================================== LIST SAMPLES ===========================================

def _getSample(name):
    if name == "colors1":
        the_list = []
        for r in range(0,255,50):
            for g in range(0,255,50):
                for b in range(0,255,50):
                    the_list.append([r,g,b])
    elif name == "colors2":
        the_list = []
        for x in range(0,kstore.size[0], 1):
            x = math.exp(-x/300)*255
            y = math.sin(x*30/kstore.size[0])*math.exp(-x/300)*255
            z = math.cos(x*30/kstore.size[0])*math.exp(-x/300)*255
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
        for x in range(0,kstore.size[0], 1):
            y = math.sin(x*30/kstore.size[0])*math.exp(-x/300)*kstore.size[0]//2 + kstore.size[0]//2
            the_list.append([x,y])
    elif name == "coords2":
        the_list = []
        for i in range(10):
            x = random.randint(0,kstore.size[0])
            y = random.randint(0,kstore.size[1])
            the_list.append([x,y])
    elif name == "coords3":
        the_list = []
        for x in range(0,kstore.size[0], 1):
            y = math.sin(x*20/kstore.size[1])*300 - x/2 + 100*(random.random()-0.5) + kstore.size[1]//2-100
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
        for r in range(0,kstore.size[1]//2):
            h = r%50*5
            the_list.append([kstore.size[0]//2-r,h])
    elif name == "strings1":
        the_list = ["Alice", "Bob", "Charlie", "Danita", "Erich", "Frederica", "Gian", "Hanna", "Ibn", "Jasmin", "Kevin", "Lisa", "Manuel", "Nora", "Oskar", "Petra", "Qasim", "Rihanna", "Sandro", "Theres", "Ulrich", "Vivienne", "Walter", "Xenia", "Yannes", "Zora"]
    elif name == "int1":
        the_list = list([random.randint(1,100) for x in range(0,100)])
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

# ==================================== PUBLIC INTERFACE ===========================================

__all__ = ['createWindow', 'showGrid', 'hideGrid', 'maximizeWindow', 'setWindowWidth', 'setWindowHeight', 'getWindowWidth', 'getWindowHeight', 'setWindowSize', 'getWindowSize', 'run', 'drawEllipse', 'drawCircle', 'drawRect', 'drawLine', 'drawLineTo', 'drawVector', 'drawVectorTo', 'drawTriangle', 'drawRoundedRect', 'drawArc', 'drawPoly', 'setAnim', 'setDelay', 'setTime', 'getAnim', 'getDelay', 'delay', 'setPos', 'getPos', 'getX', 'setX', 'setY', 'getY', 'setRot', 'getRot', 'move', 'forward', 'backward', 'left', 'right', 'up', 'down', 'rotate', 'penDown', 'penUp', 'setLine', 'getLine', 'setFill', 'getFill', 'setColorMixing', 'getColorMixing', 'setColor', 'getColor', 'setFillColor', 'getFillColor', 'setLineColor', 'getLineColor', 'setBackgroundColor', 'getBackgroundColor', 'setLineWidth', 'getLineWidth', 'saveAsPng', 'onTick', 'removeOnTick', 'setFrameTick', 'getTick', 'setFps', 'getFps', 'onKeyPressed', 'removeOnKeyPressed', 'onKeyReleased', 'removeOnKeyReleased', 'onMousePressed', 'removeOnMousePressed', 'onMouseReleased', 'removeOnMouseReleased', 'onMouseMoved', 'removeOnMouseMoved', 'isKeyPressed', 'isMousePressed', 'getMousePos', 'getMouseX', 'getMouseY', 'drawInput', 'drawLabel', 'drawText', 'drawButton', 'setFontSize', 'getFontSize', 'setFontColor', 'getFontColor', 'setAnimationType', 'showCursor', 'hideCursor', 'clear', "getListSample", "beginRecording", "endRecording", "saveAsGif", "saveAsMp4", "drawImage", "getRainbow", "drawList"]

def createWindow(width=1000, height=1000):
    """
    Create the main drawing window with optional width, height.

    **default size**
    - 0 <= x <= 1000 from left to right
    - 0 <= y <= 1000 from bottom to top

    **examples**
    - createWindow()
    - createWindow(800,800)
    """
    sys.excepthook = exception_hook

    kstore.app = QApplication(sys.argv)
    kstore.window = kMainWindow()

    kstore.window.show()
    initWindowSize()

    action_queue.add(kMessage(" > begin drawing"))

    kstore.main_timer = QTimer()
    kstore.main_timer.timeout.connect(lambda: action_queue.process())
    kstore.main_timer.timeout.connect(lambda: kstore.window.update())
    kstore.main_timer.start(kstore.dt)  # Process the queue every 100 ms

    kstore.elapsed_timer.start()

def _grid(value):
    kstore.show_grid = value 
    kstore.grid.clear()

def showGrid():
    """
        shows a 100x100 coordinate grid
    """
    action_queue.add(kSetter(_grid, True))

def hideGrid():
    """
        hides the coordinate grid
    """
    action_queue.add(kSetter(_grid, False))

def maximizeWindow():
    """
        maximize to screen size
    """
    screen = QDesktopWidget().availableGeometry()
    setWindowSize(screen.width(), screen.height())

def setWindowWidth(width):
    """
        set window width (x) in pixel
    """
    setWindowSize(width, getWindowHeight())

def getWindowWidth():
    """
        get window widht (x) in pixel
    """
    return kstore.window.width() 

def setWindowHeight(height):
    """
        set window height (y) in pixel
    """
    setWindowSize(getWindowWidth(), height)

def getWindowHeight():
    """
        get window height(y) in pixel
    """
    return kstore.window.height() 

def initWindowSize():
    screen = QDesktopWidget().availableGeometry()
    max_height = screen.height()
    max_width = screen.width()
    
    temp_dock = QDockWidget()
    dock_height = temp_dock.sizeHint().height()
    max_height -= dock_height

    size = int(0.9*min(max_width, max_height))
    
    kstore.size[0] = 1000
    kstore.size[1] = 1000
    kstore.scale_factor = 1000/size

    kstore.window.setSize(size, size, kstore.scale_factor)

def setWindowSize(*size):
    """
        set window size (x,y) in pixel

        **examples**
        - setWindowSize(1000, 1000)
        - setWindowSize([1000,1000]) *as a list*
    """
    size = toFloatList(size)
    width = size[0]
    height = size[1]

    screen = QDesktopWidget().availableGeometry()
    max_height = screen.height()
    max_width = screen.width()
    
    temp_dock = QDockWidget()
    dock_height = temp_dock.sizeHint().height()
    max_height -= dock_height

    window_width = min(width, max_width)
    window_height = min(height, max_height)
    
    kstore.size[0] = window_width
    kstore.size[1] = window_height
    kstore.scale_factor = max(width / window_width, height / max_height)

    kstore.window.setSize(kstore.size[0], kstore.size[1], kstore.scale_factor)

def getWindowSize(*size):
    """
        returns window size as a list [x,y] in pixel
    """
    return [kstore.window.width(), kstore.window.height()]

def run():
    """
        needs to be the last function call of your script
    """
    action_queue.add(kMessage(" > end drawing"))
    kstore.elapsed_timer.start()
    sys.exit(kstore.app.exec_())

def drawEllipse(a, b):
    """
        draws an ellipse with half-axis a (x) and b (y)

        **example**
        - drawEllipse(100, 200)
    """
    ellipse = kEllipse(a, b)
    ellipse._updateShape()
    ellipse._draw()
    return ellipse 

def drawCircle(radius):
    """
        draws a circle with a given radius 

        **example**
        - drawCircle(500)
    """
    circle = kCircle(radius)
    circle._updateShape()
    circle._draw()
    return circle

def drawRect(width, height):
    """
        draws a rectangle with a given width (x) and height (y)

        **example**
        - drawRect(100, 400)
    """
    rect = kRect(width, height)
    rect._updateShape()
    rect._draw()
    return rect

def drawImage(file_name, width):
    """
        draws an image (saved under file_name in the current working directory) with a given width (x)

        the height is calculated automatically upon the image dimensions

        **example**
        - drawImage("cat.png", 500)
    """
    image = kImage(file_name, width)
    image._updateShape()
    image._draw()
    return image

def drawLine(*size):
    """
        draws a line of a certain size (width, height) or with a given length

        **Examples**
        - Draw a line of length 100 with angle 45:
        
            setRot(45)
            drawLine(100) 

        - Draw a line with x-distance 100 and y-distance 300:
        
            drawLine(100, 300)
    """
    if not isinstance(size[0], (list,tuple)) and len(size) == 1:
        size = [size[0], 0]

    size = toFloatList(size)
    line = kLine(size)
    line._updateShape()
    line._draw()
    return line

def drawLineTo(*point):
    """
        draws a line from the cursor position to a certain point (ignores rotation)

        **Examples**
        - drawLineTo(600,600)
        - drawLineTo([600,600])
    """

    point = toFloatList(point)
    old_rot = getRot()
    setRot(0)
    dx = point[0] - kstore.getX()
    dy = point[1] - kstore.getY()
    
    line = drawLine(dx, dy)

    setRot(old_rot)
    return line 

def drawVector(*size):
    """
        draws a vector (with arrowhead) of a certain size (width, height) or with a given length

        **Examples**
        - Draw a vector of length 100 with angle 45:
        
            setRot(45)
            drawVector(100) 

        - Draw a vector with x-distance 100 and y-distance 300:
        
            drawVector(100, 300)
    """
    if not isinstance(size[0], (list,tuple)) and len(size) == 1:
        size = [size[0], 0]

    size = toFloatList(size)

    vector = kVector(size)
    vector._updateShape()
    vector._draw()
    return vector

def drawVectorTo(*point):
    """
        draws a line from the cursor position to a certain point (ignores rotation)

        **Examples**
        - drawLineTo(600,600)
        - drawLineTo([600,600])
    """

    point = toFloatList(point)
    old_rot = getRot()
    setRot(0)
    dx = point[0] - kstore.getX()
    dy = point[1] - kstore.getY()
    
    vector = drawVector(dx, dy)

    setRot(old_rot)
    return vector 

def drawTriangle(length):
    """
        draws an equilateral triangle with a given side length

        **example**

        - drawTriangle(100)
    """
    triangle = kTriangle(length)
    triangle._updateShape()
    triangle._draw()
    return triangle

def drawRoundedRect(width, height, radius=20):
    """
        draws a rectangle with a given width (x) and height (y) with rounded corners (radius)

        **example**
        - drawRoundedRect(100, 400, 20)
    """
    rect = kRoundedRect(width, height, radius)
    rect._updateShape()
    rect._draw()
    return rect

def drawArc(radius, angle):
    """
        draws an arc (circle sector) with a given radius and a given opening angle 

        - angle is in degrees
        - 0 degrees points to the right 
        - positive angles are drawn counter clockwise

        **example**
        - drawArc(100, 45)
    """
    arc = kArc(radius, angle)
    arc._updateShape()
    arc._draw()
    return arc 

def drawPoly(vertices):
    """
        draws a polygon consisting of a given list of vertices (points) [x,y]

        **important**

        the vertex coordinates are calculated relative to the **current cursor pos** (setPos)

        **example**
        - drawPoly([[100,100], [300,100], [300,300]])
    """
    polygon = kPolygon(vertices)
    polygon._updateShape()
    polygon._draw()
    return polygon

def setAnim(milliseconds):
    """
        define how long a drawing animation takes in milliseconds (default 250 ms)
    """
    kstore.animation = milliseconds

def setDelay(milliseconds):
    """
        define how the delay between each drawing animation should take in milliseconds (default 250 ms)
    """
    kstore.delay = milliseconds

def setTime(milliseconds):
    """
        define how the delay and animation time for each drawing animation should take in milliseconds (default 250 ms animation and 250 ms delay)

        shorthand for setAnim(milliseconds) and setDelay(milliseconds)

        **example**

        - setTime(10)
    """
    setAnim(milliseconds)
    setDelay(milliseconds)

def getAnim():
    """
        get the animation time in milliseconds (how long it takes, to complete an animation)
    """
    return kstore.animation

def getDelay():
    """
        get the delay time in milliseconds (how long the gap between each animation is)
    """
    return kstore.delay

def delay(milliseconds):
    """
        add an extra delay before the next animation (in milliseconds)
    """
    kstore.milliseconds += milliseconds

def setPos(*point):
    """
        set the position of the drawing cursor 

        - x from left to right 
        - y from bottom to top 

        **example**
        - setPos(400,400)
        - setPos([400, 400]) *as a list*
    """
    pos = toFloatList(point)
    kstore.setPos(pos)

def getPos():
    """
        get the position of the drawing cursor as a list [x,y]

        - x from left to right 
        - y from bottom to top 
    """
    return kstore.getPos() 

def setX(x):
    """
        set x-coordinate of the of the drawing cursor position (x from left to right)
    """
    kstore.setX(x)

def getX():
    """
        get x-coordinate of the drawing cursor position (x from left to right)
    """
    return kstore.getX()

def setY(y):
    """
        set y-coordinate of the of the drawing cursor position (y from bottom to top)
    """
    kstore.setY(y)

def getY():
    """
        get y-coordinate of the drawing cursor position (y from bottom to top)
    """
    return kstore.getY()

def move(*distance):
    """
        move the drawing cursor a certain position in x and y direction 

        **examples**
        - move(100, 400)
        - move([100,400]) *as a list*
    """
    delta = toFloatList(distance)
    pos = kstore.getPos()
    pos[0] += delta[0]
    pos[1] += delta[1]

    kstore.setPos(pos)

def forward(distance):
    """
        move the drawing cursor a certain distance forward at the direction it is currently facing (rotation)
    """
    angle = kstore.getRot()*math.pi/180
    dx = math.cos(angle)*distance
    dy = math.sin(angle)*distance
    setPos(getX() + dx, getY() + dy)

def backward(distance):
    """
        move the drawing cursor a certain distance backward at the direction it is currently facing (rotation)
    """
    angle = kstore.getRot()*math.pi/180
    dx = math.cos(angle)*distance
    dy = math.sin(angle)*distance
    setPos(getX() - dx, getY() - dy)

def penDown():
    """
        when the cursor is moved: draw a line 
    """
    kstore.setPen(True)

def penUp():
    """
        when the cursor is moved, no line is drawn 
    """
    kstore.setPen(False)

def left(distance):
    """
        move the drawing cursor a certain distance to the left (negative x)
    """
    setPos(getX() - distance, getY())

def right(distance):
    """
        move the drawing cursor a certain distance to the right (positive x)
    """
    setPos(getX() + distance, getY())


def down(distance):
    """
        move the drawing cursor a certain distance downwards (negative y)
    """
    setPos(getX(), getY() - distance)

def up(distance):
    """
        move the drawing cursor a certain distance upwards (positive y)
    """
    setPos(getX(), getY() + distance)

def rotate(angle):
    """
        rotate the cursor (angle in degrees)
         
        - positive angles: counterclockwise
        - negative angles: clockwise
    """
    angle = angle
    old_angle = kstore.getRot()
    new_angle = old_angle + angle 
    kstore.setRot(new_angle)

def setRot(angle):
    """
        set rotation angle in degrees 
        
        - 0 degrees points to the right
        - positive angles: clockwise
        - negative angles: clockwise

        **example**
        - setRot(60)
    """

    kstore.setRot(angle)

def getRot():
    """
        get current rotation angle in degrees

        - 0 degrees points to the right
        - positive angles: clockwise
        - negative angles: clockwise
    """
    return kstore.getRot()

def setLine(value):
    """
        define, whether the shape borders are drawn (expects value *True* or *False*)

        **examples**
        - setLine(True)
        - setLine(False)
    """
    kstore.line = value 

def getLine():
    """
        check, if the shape borders are drawn (returns *True* or *False*)
    """
    return kstore.line 

def setFill(value):
    """
        define, whether the shapes are drawn with filling (expects value *True* or *False*)

        **examples**
        - setFill(True)
        - setFill(False)
    """
    kstore.fill = value 

def getFill():
    """
        check, if the shapes are drawn with filling (returns *True* or *False*)
    """
    return kstore.fill 

def setColorMixing(mixer):
    """
        set the color mixing (for transparent shapes) to "additive" or "subtractive"
    """
    kstore.color_mixing = mixer 

def getColorMixing():
    """
        get the current color mixing (default "additive")
    """
    return kstore.color_mixing

def setColor(*rgba):
    """
        set the current fill and line color in rgba 
        
        - rgb = red, green, blue
        - a stands for alpha (transparency)
        - each value is between 0 and 255

        **examples**
        - setColor(255,0,0)
        - setColor(255,0,0, 100) *with alpha (transparency)*
        - setColor([255,0,0]) *as a list*
        - setColor([255,0,0,100]) *as a list (including alpha)*
    """
    kstore.setColor(*rgba)

def getColor():
    """
        returns the current fill color as a list [r,g,b,a] 

        - rgb = red, green, blue
        - a stands for alpha (transparency)
        - each value is between 0 and 255
    """
    return kstore.getColor()

def getRainbow(pieces):
    """
        returns a rainbow object, made of a certain amount of pieces

        the next rainbow color can be retrieved by next()

        **example**

        rainbow = getRainbow(255)
        
        setColor(rainbow.next())
    """
    rainbow = kRainbow(pieces)
    return rainbow 

def setFillColor(*rgba):
    """
        set the current fill color rgba

        - rgb = red, green, blue
        - a stands for alpha (transparency)
        - each value is between 0 and 255

        **examples**
        - setFillColor(255,0,0)
        - setFillColor(255,0,0, 100) *with alpha (transparency)*
        - setFillColor([255,0,0]) *as a list*
        - setFillColor([255,0,0,100]) *as a list (including alpha)*
    """
    kstore.setFillColor(*rgba)

def getFillColor():
    """
        returns the current fill color as a list [r,g,b,a] 

        - rgb = red, green, blue
        - a stands for alpha (transparency)
        - each value is between 0 and 255
    """
    return kstore.getFillColor()

def setLineColor(*rgba):
    """
        set the current line color in rgba

        - rgb = red, green, blue
        - a stands for alpha (transparency)
        - each value is between 0 and 255

        **examples**
        - setLineColor(255,0,0)
        - setLineColor(255,0,0, 100) *with alpha (transparency)*
        - setLineColor([255,0,0]) *as a list*
        - setLineColor([255,0,0,100]) *as a list (including alpha)*
    """
    kstore.setLineColor(*rgba)

def getLineColor():
    """
        returns the current line color as a list [r,g,b,a] 

        - rgb = red, green, blue
        - a stands for alpha (transparency)
        - each value is between 0 and 255
    """
    return kstore.getLineColor()

def setBackgroundColor(*rgba):
    """
        set the current window background color in rgba

        - rgb = red, green, blue
        - a stands for alpha (transparency)
        - each value is between 0 and 255

        **examples**
        - setBackgroundColor(255,0,0)
        - setBackgroundColor(255,0,0, 100) *with alpha (transparency)*
        - setBackgroundColor([255,0,0]) *as a list*
        - setBackgroundColor([255,0,0,100]) *as a list (including alpha)*
    """
    kstore.backgroundColor = toColor(rgba)

def getBackgroundColor():
    """
        returns the current background color as a list [r,g,b,a] 

        - rgb = red, green, blue
        - a stands for alpha (transparency)
        - each value is between 0 and 255
    """
    return kstore.backgroundColor

def setLineWidth(value):
    """
        set line width (for borders and lines) in pixel

        **example**
        - setLineWidth(2)
    """
    kstore.lineWidth = value 

def getLineWidth():
    """
        returns line width (for borders and lines) in pixel
    """
    return kstore.lineWidth 

def setFrameTick(milliseconds):
    """
        set the main timer tick in milliseconds (time between two frames)

        if the drawing operation can't keep up, the real tick (time between two frames) might be larger
    """
    kstore.dt = milliseconds
    if kstore.timer is not None:
        kstore.timer.setInterval(milliseconds)

def getTick():
    """
        returns the main timer tick in milliseconds
    """
    return kstore.dt


def setFps(fps):
    """
        set the main timer fps in frames per second

        if the drawing operation can't keep up, the real tick (time between two frames) might be larger
    """
    setFrameTick(1000/fps)

def getFps(fps):
    """
        returns the main timer fps in frames per second 
    """

    return 1000/kstore.dt

def onTick(tick_function, milliseconds=20):
    """
        executes tick_function at a regular interval (milliseconds)

        - milliseconds must be at least 20
        - if the drawing operation can't keep up, the real tick might be larger
        - it is recommended to disable animations with setTime(0)

        **example**

        def loop():
            move(1,1)
            drawCircle(5)

        setTime(0)
        onTick(loop, 10) *# draws one circle every 100 ms*
    """

    kstore.immediate = True
    kstore.scaleAnim(0)
    action_queue.add(kLoop(tick_function, max(20, milliseconds)))
    kstore.unscaleAnim()
    kstore.immediate = False
    
def removeOnTick(tick_function):
    """
        removes the tick function
    """
    i = 0
    while i < len(action_queue):
        action = action_queue[i]
        if action.loop_function == tick_function:
            action_queue.pop(i)
        else:
            i = i + 1
    

on_key_pressed_handlers = []
on_key_released_handlers = []
on_mouse_pressed_handlers = []
on_mouse_released_handlers = []
on_mouse_moved_handlers = []

def onKeyPressed(handler_function, key=None):
    """
        executes the handler_function(key) if a the key is pressed
        
        - the handler_function excpects a single argument *key* (a string)
        - if no key (as string) is given, the function is executed any every key press

        **examples**

        onKeyPressed(print) *# executes on every key press*
        onKeyPressed(print, "a") *# only executes if a was pressed*
    """
    def submit(the_key):
        kstore.immediate = True
        if key is not None and the_key == key:                  
            handler_function(the_key)
        elif key is None:
            handler_function(the_key)
        kstore.immediate = False

    on_key_pressed_handlers.append((submit, key, handler_function))

def removeOnKeyPressed(handler_function):
    """
        removes the key press handler
    """
    target = on_key_pressed_handlers
    i = 0
    while i < len(target):
        if target[i][2] == handler_function:
            target.pop(i)
        else:
            i += 1

def onKeyReleased(handler_function, key=None):
    """
        executes the handler_function(key) if a the key is released
        
        - the handler_function excpects a single argument *key* (a string)
        - if no key (as string) is given, the function is executed on any key release

        **examples**

        onKeyReleased(print) *# executes on every key release*
        onKeyReleased(print, "a") *# only executes if a was released*
    """
    def submit(the_key):
        kstore.immediate = True
        if key is not None and the_key == key:                  
            handler_function(the_key)
        elif key is None:
            handler_function(the_key)
        kstore.immediate = False 

    on_key_released_handlers.append((submit, key, handler_function))

    return submit


def removeOnKeyReleased(handler_function):
    """
        removes the key release handler
    """
    target = on_key_released_handlers
    i = 0
    while i < len(target):
        if target[i][2] == handler_function:
            target.pop(i)
        else:
            i += 1

    
def onMousePressed(handler_function, button):
    """
        executes the handler_function(key) if a mouse button is pressed
        
        - the handler_function excpects three arguments x, y and *button* (a string)
        - button is either "left", "middle" or "right"
        - if no button is given, the function is executed on any button press

        **examples**

        def button_press(x,y,button):
            print(x, y, button)

        onButtonPressed(button_press) *# executes on every button press*
        onButtonPressed(button_press, "left") *# only executes if the left button was pressed*
    """
    def submit(x, y, the_button):
        kstore.immediate = True
        if button is not None and the_button == button:                  
            handler_function(x, y, the_button)
        elif button is None:
            handler_function(x, y, the_button)
        kstore.immediate = False 

    on_mouse_pressed_handlers.append((submit, button , handler_function))

def removeOnMousePressed(handler_function):
    """
        removes the key press handler
    """
    target = on_mouse_pressed_handlers
    i = 0
    while i < len(target):
        if target[i][2] == handler_function:
            target.pop(i)
        else:
            i += 1

    
def onMouseReleased(handler_function, button):
    """
        executes the handler_function(key) if a mouse button is released
        
        - the handler_function excpects three arguments x, y and *button* (a string)
        - button is either "left", "middle" or "right"
        - if no button is given, the function is executed on any button release

        **examples**

        def button_release(x,y,button):
            print(x, y, button)

        onButtonReleased(button_release) *# executes on every button release*
        onButtonReleased(button_release, "left") *# only executes if the left button was released*
    """
    def submit(x, y, the_button):
        kstore.immediate = True 
        if button is not None and the_button == button:                  
            handler_function(x,y, the_button)
        elif button is None:
            handler_function(x, y, the_button)
        kstore.immediate = False 

    on_mouse_released_handlers.append((submit, button, handler_function))
    return submit

def removeOnMouseReleased(handler_function):
    """
        removes the key press handler
    """
    target = on_mouse_released_handlers
    i = 0
    while i < len(target):
        if target[i][2] == handler_function:
            target.pop(i)
        else:
            i += 1

def onMouseMoved(handler_function):
    """
        executes the handler_function(x,y) if a the mouse has moved
        
        - the handler_function excpects a two arguments *x* and *y*

        **examples**

        def handler(x,y):
            print(x,y)
        onMouseMoved(handler) 
    """

    def submit(x,y):
        kstore.immediate = True 
        handler_function(x,y)
        kstore.immediate = False 

    on_mouse_moved_handlers.append((submit, handler_function))

def removeOnMouseMoved(handler_function):
    """
        removes the mouse move handler
    """
    target = on_mouse_moved_handlers
    i = 0
    while i < len(target):
        if target[i][1] == handler_function:
            target.pop(i)
        else:
            i += 1

def isKeyPressed(key):
    """
        returns *True* if the key (a string) is pressed, and *False* else
    """
    return kstore.window.isKeyPressed(key)

def isMousePressed(button):
    """
        returns *True* if the mouse button (string "left", "middle" or "right") is pressed, and *False* else
    """
    return kstore.window.isButtonPressed(button)

def getMousePos():
    """
        returns the mouse position as a list [x,y]

        - x from left to right 
        - y from bottom to top 
    """
    return kstore.window.getMousePos()

def getMouseX():
    """
        returns the x-coordinate of the mouse position  (x from left to right) 
    """
    return kstore.window.getMousePos()[0]

def getMouseY():
    """
        returns the y-coordinate of the mouse position  (y from bottom to top) 
    """
    return kstore.window.getMousePos()[1]

def drawInput(label="", handler=None):
    """
        draws an input field (single line) with default width 200 and height 50

        - label is an optional string (name of the input field)
        - handler is an optional function that executes, if the return key is pressed; handler expects one argument (the text as a string)
        - if handler is not provided, the text can be retrieved by label.getText()

        **example 1**

        input = drawInput("name", print) # prints the input content, if return isp ressed

        **example 2**
        
        input = drawInput("name")
        
        def print_input():
            print(input.getText())
        
        move(0,-100)
        drawInput("submit", print_input)
    """
    input = kInput(str(label), handler)
    input._updateShape()
    input._draw()
    return input 

def drawLabel(name, text):
    """
        draws an multi-line label with default width 200 and height 50
        
        - new lines can be insertes by \\n

        **example**

        drawLabel("name", "Johnny\\nCash")
    """
    label = kLabel(str(name), str(text))
    label._updateShape()
    label._draw()
    return label 

def drawText(text):
    """
        draws an single-line text (without a border)

        **example**

        drawText("hello world")
    """
    text = kText(str(text))
    text._updateShape()
    text._draw()
    return text 

def drawButton(text, handler):
    """
        draws an button with default width 200 and height 50

        - text is a string (displayed name of the button)
        - handler is an function that executes, when the button is pressed
        - the handler function excpects 0 arguments

        **example**
        
        def print_button():
            print("world")
        
        drawButton("hello", print_input)
    """
    button = kButton(str(text), handler)
    button._updateShape()
    button._draw()
    return button

def setFontSize(size):
    """
        set font size in pixel
    """
    kstore.setFontsize(size)

def getFontSize():
    """
        returns font size in pixel
    """
    return kstore.getFontSize()

def setFontColor(*rgba):
    """
        set the current font color (for texts, labels, inputs, buttons) in rgba

        - rgb = red, green, blue
        - a stands for alpha (transparency)
        - each value is between 0 and 255

        **examples**

        - setFontColor(255,0,0)
        - setFontColor(255,0,0, 100) *with alpha (transparency)*
        - setFontColor([255,0,0]) *as a list*
        - setFontColor([255,0,0,100]) *as a list (including alpha)*
    """
    kstore.setFontColor(rgba)

def getFontColor():
    """
        returns the current font color as a list [r,g,b,a] 

        - rgb = red, green, blue
        - a stands for alpha (transparency)
        - each value is between 0 and 255
    """
    return kstore.getFontColor()

def saveAsPng(filename):
    """
        save the current window as a png 

        filename is the name of the file (as a string)

        **example**
        - saveAsPng("screenshot")
    """
    kstore.scaleAnim(0)
    action_queue.add(kSetter(kstore.window.saveAsPng, filename))
    kstore.unscaleAnim()

def beginRecording():
    """
        activate frame capture

        **example**

        beginRecording()
        
        ... 

        endRecording()

        saveAsGif("example")
    """
    kstore.scaleAnim(0)
    action_queue.add(kSetter(kstore.window.setRecord, True))
    kstore.unscaleAnim()

def endRecording():
    """
        end frame capture

        **example**

        beginRecording()
        
        ... 

        endRecording()

        saveAsGif("example")
    """
    kstore.scaleAnim(0)
    action_queue.add(kSetter(kstore.window.setRecord, False))
    kstore.unscaleAnim()

def saveAsMp4(filename):
    """
        save captured frames as a mp4 movie

        **example**

        beginRecording()
        
        ... 

        endRecording()

        saveAsMp4("example")
    """
    kstore.scaleAnim(0)
    action_queue.add(kSetter(kstore.window.saveAsMp4, filename))
    kstore.unscaleAnim()

def saveAsGif(filename):
    """
        save captured frames as a GIF

        **example**

        beginRecording()
        
        ... 

        endRecording()

        saveAsGif("example")
    """
    kstore.scaleAnim(0)
    action_queue.add(kSetter(kstore.window.saveAsGif, filename))
    kstore.unscaleAnim()

def setAnimationType(type):
    """
        set the animation type to "linear" or "smooth"

        **examples**

        setAnimationType("linear")
        setAnimationType("smooth")
    """
    global INTERPOLATION_FUNCTION

    if type == "linear":
        INTERPOLATION_FUNCTION = linear
    elif type == "smooth":
        INTERPOLATION_FUNCTION = smooth
    else:
        raise ValueError("unknown inteprolation function")

def showCursor():
    """
        shows the drawing cursor
    """
    kstore.cursor.show()

def hideCursor():
    """
        hides the drawing cursor
    """
    kstore.cursor.hide()

def _clear():
    i = 0
    while i < len(shape_buffer):
        shape = shape_buffer[i]
        if shape._ready:
            shape_buffer.pop(i)
        else:
            i = i + 1

    i = 0
    while i < len(ui_buffer):
        shape = ui_buffer[i]
        if shape._ready:
            ui_buffer.pop(i)
        else:
            i = i + 1

    kstore.window.update()

def clear():
    """
        clears the drawing board
    """
    kstore.scaleAnim(0)
    action_queue.add(kAction(_clear))
    kstore.unscaleAnim()
    
def getListSample(name):
    """
        returns a mysterious list of a given name (string)
    """
    return _getSample(name)


def drawList(the_list, width, height):
    the_list = kList(the_list, width, height)
    the_list._updateShape()
    the_list._draw()
    return the_list
    
# ==================================== TEST CODE ===========================================

if __name__ == "__main__":
    print(" > create your own python script")
    print("""
    from ksbanim import *
    
    createWindow()
          
    # your drawing code hier 
          
    run()
""")