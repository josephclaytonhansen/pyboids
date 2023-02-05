import bpy, random, math

def hopInPlace(o, height, speed):
    o.location.z = abs(math.sin(bpy.data.scenes["Scene"].frame_current/speed)) * height


def hopForward(o, velocity):
    o.location.x += velocity[0]
    b.location.y += velocity[1]

def hopAround(scene):
    height = 2
    speed = 3
    hopInPlace(bpy.data.objects["Cube"], height, speed)
   
bpy.app.handlers.frame_change_post.append(hopAround)