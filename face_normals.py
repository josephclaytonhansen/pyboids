import bpy, bmesh, random
from mathutils import Vector, Matrix

surfaceBounds = {}
surfacePoints = {}

def getUpwardsFaces(obj):
    obj = bpy.data.objects[obj]
    bpy.ops.object.mode_set(mode='EDIT')
    mesh = bmesh.from_edit_mesh(bpy.context.object.data)
    ge = False

    for g in bpy.context.active_object.vertex_groups:
        if g.name == "PB_LandingSurface":
            ge = True
            break
    if not ge:
        vg = bpy.context.active_object.vertex_groups.new(name="PB_LandingSurface")
    else:
        vg = bpy.context.active_object.vertex_groups["PB_LandingSurface"]
        
    vi = []
    fvc = {}
    fvc_baked = {}

    up = Vector([0,0,1])

    for f in mesh.faces:
        if f.normal.dot(up) == 1.0 and f.normal.z == 1: #we can get slanting faces within a leniency amount
            #with something like < 0.9; however, this makes things FAR more complex later on.
            #for now, only flat faces can be considered.
            f.select = True
            
            v = [vert.index for vert in f.verts]
            vi.append(v)
            
            fvc[f.index] = [[vert.co[0], vert.co[1]] for vert in f.verts]
            fvc_baked[f.index] = False

    bmesh.update_edit_mesh(bpy.context.object.data)        
    bpy.ops.object.mode_set(mode='OBJECT')
    for l in vi:
        vg.add(l, 1.0, 'ADD')
    
    for o in bpy.context.selected_objects:
        o.select_set(False)
    
    return [fvc, fvc_baked]

def bakeFace(f,i):
    min_x = f[1][0]
    max_x = f[0][0]
    min_y = f[2][1]
    max_y = f[1][1]
    surfaceBounds[i] = [min_x, max_x, min_y, max_y]

def getRandomPoints(o, fvc):
    for face in fvc[0]: 
        if fvc[1][face] == False: #save resources wherever possible;
            #there's no need to repeat work
            bakeFace(fvc[0][face], face)
            fvc[1][face] == True

        h = surfaceBounds[face]
        random_x = random.randint(h[0], h[1]) * random.random()
        random_y = random.randint(h[2], h[3]) * random.random()
        surfacePoints[face] = [random_x, random_y, 0]
        
        o = bpy.data.objects.new(str(face), None)
        o.location = surfacePoints[face]
        bpy.context.scene.collection.objects.link(o)
        o.empty_display_size = 2
        o.empty_display_type = "PLAIN_AXES"
        
    print(surfacePoints)

getRandomPoints("Cube", getUpwardsFaces("Cube"))
