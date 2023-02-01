import bpy, random
from datetime import datetime
from mathutils import Vector
C = bpy.context

#----------------Generic helper functions-----------------

def vectorDistance(a: Vector, b: Vector) -> float: 
    return (b - a).length
      
def selectAndActive(n):
    #utility function- there may be a one-liner that can replace this
    obj = bpy.data.objects[n]
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def moveToCollection(target, n): #this isn't working, for some reason I haven't bug checked yet
    collection = C.blend_data.collections.new(name=target)
    C.collection.children.link(collection)
    selectAndActive(n)
    objs = C.selected_objects
    coll_target = C.scene.collection.children.get(target)
    if coll_target and objs:
        for ob in objs:
            for coll in ob.users_collection:
                coll.objects.unlink(ob)
            coll_target.objects.link(ob)

def randomSeed():
    seed = int(datetime.now().day * datetime.now().second * random.random())
    return seed


#-------------------Boid classes--------------------------

class GlobalParameters: #seed, count
    #eventually this would have a UI
    def __init__(self, seed, count):
        self.debug = False
        self.seed = seed
        self.count = count
        self.sim_start = 0
        self.sim_end = 250
        self.baked = False
        self.seed = 10

class Critter: #wrapper for Blender object with some additional information 
    def __init__(self, name, obj):
        self.name = name
        self.obj = obj
        self.color = obj.color #debug value, remove
        self.velocity = Vector([0.0,0.0,0.0])
        self.personal_space = 1.35
        self.perception_length = 1.55 #this should always be bigger than personal space
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
    moveToCollection(col, critter)
    
    for x in range(0, count):
        bpy.ops.object.duplicate(linked=True)
        o = bpy.context.selected_objects[0]
        r = Critter(o.name, o)
        ClassyCritters.append(r)
        r.initialized = True
        
    if initialSpacing(count):
        finalizeInitialSpacing()
    
def initialSpacing(count):
    if count > 0:
        c = count / 100
        for critter in ClassyCritters:
            p = critter.personal_space + c
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

fillCollectionWithCritters("Cube", "Boids", g.count)
#this is reasonably fast for 0 < count < 1000, 
#it can take several seconds to initialize at count > 1000 . Probably can be optimized

#-------------------------------------Simulation---------------------------------------

def syncWeights(critter, s, c, a, sw, cw, aw, mw):
    t = sw+cw+aw+mw
    if t != 100:
        factor = 100/t
        sw = sw * factor
        cw = cw * factor
        aw = aw * factor
        mw = mw * factor
        
    working_velocity = critter.velocity.copy()
    maintain = mw * working_velocity 
    s = s * sw
    c = c * cw
    a = a * aw
    working_velocity = maintain + s + c + a
    return working_velocity.normalized()

def bakeFrameAndAdvance(scene):
    #starting on g.sim_start, 
    if not g.baked:
        for critter in ClassyCritters:
            vs = separation(critter)
            vc = cohesion(critter, 3)
            va = alignment(critter, 2)
            
            if g.debug:
                print("Critter: ", critter,
                 "Frame: ", bpy.data.scenes["Scene"].frame_current,
                "Separation: ", vs, "Cohesion: ",
                vc, "Alignment: ", va)
                
            critter.velocity = syncWeights(critter, vs, vc, va, 20, 40, 30, 10)

            
        #calculate...
        #bake frame...
        #advance to next frame...
        #until g.sim_end
        return True


def separation(critter):
    temp_velocity = Vector([0,0,0])
    if critter.lneighbors > 0:
        for boid in critter.neighbors:
            d = vectorDistance(critter.obj.location, boid.obj.location)
            if d < critter.personal_space:
                temp_velocity -= critter.obj.location - boid.obj.location
                    
        critter.get_neighbors(ClassyCritters)
        return temp_velocity.normalized()

def cohesion(critter, group):
    i = bpy.data.scenes["Scene"].frame_current % group == 0 
    #there's no need for universal cohesion on every frame, this switches between groups
    for boid in range(i, len(ClassyCritters), group):
        temp_velocity = Vector([0,0,0])
        temp_velocity += ClassyCritters[boid].obj.location
    temp_velocity -= critter.obj.location
    temp_velocity = temp_velocity / (len(ClassyCritters)/group)
    return temp_velocity.normalized()

def alignment(critter, group):
    i = bpy.data.scenes["Scene"].frame_current % group == 0 
    #there's no need for universal alignment on every frame, this switches between groups
    for boid in range(i, len(ClassyCritters), group):
        temp_velocity = Vector([0,0,0])
        temp_velocity += ClassyCritters[boid].velocity
    temp_velocity -= critter.obj.location
    temp_velocity = temp_velocity / (len(ClassyCritters)/group)
    return temp_velocity.normalized()
    
        
bpy.app.handlers.frame_change_post.append(bakeFrameAndAdvance)