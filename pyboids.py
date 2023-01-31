import bpy, random
from mathutils import Vector
C = bpy.context

class GlobalParameters: #seed, count
    #eventually this would have a UI
    def __init__(self, seed, count):
        self.seed = seed
        self.count = count

class Critter: #wrapper for Blender object with some additional information 
    def __init__(self, name, obj):
        self.name = name
        self.obj = obj
        self.velocity = None
        self.personal_space = 1.0
        self.perception_length = 5
        self.neighbors = []
        self.initialized = False

ClassyCritters = []

def vectorDistance(a: Vector, b: Vector) -> float: 
    #going to need this later
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

def fillCollectionWithCritters(critter, col, count):
    random.seed(g.seed) 
    
    selectAndActive(critter)
    o = bpy.context.selected_objects[0]
    ClassyCritters.append(Critter(o.name, o))
    moveToCollection(col, critter)
    
    for x in range(0, count):
        bpy.ops.object.duplicate(linked=True)
        o = bpy.context.selected_objects[0]
        ClassyCritters.append(Critter(o.name, o))

    initialSpacing(count)

def initialSpacing(count):
    c = count / 100
    for critter in ClassyCritters:
        p = critter.personal_space + c
        # I don't have any hard math behind this, but it gives good looking results in testing
        critter.obj.location[0] = ((p*2)*random.random()) - p
        critter.obj.location[1] = ((p*2)*random.random()) - p
        critter.obj.location[2] = ((p*2)*random.random()) - p
 
g = GlobalParameters(10, 300) #the same seed will return the same results! 
#use a random number for the first parameter if you want random results

fillCollectionWithCritters("Cube", "Boids", g.count)
#this is reasonably fast for 0 < count < 1000, 
#it can take several seconds to initialize at count > 1000 . Probably can be optimized
