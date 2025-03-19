from pxr import Gf


class CornerStatus:
    valid = 0 # 
    '''corner is still part of the poly and its data is up to date'''
    outdated = 1 
    '''neighbor changed, score need to be recalculated'''
    removed = 2 
    '''corner already removed from the polygon'''


class CornerListItem:
    centerCornerId = 0 # ID of this corner (from 0 to N for a n-gon)
    centerPoint = 0 # coords in 3D space of this point (usefull for vector maths)
    leftCornerId = 0 # link (id) to the right (next) corner
    rightCornerId = 0 # link (id) the the left (previous) corner
    leftVect = Gf.Vec3f(1,1,1) # 3D vector from this point to the left one
    rightVect = Gf.Vec3f(-1,1,1) # 3D vector from this point to the right one
    
    status = CornerStatus.outdated
    normal = Gf.Vec3f(0,0,1) 
    diagonal = 0
    sharpness = 0
    alignement = 0
    score = 0
    
    def __init__(self, id, point):
        self.status = CornerStatus.outdated
        self.centerCornerId = id
        self.centerPoint = point
        self.leftCornerId = 0
        self.rightCornerId = 0

        self.normal = Gf.Vec3f(0,0,0) 
        self.diagonal = 0
        self.sharpness = 0
        self.alignement = 0
        self.score = 0

    def LinkLeft(self, leftId : int, leftPoint : Gf.Vec3f):
        self.leftCornerId = int(leftId)
        self.leftVect = Gf.Vec3f(leftPoint - self.centerPoint)

    def LinkRight(self, rightId : int, rightPoint : Gf.Vec3f):
        self.rightCornerId = int(rightId)
        self.rightVect = Gf.Vec3f(rightPoint - self.centerPoint)

    def UpdateScore(self, refNormal : Gf.Vec3f):
        diagonalVect = Gf.Vec3f(self.rightVect - self.leftVect)
        self.diagonal = diagonalVect.GetLength()

        leftNormalized = self.leftVect.GetNormalized()
        rightNormalized = self.rightVect.GetNormalized()
        
        self.sharpness = leftNormalized.GetDot(rightNormalized)
        if self.sharpness == -1: # 180 deg angle
            self.normal = Gf.Vec3f(0,0,0)
            self.alignement = -1.0 # removing this point early can softlock better subdivision
            return
        
        self.normal = rightNormalized.GetCross(leftNormalized)
        self.normal.Normalize()

        self.alignement = self.normal.GetDot(refNormal)
    
    def GetScore(self, normal : Gf.Vec3f, remain : float = 1.0, longestSide : float = 1.0) -> float:
        if self.status == CornerStatus.outdated:
            self.score = self.UpdateScore(normal)

            alignmentScore = self.alignement * ( remain**2)
            diagonalScore = ( 1.0 - (self.diagonal / longestSide) )
            self.score = ( 1.0 * self.sharpness) + ( 1.0 * alignmentScore ) + (0.5 * diagonalScore)
            cornerStr = str(self.centerCornerId) + " [" + str(self.sharpness) + ", " + str(alignmentScore) + ", " + str(diagonalScore) + "] ,"
            print(cornerStr)
            self.status = CornerStatus.valid
        
        return self.score


class CornerList:
    itemList = []
    itemListSize = 0

    def __init__(self, points):
        self.itemList = []
        self.itemListSize = len(points)
        for id in range(len(points)):
            self.itemList.append( CornerListItem(id, points[id]) )

            leftId = (id - 1) % self.itemListSize
            rightId = (id + 1) % self.itemListSize
            self.itemList[id].LinkLeft(leftId, points[leftId])
            self.itemList[id].LinkRight(rightId, points[rightId])
    
    def TraverseRemaining(self):
        for item in self.itemList:
            if item.status == CornerStatus.removed:
                continue
            yield item, self.itemListSize / len(self.itemList)
    
    def Item(self, id) -> CornerListItem:
        return self.itemList[id]
    
    def LeftItem(self, id) -> CornerListItem:
        return self.itemList[ self.itemList[id].leftCornerId ]
    
    def RightItem(self, id) -> CornerListItem:
        return self.itemList[ self.itemList[id].rightCornerId ]
    
    def PopItem(self, id):
        self.itemList[id].status = CornerStatus.removed
        self.itemListSize -= 1

        left = self.LeftItem(id)
        right = self.RightItem(id)

        left.status = CornerStatus.outdated
        right.status = CornerStatus.outdated

        left.LinkRight(right.centerCornerId, right.centerPoint)
        right.LinkLeft(left.centerCornerId, left.centerPoint)

        return [left.centerCornerId, id, right.centerCornerId]
    

class NgonSplitter:
    corners = None
    faceNormal = Gf.Vec3f(0,0,0)
    longestSide = 0
    
    def __init__(self, points):
        self.corners = CornerList(points)

        vect = []
        self.longestSide = 0
        for i in range(len(points)):
            vect.append( Gf.Vec3f(points[(i+1)%len(points)] - points[i]) )

            if vect[i].GetLength() > self.longestSide:
                self.longestSide = vect[i].GetLength()

        self.faceNormal = Gf.Vec3f(0,0,0)
        for i in range(len(vect)):
            left = vect[(i-1)%len(points)]
            right = vect[i]
            normal = Gf.Vec3f.GetCross(left, right).GetNormalized()
            # NOTE: this does not acount for face surface size, only point dencity
            # removing the GetNormalized() give normals closer to were most of the face is pointing
            
            self.faceNormal += normal
        self.faceNormal.Normalize()

    def FindBest(self) -> CornerListItem:
        bestScore = -5
        bestId = 0
        scoreStr = ""
        for corner, remain in self.corners.TraverseRemaining():
            # terminate early for the last triangle, it's ugly but faster
            if self.corners.itemListSize <= 3:
                return corner.centerCornerId

            score = corner.GetScore(self.faceNormal, remain, self.longestSide)
            if score > bestScore:
                bestScore = score
                bestId = corner.centerCornerId
            scoreStr += "[" + str(corner.centerCornerId) + " , " + str(score) + "] , "
        print("\n" + scoreStr + "\n")
        return bestId
    
    def Triangulate(self):
        faceCounts = []
        cornerIDs = []
        while self.corners.itemListSize >= 3:
            id = self.FindBest()
            cornerIDs.extend( self.corners.PopItem(id) )
            faceCounts.append( 3 )

        return faceCounts, cornerIDs