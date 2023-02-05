import bpy, random, math
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
        self.underwater = False #expose this!

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
        
        self.energy_store = 200
        self.energy = 200
        self.landing_time = 0
        self.recharge_time = 40
        self.rt_store = 40
        self.is_flying = True
        
        self.zero_frame_loc = Vector([0.0,0.0,0.0])
        self.zero_frame_vel = Vector([0.0,0.0,0.0])
    
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
    
    #selectAndActive(critter)
    o = bpy.context.selected_objects[0]
    ClassyCritters.append(Critter(o.name, o))
    #moveToCollection(col, critter)
    
    for x in range(0, count):
        bpy.ops.object.duplicate(linked=True)
        o = bpy.context.selected_objects[0]
        
        try:
            bpy.data.collections["PyBoids"].objects.link(o)
            bpy.data.collections["Collection"].objects.unlink(o)
        except:
            pass

        r = Critter(o.name, o)
        k = random.random() #no need to re-run this each time
        
        max_energy = bpy.data.scenes["Scene"].max_airtime - bpy.data.scenes["Scene"].min_airtime
        if max_energy < 0:
            max_energy = 0
        
        p = int(bpy.data.scenes["Scene"].min_airtime + (k * max_energy))
        r.energy = p
        r.energy_store = p
        
        max_recharge_time = bpy.data.scenes["Scene"].max_rechargetime - bpy.data.scenes["Scene"].min_rechargetime
        if max_recharge_time < 0:
            max_recharge_time = 0
        
        i = int(bpy.data.scenes["Scene"].min_rechargetime + (k * max_recharge_time))
        r.recharge_time = i
        r.rt_store = i
        
        if g.debug:
            print(r.energy, r.recharge_time)
        
        r.air_speed = g.air_speed
        if k >= .5:
            r.air_speed -= ((k / (1/g.air_speed_variation)))
        else:
            r.air_speed += ((k / (1/g.air_speed_variation)))
        ClassyCritters.append(r)
        r.initialized = True
        r.personal_space = 1120 * g.personal_space_multiplier
        r.perception_length = r.personal_space - 2
        j = r.air_speed / ((1/bpy.data.scenes["Scene"].pscalesf) * 100)
        
        
        if bpy.data.scenes["Scene"].pscale == True:
            for d in [0,1,2]:
                o.scale[d] = o.scale[d] + j
        
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
            
            critter.zero_frame_loc = critter.obj.location.copy()
            critter.zero_frame_velocity = critter.velocity.copy()
            
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
    g.underwater = bpy.data.scenes["Scene"].underwater
    g.personal_space_multiplier = bpy.data.scenes["Scene"].psm / 100.0
    if bpy.data.scenes["Scene"].goalb:
        goal_pos = bpy.data.scenes["Scene"].goal.location
    
    #starting on g.sim_start, 
    if not g.baked and g.started:
        for critter in ClassyCritters:
            use_synced_weights = True
            k = random.random()
            
            if g.underwater:
                critter.energy = 999
                critter.recharge_time = 0
                
            if bpy.data.scenes["Scene"].frame_current <= 1: #zero frame checks
                critter.obj.location = critter.zero_frame_loc
                critter.velocity = critter.zero_frame_velocity
                critter.recharge_time = critter.rt_store
                critter.energy = critter.energy_store

            else: #every other frame
                if critter.is_flying: #flying
                    critter.energy -= 1
                    if critter.energy <= 0: #out of energy, time to land
                        critter.energy = 0
                        critter.is_flying = False
                        critter.recharge_time = critter.rt_store
                        
                else: #landed
                    landingBehavior(critter)
                    critter.recharge_time -= 1
                    if critter.recharge_time <= 0: #done recharging, time to fly
                        critter.recharge_time = 0
                        critter.is_flying = True
                        critter.energy = critter.energy_store    
            
            if bpy.data.scenes["Scene"].goalb: #goal enabled
                if k <= bpy.data.scenes["Scene"].goalweight / 10: #move towards goal?
                    critter.velocity = (critter.air_speed * (goal_pos - critter.obj.location)).normalized()
                    use_synced_weights = False
                    
            
            if use_synced_weights: #normal behavior, three basic rules
                vs = separation(critter)
                vc = cohesion(critter, 3)
                va = alignment(critter, 2)
                
                if g.debug:
                    print("Critter: ", critter, "Energy: ",critter.energy,
                     "Air Speed: ", critter.air_speed,
                    "Separation: ", vs, "Cohesion: ",
                    vc, "Alignment: ", va)
                    
                critter.velocity = (syncWeights(critter,
                 vs, vc, va,
                  -g.personal_space_multiplier, 0.1, 0.1, 0.5)).normalized()

            #for now...
            if critter.is_flying:
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

def landingBehavior(critter):
    pass
        
    
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
        layout.label(text="Static (initial) settings")
        row = layout.row()
        row.scale_y = 2
        if not g.started:
            row.operator("pyboids.init")
            row = layout.row()
            row.prop(scene, "boid_count")
            row.prop(scene, "bseed")
            row = layout.row(align=True)
            row.prop(scene, "pscale")
            sub = row.row()
            sub.scale_x = 1.6
            sub.prop(scene, "pscalesf")
        else:
            row.operator("pyboids.clear")
        layout.separator()
        layout.label(text="Dynamic settings (keyframe-able)")
        row=layout.row()
        row.prop(scene, "underwater")
        row = layout.row()
        row.prop(scene, "psm")
        row = layout.row(align=True)
        row.prop(scene, "bas")
        row.prop(scene, "asv")
        layout.separator()

class BoidsLandingPanel(bpy.types.Panel):
    bl_label = "PyBoids Landing"
    bl_idname = "OBJECT_PT_pyboids_landing_panel"
    bl_space_type = 'VIEW_3D'
    bl_parent_id = 'OBJECT_PT_pyboids_panel' 
    bl_region_type = 'UI'
    bl_context = "objectmode"
    bl_category = "Animation"

    def draw(self, context):
        layout = self.layout
        scene = context.scene 
        if not bpy.data.scenes["Scene"].underwater:
            layout.label(text="Recharge time:")
            row = layout.row(align=True)
            row.prop(scene, "min_rechargetime")
            row.prop(scene, "max_rechargetime")
            layout.label(text="Air time:")
            row = layout.row(align=True)
            row.prop(scene, "min_airtime")
            row.prop(scene, "max_airtime")
            layout.separator()
            row = layout.row(align=True)
            row.prop(scene, "crawl")
            row.prop(scene, "sticky")
            row = layout.row(align=True)
            row.scale_x = .9
            row.prop(scene, "hopandfeed")
            sub = row.row()
            sub.scale_x = 1.6
            sub.prop(scene, "hopsurface")
        
class BoidsRulesPanel(bpy.types.Panel):
    bl_label = "PyBoids Rules"
    bl_idname = "OBJECT_PT_pyboids_rules_panel"
    bl_space_type = 'VIEW_3D'
    bl_parent_id = 'OBJECT_PT_pyboids_panel' 
    bl_region_type = 'UI'
    bl_context = "objectmode"
    bl_category = "Animation"

    def draw(self, context):
        layout = self.layout
        scene = context.scene 
        row = layout.row(align=True)
        row.prop(scene, "goalb")
        sub = row.row()
        sub.scale_x = 1.6 
        sub.prop(scene, "goal")
        row = layout.row(align=True)
        row.prop(scene, "goalweight")
        layout.separator()
        
        row = layout.row(align=True)
        row.prop(scene, "predatorsb") 
        row.prop(scene, "predators")
        row = layout.row(align=True)
        row.prop(scene, "predatorscatter") 
        row.prop(scene, "predatoracc")
              

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
        
        g.saved_initiator = bpy.context.selected_objects[0]
        g.saved_initiator_location = bpy.context.selected_objects[0].location.copy()
        #currently this only allows for 1 selected object to be a boid object
        #eventually this needs to be changed to be a list of saved locations
        
        
        ClassyCritters = []
        
        g.seed = bpy.data.scenes["Scene"].bseed
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
        
        g.saved_initiator.location = g.saved_initiator_location
        g.saved_initiator.select_set(True)
        
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
    b = bpy.types.Scene
    bpy.utils.register_class(BoidsPanel)
    bpy.utils.register_class(BoidsLandingPanel)
    bpy.utils.register_class(BoidsRulesPanel)
    bpy.utils.register_class(CreateBoids)
    bpy.utils.register_class(ResetBoids)
    b.boid_count = IntProperty(name = "Count", default = 100)
    b.bas = IntProperty(name = "Air speed", default = 8) #/10
    b.asv = FloatProperty(name = "Variation", description = "Air speed variation", default = .5)
    b.psm = IntProperty(name = "Personal space", default = 9) #/100
    b.pscale = BoolProperty(name = "Mass",
    description = "Boids scale relative to air speed", default = False)
    b.pscalesf = IntProperty(name="Variation", default = 2) # *1/n * 100
    b.underwater = BoolProperty(name = "Underwater (Disable Landing)",
    description = "Underwater boid simulations don't land.\nThey remain in motion indefinitely")
    b.min_rechargetime = IntProperty(name="Min",
    default=20,
    description="When a boid has been in the air long enough to run out of energy,\n it must land and recharge. This is the minimum amount of time (in frames) for recharge")
    b.max_rechargetime = IntProperty(name="Max",
    default=40,
    description="When a boid has been in the air long enough to run out of energy,\n it must land and recharge. This is the maximum amount of time (in frames) for recharge")
    b.min_airtime = IntProperty(name="Min",
    default = 200,
    description="How long (at least) a boid stays in the air before needing to land, in frames.")
    b.max_airtime = IntProperty(name="Max",
    default = 300,
    description="How long (at most) a boid stays in the air before needing to land, in frames.\nSet to 0 to disable flying")
    b.crawl = BoolProperty(name = "Crawl",
    description = "If set to True, landed boids will crawl along the surfaces of set objects while landed, like insects.\nIf set to False, boids will be stationary while landed, like birds in a tree.")
    b.hopandfeed=BoolProperty(name="Hop",
    description = "If True, landed boids will hop on the selected surface like birds feeding.\nCan combine with crawling.")
    b.hopsurface = PointerProperty(name="Surfaces", type = bpy.types.Collection,
    description="Set the surfaces for boids to move on")
    b.sticky = BoolProperty(name="Sticky crawl", 
    description = "If True, boids will crawl and ignore gravity, like insects.\nIf false, boids will only land on and crawl on faces facing upwards, like birds")
    b.goal = PointerProperty(name="",
    type = bpy.types.Object,
    description = "Goal object to move towards in flight")
    b.goalb = BoolProperty(name = "Goal?", description="Goal object to move towards in flight.")
    b.predators = PointerProperty(name="",
    type = bpy.types.Collection,
    description = "Predators to move away from in flight, and potentially split the flock.\nEffective distance is determined by perception distance")
    b.predatorsb = BoolProperty(name = "Predators?",
    description = "Predators to move away from in flight, and potentially split the flock.\nEffective distance is determined by perception distance")
    b.predatorscatter=BoolProperty(name="Scatter landed",
    description = "If True, predators will force landed boids to take flight immediately if they are near enough")
    b.predatoracc = BoolProperty(name="Air speed burst",
    description = "If True, boids will have a burst of increased speed while a predator is within perception distance.\nThis will rapidly deplete their air time, and they will land sooner")
    b.bseed = IntProperty(name="Seed", default=g.seed)
    b.goalweight = FloatProperty(min=0.1, max = 2.0, default = 0.75, 
    name = "Goal importance",
    description = "Chance a boid has of moving towards the goal at any moment")
    

def unregister():
    bpy.utils.unregister_class(BoidsPanel)
    bpy.utils.unregister_class(BoidsLandingPanel)
    bpy.utils.unregister_class(BoidsRulesPanel)
    bpy.utils.unregister_class(CreateBoids)
    bpy.utils.unregister_class(ResetBoids)
    for i in [b.boid_count, b.bas,
    b.asv, b.psm, b.pscale,
    b.pscalesf, b.underwater,
    b.min_rechargetime, b.max_rechargetime,
    b.min_airtime, b.max_airtime, b.sticky,
    b.crawl, b.hopandfeed, b.hopsurface,
    b.goal, b.goalb, b.predators, b.predatorsb,
    b.predatorscatter, b.preatoracc, b.bseed,
    b.goalweight]:
        del i


if __name__ == "__main__":
    register()