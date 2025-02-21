from pxr import Gf


def SplitQuad(points):
    sidesVect = [
        Gf.Vec3f(points[1]-points[0]),
        Gf.Vec3f(points[2]-points[1]),
        Gf.Vec3f(points[3]-points[2]),
        Gf.Vec3f(points[0]-points[3]),
    ]
    
    scoreA = Gf.Vec3f.GetDot(
        sidesVect[0] - sidesVect[2], 
        sidesVect[1] - sidesVect[3]
        )
    scoreB = Gf.Vec3f.GetDot(
        sidesVect[1] - sidesVect[3], 
        sidesVect[2] - sidesVect[0]
        )

    if scoreA >= scoreB:
        return [3,3], [3,0,1, 1,2,3]
    else:
        return [3,3], [0,1,2, 2,3,0]
    