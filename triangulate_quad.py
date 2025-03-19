from pxr import Gf


def SplitQuad(points):
    vectAB = Gf.Vec3f(points[1]-points[0]).GetNormalized()
    vectBC = Gf.Vec3f(points[2]-points[1]).GetNormalized()
    vectCD = Gf.Vec3f(points[3]-points[2]).GetNormalized()
    vectDA = Gf.Vec3f(points[0]-points[3]).GetNormalized()
    
    splitBD = Gf.Vec3f.GetDot(vectAB-vectCD, vectBC-vectDA)
    splitAC = Gf.Vec3f.GetDot(vectBC-vectDA, vectCD-vectAB)

    if splitBD >= splitAC:
        return [3,3], [3,0,1, 1,2,3]
    else:
        return [3,3], [0,1,2, 2,3,0]
    