"""For basic use import createOctreeFromBPYObjs from this module, pass it a
list of BPY objects and use the resulting octree for accellerated bounding box
collision detection and point intersection tests.
"""

try:
    from ins_vector import Vector
except:
    from mathutils import Vector

import bpy

#  TODO use Vector for locations and dimensions

def boundingBoxFromBPY(ob, overwriteRadii=None):
    corners = [ob.matrix_world * Vector(corner) for corner in ob.bound_box]

    # Visualise the corners. WARNING: Extremely slow
    """for x in range(8):
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        ob = bpy.context.object
        ob.location = corners[x]"""

    minx = min([c[0] for c in corners])
    miny = min([c[1] for c in corners])
    minz = min([c[2] for c in corners])

    radiusx = (max([c[0] for c in corners]) - minx)/2
    radiusy = (max([c[1] for c in corners]) - miny)/2
    radiusz = (max([c[2] for c in corners]) - minz)/2

    x = minx + radiusx
    y = miny + radiusy
    z = minz + radiusz

    if overwriteRadii:
        radiusx, radiusy, radiusz = overwriteRadii

    # Visualise the box. WARNING: Very slow
    """bpy.ops.mesh.primitive_cube_add()
    ob = bpy.context.object
    ob.dimensions = (dimx, dimy, dimz)
    ob.location = (x + (dimx/2), y + (dimy/2), z + (dimz/2))"""
    return BoundingBox((x, y, z), (radiusx, radiusy, radiusz), ob.name)


def boundingSphereFromBPY(ob, overwriteRadii=None):
    bb = boundingBoxFromBPY(ob, overwriteRadii=overwriteRadii)
    bb.isSphere = True
    return bb


class BoundingBox:
    """The object that is given to the octree so that it doesn't have to
    deal with the raw objects"""

    def __init__(self, position, radii, original, isSphere=False):
        """Note: isSphere can have serious speed improvements for dense scenes
        """
        self.pos = position  # (float, float, float)  # Middle
        self.dim = radii  # (float, float, float)
        self.sphereRadius = max(radii)  # only for when self.isSphere is True
        self.original = original  # Any type. Not touched in code
        self.isSphere = isSphere

        #  To visualise the tree. WARNING: Very slow
        """bpy.ops.mesh.primitive_cube_add()
        ob = bpy.context.object
        ob.draw_type = 'WIRE'
        ob.dimensions = self.dim
        ob.location = (self.pos[0] + (self.dim[0]/2),
                       self.pos[1] + (self.dim[1]/2),
                       self.pos[2] + (self.dim[2]/2))"""

    def setIsSphere(self, isSphere):
        """This is here so that if optimisations are later made to spheres or
        boxes then the shortcut can still be used to create spheres using the
        create bb = boundingBoxFromBPY then bb.setIsSphere(True)"""
        self.isSphere = isSphere

    def checkPoint(self, point):
        """Check if point is within the sphere or boundingbox"""
        if self.isSphere:
            dist = sum([(a-b)**2 for a, b in zip(self.pos, point)])
            # dist is actually distance**2
            if dist < self.sphereRadius**2:
                return True
            return False
        else:
            if not (abs(point[0] - self.pos[0]) <= self.dim[0]):
                return False
            if not (abs(point[1] - self.pos[1]) <= self.dim[1]):
                return False
            if not (abs(point[2] - self.pos[2]) <= self.dim[2]):
                return False
        return True

    def checkCollisionWithBB(self, bb):
        """Check if this sphere or box overlaps with another. If this or
        bb is not a sphere then it will default to boundingbox testing"""
        if self.isSphere and bb.isSphere:
            dist = sum([(a-b)**2 for a, b in zip(self.pos, bb.pos)])
            # Dist is actually distance**2
            if dist <= (self.sphereRadius + bb.sphereRadius)**2:
                return True
        else:
            if not abs(self.pos[0] - bb.pos[0]) <= (self.dim[0] + bb.dim[0]):
                return False
            if not abs(self.pos[1] - bb.pos[1]) <= (self.dim[1] + bb.dim[1]):
                return False
            if not abs(self.pos[2] - bb.pos[2]) <= (self.dim[2] + bb.dim[2]):
                return False
            return True


def createOctree(boundingBoxes):
    """Make an octree from bounding boxes"""
    if len(boundingBoxes) == 0:
        return Octree((0, 0, 0), (0, 0, 0))
    x = min([b.pos[0] for b in boundingBoxes])
    y = min([b.pos[1] for b in boundingBoxes])
    z = min([b.pos[2] for b in boundingBoxes])

    ux = max([b.pos[0] + b.dim[0] - x for b in boundingBoxes])
    uy = max([b.pos[1] + b.dim[1] - y for b in boundingBoxes])
    uz = max([b.pos[2] + b.dim[2] - z for b in boundingBoxes])

    #  To visualise the tree. WARNING: Very slow
    """#  To visualise the tree
    bpy.ops.mesh.primitive_cube_add()
    ob = bpy.context.object
    ob.dimensions = (ux, uy, uz)
    ob.location = (x + (ux/2),
                   y + (uy/2),
                   z + (uz/2))"""

    ot = Octree((x, y, z), (ux, uy, uz))

    for item in boundingBoxes:
        ot.add(item)

    return ot

def createOctreeFromBPYObjs(objs, allSpheres=True, radii=None):
    """The function you want to import from this module in most cases.
    If radii is left as default then the radius will be calculated from the
    object."""
    bbs = []

    for n, ob in enumerate(objs):
        if allSpheres:
            bbs.append(boundingSphereFromBPY(ob, overwriteRadii=radii[n]))
        else:
            bbs.append(boundingBoxFromBPY(ob, overwriteRadii=radii[n]))

    return createOctree(bbs)


class Octree:
    def __init__(self, position, dimensions):
        self.pos = position  # (float, float, float)
        self.dim = dimensions  # (float, float, float)
        hdx = self.dim[0]/2
        hdy = self.dim[1]/2
        hdz = self.dim[2]/2
        dims = (hdx, hdy, hdz)
        px = self.pos[0]
        py = self.pos[1]
        pz = self.pos[2]
        self.cells = [Leaf((px      , py + hdy, pz + hdz), dims),
                      Leaf((px + hdx, py + hdy, pz + hdz), dims),
                      Leaf((px      , py      , pz + hdz), dims),
                      Leaf((px + hdx, py      , pz + hdz), dims),
                      Leaf((px      , py + hdy, pz      ), dims),
                      Leaf((px + hdx, py + hdy, pz      ), dims),
                      Leaf((px      , py      , pz      ), dims),
                      Leaf((px + hdx, py      , pz      ), dims)
                     ]
        # 0: Top front left, 1: top front right,
        # 2: top back left, 3: top back right,
        # 4: bottom front left, 5: bottom front right,
        # 6: bottom back left, 7: bottom back right

        #  TODO store bounding boxes that are in all subtrees in the OT and
        #      and then pass them down to the leafs for collision detection

    def addToCell(self, item, cell):
        """Add item to cell and then divide cell if required"""
        if self.cells[cell].add(item):
            tmpLeaf = self.cells[cell]
            new = Octree(tmpLeaf.pos, tmpLeaf.dim)
            for content in tmpLeaf.contents:
                new.add(content)
            self.cells[cell] = new

    def isIn(self, pos, dim, axis):
        """Check if this bounding box is above and/or below the mid point of
        this octree along this axis"""
        greater = False
        less = False
        if (pos[axis] - self.pos[axis] + dim[axis]) >= self.dim[axis]/2:
            greater = True
        if (pos[axis] - self.pos[axis] - dim[axis]) <= self.dim[axis]/2:
            less = True
        return greater, less

    def add(self, item):
        """Return False since this node doesn't need splitting (already OT)"""
        gtx, ltx = self.isIn(item.pos, item.dim, 0)
        gty, lty = self.isIn(item.pos, item.dim, 1)
        gtz, ltz = self.isIn(item.pos, item.dim, 2)
        if gtx and gty and gtz:
            self.addToCell(item, 1)
        if gtx and gty and ltz:
            self.addToCell(item, 5)
        if gtx and lty and gtz:
            self.addToCell(item, 3)
        if gtx and lty and ltz:
            self.addToCell(item, 7)
        if ltx and gty and gtz:
            self.addToCell(item, 0)
        if ltx and gty and ltz:
            self.addToCell(item, 4)
        if ltx and lty and gtz:
            self.addToCell(item, 2)
        if ltx and lty and ltz:
            self.addToCell(item, 6)
        return False

    def checkPoint(self, point):
        """Which subtrees in the point in"""
        #  TODO can't one subtree just be chosen if the point is on the edge.
        #      does acuracy really matter that much?
        gtx, ltx = self.isIn(point, (0, 0, 0), 0)
        gty, lty = self.isIn(point, (0, 0, 0), 1)
        gtz, ltz = self.isIn(point, (0, 0, 0), 2)
        intersects = set()
        if gtx and gty and gtz:
            intersects = intersects.union(self.cells[1].checkPoint(point))
        if gtx and gty and ltz:
            intersects = intersects.union(self.cells[5].checkPoint(point))
        if gtx and lty and gtz:
            intersects = intersects.union(self.cells[3].checkPoint(point))
        if gtx and lty and ltz:
            intersects = intersects.union(self.cells[7].checkPoint(point))
        if ltx and gty and gtz:
            intersects = intersects.union(self.cells[0].checkPoint(point))
        if ltx and gty and ltz:
            intersects = intersects.union(self.cells[4].checkPoint(point))
        if ltx and lty and gtz:
            intersects = intersects.union(self.cells[2].checkPoint(point))
        if ltx and lty and ltz:
            intersects = intersects.union(self.cells[6].checkPoint(point))
        return intersects

    def checkCollisions(self, failed=set(), collided=set()):
        """The collided set will be updated and returned"""
        for cell in self.cells:
            cell.checkCollisions(failed, collided)
        return collided

    def printTree(self, depth=0):
        print(depth*"--" + "tree")
        for cell in self.cells:
            cell.printTree(depth=depth+1)


class Leaf:
    """The lowest level of the octree which contains the actual objects"""
    def __init__(self, position, dimensions):
        self.pos = position
        self.dim = dimensions
        self.contents = []
        self.minDim = [float("inf"), float("inf"), float("inf")]

        #  To visualise the tree. WARNING: Very slow
        """bpy.ops.mesh.primitive_cube_add()
        ob = bpy.context.object
        ob.draw_type = 'WIRE'
        ob.dimensions = self.dim
        ob.location = (self.pos[0] + (self.dim[0]/2),
                           self.pos[1] + (self.dim[1]/2),
                           self.pos[2] + (self.dim[2]/2))"""

    def add(self, item):
        """Add a new object to this leaf of the octree. If there is already a
        node in this leaf then return true indicates a request to split this
        leaf into an octree."""
        self.contents.append(item)
        self.minDim = [min(self.minDim[x], item.dim[x]) for x in range(3)]
        if len(self.contents) > 2:
            for minD, D in zip(self.minDim, self.dim):
                if D/4 < minD:
                    return False
            return True
        return False

    def checkPoint(self, point):
        """Which objects is this point in?"""
        result = set()
        for item in self.contents:
            if item.checkPoint(point):
                result.add(item.original)
        return result

    def checkCollisions(self, failed, collided):
        """Tested is a dictionary {pair with lower name first: boolean}"""
        for outer in self.contents:
            for inner in self.contents:
                if outer != inner:
                    f = lambda x : x.original
                    key = (min(outer, inner, key=f), max(outer, inner, key=f))
                    if key not in failed and key not in collided:
                        if outer.checkCollisionWithBB(inner):
                            collided.add(key)
                        else:
                            failed.add(key)

    def printTree(self, depth=0):
        print(depth*"--", [c.original for c in self.contents])



if __name__ == "__main__":
    """
    bbs = []
    for ob in bpy.context.scene.objects:
        bbs.append(boundingBoxFromBPY(ob))
    """
    bbs = []
    for ob in bpy.context.scene.objects:
        bbs.append(boundingSphereFromBPY(ob))

    import time
    t = time.time()
    for f in range(10):
        O = createOctree(bbs)
    #print("Time to construct quad tree", time.time() - t)
    print(time.time() - t)
    # E = bpy.context.scene.objects["Empty"]
    # pos = (E.location.x, E.location.y, E.loxcation.z)
    import random
    pos = [(random.random()*100-50, random.random()*100-50, random.random()*100-50) for x in range(10000)]
    t = time.time()
    for f in range(10000):
        O.checkPoint(pos[f])
    #print("Time to check 1000 points", time.time() - t)
    print(time.time() - t)
    # AO.printTree()
    t = time.time()
    for f in range(10):
        O.checkCollisions()
    #print("Time to find all boundingbox collision:", time.time() - t)
    print(time.time() - t)
    print(len(O.checkCollisions()))