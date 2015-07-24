#
# This script uses RaspberryJamMod's ability to capture all hits, not just sword hits, to provide symmetric
# drawing. Stand at the center of symmetry. By default, you get north-south and east-west mirroring, but you
# can include other transformations on the commandline:
#
#    n : northsouth flip
#    e : east west flip
#    u : up down flip
#    nw : nw - se flip
#    ne : ne - sw flip
#
#    90 : 90, 180 and 270 degrees in the plane
#    180 : 180 degrees in the plane
#
#  You can do translational symmetry with:
#    t N x y z : translate N-1 times by vector (x,y,z)
#
#  The transformations are combined in a complicated fashion to generate the list of all applied transformations. 
#  Effectively this works like this:
#  1. The group generated by all the rotations and flips is put into the list. 
#  2. For each translational symmetry "t N x y z", the list is updated as follows: For each transformation F on the list 
#     so far, the N-1 transformations lambda (x1,y1,z1) : F(x1,y1,z1) + (kx,ky,kz) are added to the list, for k from 1 to N-1.
#  3. The identity transformation is removed.
#
#  Then whenever you draw or erase a block, all the transforms of that block location are are also drawn or erased.
#
#  For instance, specifying n e t 10 0 1 0 will do north-south and east-west mirroring, plus raising up pillars 10 high on
#  top of whatever you draw. On the other hand, doing t 10 1 0 0 t 10 0 1 0 t 10 0 0 1 will draw 10x10x10 cubes wherever you
#  draw.
# 


#
# Code by Alexander Pruss under MIT license.
#

from mcpi.minecraft import Minecraft
import mcpi.block as block
from functools import partial
import sys
import time

xn = ( (1,0,0), 
       (0,1,0),
       (0,0,-1) )
xe = ( (-1,0,0),
       (0,1,0),
       (0,0,1) )
xu = ( (1,0,0),
       (0,-1,0),
       (0,0,-1) )
xnw = ( (0,0,-1),
        (0,1,0),
        (-1,0,0) )
xne = ( (0,0,1),
        (0,1,0),
        (1,0,0 ) )
x90 = ( (0,0,1),
        (0,1,0),
        (-1,0,0) )
xid = ( (1,0,0),
        (0,1,0),
        (0,0,1) )

faces = ( (0,-1,0), (0,1,0), (0,0,-1), (0,0,1), (-1,0,0), (1,0,0), (0,0,0) )

def mulMat(a,b):
    return tuple(tuple(a[i][0]*b[0][j]+a[i][1]*b[1][j]+a[i][2]*b[2][j] for j in range(3)) for i in range(3))

def mulMatVec(a,b):
    return tuple(a[i][0]*b[0]+a[i][1]*b[1]+a[i][2]*b[2] for i in range(3))

def subVec(a,b):
    return tuple(a[i]-b[i] for i in range(3))

def addVec(a,b):
    return tuple(a[i]+b[i] for i in range(3))

x180 = mulMat(x90,x90)

if __name__ == "__main__":
    def copy(v,airOnly=False):
        b = mc.getBlockWithNBT(v)
        if airOnly and b.id != block.AIR.id:
            return
        v1 = addVec(v,(0.5,0.5,0.5))
        for t in transforms:
            mc.setBlockWithNBT(t(v1),b)

    def err():
        mc.postToChat("Invalid symmetry specification. See symmetry.py comments.")
        exit()

    mc = Minecraft()

    playerPos = mc.player.getPos()

    matrices = set()
    translations = []

    if len(sys.argv) <= 1:
        matrices.add(xn)
        matrices.add(xe)

    i = 1
    while i < len(sys.argv):
        opt = sys.argv[i]
        i += 1
        if opt == 't':
            if len(sys.argv) <= i + 3:
                err()
            translations.append((int(sys.argv[i]), float(sys.argv[i+1]), float(sys.argv[i+2]), float(sys.argv[i+3])))
            i += 4
        elif opt == 'n':
            matrices.add(xn)
        elif opt == 'e':
            matrices.add(xe)
        elif opt == 'u':
            matrices.add(xu)
        elif opt == 'nw':
            matrices.add(xnw)
        elif opt == 'ne':
            matrices.add(xne)
        elif opt == '90':
            matrices.add(x90)
        elif opt == '180':
            matrices.add(x180)

    matrices.add(xid)
    old = set()
    while len(old) < len(matrices):
        old = matrices
        matrices = set()
        for a in old:
            for b in old:
                matrices.add(mulMat(a,b))
    matrices.remove(xid)

    transforms = []
    matrixApply = lambda v,mat : addVec(mulMatVec(mat,subVec(v,center)),center)
    for m in matrices:
        transforms.append(partial(matrixApply, mat=m))

    for t in translations:
        add = []
        for k in range(1,t[0]):
            delta = (t[1]*k,t[2]*k,t[3]*k)
            f = partial(addVec,b=delta)
            add.append(f)
            for g in transforms:
                add.append(lambda v,f=f,g=g : f(g(v)))
        transforms += add

    center = tuple(0.5 * round(2 * x) for x in playerPos)

#    if (len(matrices) > 0):
#        mc.conn.send("world.spawnParticle", "footstep", center, 0.0,0.0,0.0, 0, 1)

    mc.conn.send("events.setting","restrict_to_sword",0)

    mc.postToChat("Will be drawing {} copies".format(1+len(transforms)))

    mc.events.clearAll()

    while True:
        hits = mc.events.pollBlockHits()
        time.sleep(0.25)
        for h in hits:
            v = tuple(x for x in h.pos)
            copy(v,airOnly=True)
            copy(addVec(v,faces[h.face]))
