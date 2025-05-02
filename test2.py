from ksbanim import *
import random 

setTime(0)              # deaktiviert Animationen von ksbanim
hideCursor()            # blendet den Cursor aus

NUM_BIRDS = 75          # Anzahl Vögel
MAX_SPEED = 250         # maximale Geschwindigkeit

def createBird(radius, color):
    x = random.randint(0,1000)
    y = random.randint(0,1000)
    setPos(x, y)                # zufällige Position
    
    setColor(color)
    
    bird = drawCircle(radius)

    vx = random.randint(-MAX_SPEED,MAX_SPEED)
    vy = random.randint(-MAX_SPEED,MAX_SPEED)

    bird.vx = vx 
    bird.vy = vy
    
    return bird


def createSwarm(num, radius, color):
    the_swarm = []

    while len(the_swarm) < num:
        animal = createBird(radius, color)
        the_swarm.append(animal)

    return the_swarm 

birds = createSwarm(NUM_BIRDS, 5, [0,255,0])    # Vogelschwarm

def updateSwarmPosition(swarm, dt):
    for bird in swarm:
        x = bird.getX()
        y = bird.getY()

        x = x + bird.vx*dt
        y = y + bird.vy*dt
            
        bird.setPos(x,y)

def update(dt):                            
    dt = dt/1000 
    updateSwarmPosition(birds, dt)

onTick(update)