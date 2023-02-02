import bpy, random
from datetime import datetime
from mathutils import Vector
C = bpy.context

from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       FloatVectorProperty,
                       EnumProperty,
                       PointerProperty,
                       )

bl_info = {
    'name': 'PyBoids',
    'category': 'Animation',
    'author': 'Joseph Hansen',
    'version': (0, 0, 3),
    'blender': (3, 3, 0),
    'location': '',
    'description': ''
}

#----------------Generic helper functions-----------------

def vectorDistance(a: Vector, b: Vector) -> float: 
    return (b - a).length
      
def selectAndActive(n):
    #utility function- there may be a one-liner that can replace this
    obj = bpy.data.objects[n]
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def randomSeed():
    seed = int(datetime.now().day * datetime.now().second * random.random())
    return seed


#-------------------Boid classes--------------------------

class GlobalParameters: #seed, count
    #eventually this would have a UI
    def __init__(self, seed, count):
        self.started = False
        self.debug = False
        self.seed = seed
        self.count = count #expose this!
        self.sim_start = 0
        self.sim_end = 250
        self.baked = False
        self.air_speed_variation = .5 #expose this!
        self.air_speed = .8 #expose this!
        self.personal_space_multiplier = .09 #expose this!

class Critter: #wrapper for Blender object with some additional information 
    def __init__(self, name, obj):
        self.name = name
        self.obj = obj
        self.color = obj.color #debug value, remove
        self.velocity = Vector([0.0,0.0,0.0])
        self.air_speed = .8
        self.personal_space = 56
        self.perception_length = 54
        self.neighbors = []
        self.lneighbors = 0
        self.initialized = False
    
    def __str__(self):
        return self.name+"  Neighbors: " + str((self.lneighbors))
    
    def get_neighbors(self, boids):
        self.neighbors = []
        neighbors = self.neighbors
        for b in boids:
            if b != self:
                dist = vectorDistance(self.obj.location, b.obj.location)
                if dist < self.perception_length:
                    neighbors.append(b)
        self.neighbors = neighbors
        self.lneighbors = len(self.neighbors)
        return self.lneighbors

ClassyCritters = []

def fillCollectionWithCritters(critter, col, count):
    random.seed(g.seed) 
    
    selectAndActive(critter)
    o = bpy.context.selected_objects[0]
    ClassyCritters.append(Critter(o.name, o))
    #moveToCollection(col, critter)
    
    for x in range(0, count):
        bpy.ops.object.duplicate(linked=True)
        o = bpy.context.selected_objects[0]
        try:
            bpy.data.collections["PyBoids"].objects.link(o)
            bpy.data.collections["Collections"].objects.unlink(o)
        except Exception as e:
            print(e)
        r = Critter(o.name, o)
        k = random.random()
        r.air_speed = g.air_speed
        if k >= .5:
            r.air_speed -= ((k / (1/g.air_speed_variation)))
        else:
            r.air_speed += ((k / (1/g.air_speed_variation)))
        ClassyCritters.append(r)
        r.initialized = True
        r.personal_space = 1120 * g.personal_space_multiplier
        r.perception_length = r.personal_space - 2
        
    if initialSpacing(count):
        finalizeInitialSpacing()
    
def initialSpacing(count):
    if count > 0: 
        c = count / 10
        for critter in ClassyCritters:
            p = (1/critter.personal_space) + c
            # I don't have any hard math behind this, but it gives good looking results in testing
            r1, r2, r3 = random.random(), random.random(), random.random()
            critter.obj.location[0] = ((p*2)*r1) - p
            critter.obj.location[1] = ((p*2)*r2) - p
            critter.obj.location[2] = ((p*2)*r3) - p
            critter.velocity = Vector([r3, r2, r1]).normalized()
            
            if g.debug:
                print(critter.velocity)
        return True
    
def finalizeInitialSpacing():
    
    total_checks = 0 #this is a pure debug value, it should be removed for production
    
    for critter in ClassyCritters:
        total_checks += critter.get_neighbors(ClassyCritters)

 
g = GlobalParameters(randomSeed(), 100) #the same seed will return the same results! 
#use a random number for the first parameter if you want random results

#-------------------------------------Simulation---------------------------------------

def syncWeights(critter, s, c, a, sw, cw, aw, mw):        
    working_velocity = critter.velocity.copy()
    maintain = mw * working_velocity 
    s = s * sw
    c = c * cw
    a = a * aw
    working_velocity = maintain + s + c + a
    return working_velocity.normalized()

def bakeFrameAndAdvance(scene):
    #starting on g.sim_start, 
    if not g.baked and g.started:
        for critter in ClassyCritters:
            vs = separation(critter)
            vc = cohesion(critter, 3)
            va = alignment(critter, 2)
            
            if g.debug:
                print("Critter: ", critter,
                 "Frame: ", bpy.data.scenes["Scene"].frame_current,
                "Separation: ", vs, "Cohesion: ",
                vc, "Alignment: ", va)
                
            critter.velocity = (syncWeights(critter,
             vs, vc, va,
              -g.personal_space_multiplier, 0.1, 0.1, 0.5)).normalized()

            #for now...
            critter.obj.location += critter.velocity * critter.air_speed         
            
        #calculate...
        #bake frame...
        #advance to next frame...
        #until g.sim_end
        return True


#--------------------Basic Rules------------------------

def separation(critter):
    critter.get_neighbors(ClassyCritters)
    temp_velocity = Vector([0,0,0])
    if critter.lneighbors > 0:
        for boid in critter.neighbors:
            d = vectorDistance(critter.obj.location, boid.obj.location)
            if d < critter.personal_space:
                direction = (boid.obj.location - critter.obj.location).normalized()
                temp_velocity += (1.0 / d) * direction
        return temp_velocity #.normalized()

def cohesion(critter, group):
    i = bpy.data.scenes["Scene"].frame_current % group == 0 
    #there's no need for universal cohesion on every frame, this switches between groups
    center_position = Vector([0,0,0])
    count = 0
    for boid in range(i, len(ClassyCritters), group):
        center_position += ClassyCritters[boid].obj.location
        count += 1
    center_position /= count
    temp_velocity = center_position - critter.obj.location
    return temp_velocity #.normalized()

def alignment(critter, group):
    i = bpy.data.scenes["Scene"].frame_current % group == 0 
    #there's no need for universal alignment on every frame, this switches between groups
    for boid in range(i, len(ClassyCritters), group):
        temp_velocity = Vector([0,0,0])
        temp_velocity += ClassyCritters[boid].velocity
    temp_velocity -= critter.velocity
    temp_velocity = temp_velocity / (len(ClassyCritters)/group)
    return temp_velocity # .normalized()
    

#-----------------------Advanced Rules------------------------

    
#----------------------------Panel----------------------------    

class BoidsPanel(bpy.types.Panel):
    bl_label = "PyBoids"
    bl_idname = "OBJECT_PT_pyboids_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = "objectmode"
    bl_category = "Animation"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        if not g.started:
            row.operator("pyboids.init")
            row = layout.row()
            row.prop(scene, "boid_count")
            row = layout.row()
            row.prop(scene, "pscale")
        else:
            row.operator("pyboids.clear")
        row = layout.row()
        row.prop(scene, "psm")
        row = layout.row()
        row.prop(scene, "bas")
        row = layout.row()
        row.prop(scene, "asv")
        

#----------------------------Operators------------------------

class CreateBoids(bpy.types.Operator):
    """Initialize a boid simulation"""
    bl_idname = "pyboids.init"
    bl_label = "Start boid simulation"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        bpy.context.collection.children.link(bpy.data.collections.new("PyBoids"))
        
        ClassyCritters = []
        g.personal_space_multiplier = bpy.data.scenes["Scene"].psm / 100.0
        g.air_speed = bpy.data.scenes["Scene"].bas / 10.0
        g.air_speed_variation = bpy.data.scenes["Scene"].asv
        g.count = bpy.data.scenes["Scene"].boid_count
        fillCollectionWithCritters("Cube", "PyBoids", g.count)
        #this is reasonably fast for 0 < count < 1000, 
        #it can take several seconds to initialize at count > 1000 . Probably can be optimized
        g.started = True
        return {'FINISHED'}

class ResetBoids(bpy.types.Operator):
    """Clear the existing boid simulation"""
    bl_idname = "pyboids.clear"
    bl_label = "Clear boids"
    
    def execute(self, context):
        ClassyCritters = []
        for obj in bpy.data.objects:
            obj.select_set(False)
        for obj in bpy.data.collections['PyBoids'].keys():
            obj.select_set(True)
            bpy.ops.object.delete()
        bpy.data.collections.remove(bpy.data.collections['PyBoids'])
        g.started = False
        g.baked = False
        return {'FINISHED'}
    
    
#--------------------Viewport Preview-------------------------
try:
    g.personal_space_multiplier = bpy.data.scenes["Scene"].psm / 100.0
    g.air_speed = bpy.data.scenes["Scene"].bas / 10.0
    g.air_speed_variation = bpy.data.scenes["Scene"].asv
except Exception as e:
    print(e)
bpy.app.handlers.frame_change_post.append(bakeFrameAndAdvance)

#---------------------------Register--------------------------

def register():
    bpy.utils.register_class(BoidsPanel)
    bpy.utils.register_class(CreateBoids)
    bpy.utils.register_class(ResetBoids)
    bpy.types.Scene.boid_count = IntProperty(name = "Boid count", default = 100)
    bpy.types.Scene.bas = IntProperty(name = "Air speed", default = 8) #/10
    bpy.types.Scene.asv = FloatProperty(name = "Air speed variation", default = .5)
    bpy.types.Scene.psm = IntProperty(name = "Personal space multiplier", default = 9) #/100
    bpy.types.Scene.pscale = BoolProperty(name = "Proportional size",
    description = "Boids scale relative to air speed", default = False)


def unregister():
    bpy.utils.unregister_class(BoidsPanel)
    bpy.utils.unregister_class(CreateBoids)
    bpy.utils.unregister_class(ResetBoids)
    for i in [bpy.types.Scene.boid_count, bpy.types.Scene.bas,
    bpy.types.Scene.asv, bpy.types.Scene.psm, bpy.types.Scene.pscale]:
        del i


if __name__ == "__main__":
    register()