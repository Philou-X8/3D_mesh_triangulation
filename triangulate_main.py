from pxr import Usd, UsdGeom
from triangulate_quad import *
from triangulate_ngon import *


def CreateStage(baseFileName : str, outFileName : str = 'testing_mesh_dst.usda', containerFile : str = 'testing_mesh_container.usda') -> Usd.Stage:
    baseStage = Usd.Stage.Open(baseFileName)
    baseIdentifier = baseStage.GetRootLayer().identifier

    # make output file
    writeStage = Usd.Stage.CreateNew(outFileName)
    writeStage.GetRootLayer().subLayerPaths.append(baseIdentifier)
    outIdentifier = writeStage.GetRootLayer().identifier
    
    # make container file
    container = Usd.Stage.CreateNew(containerFile)
    container.GetRootLayer().subLayerPaths.append(outIdentifier)
    container.GetRootLayer().subLayerPaths.append(baseIdentifier)
    container.GetRootLayer().Save()

    return writeStage


def TriangulateMesh(mesh : UsdGeom.Mesh):
    src_counts = mesh.GetFaceVertexCountsAttr().Get()
    src_indicies = mesh.GetFaceVertexIndicesAttr().Get()
    src_points = mesh.GetPointsAttr().Get()

    dst_count = []
    dst_indicies = []

    lookup_uniform = []
    lookup_faceVarying = []

    for faceData in GetNextFace(src_counts, src_indicies, src_points):
        faceOffset, vertOffset, facePoints = faceData

        sideCounts, cornerIDs = TriangulateFace(facePoints)

        dst_count.extend( sideCounts )
        dst_indicies.extend( [src_indicies[vertOffset + n] for n in cornerIDs] )

        lookup_uniform.extend( [faceOffset for n in sideCounts] )
        lookup_faceVarying.extend( [vertOffset + n for n in cornerIDs] )
    
    mesh.GetFaceVertexCountsAttr().Set( dst_count )
    mesh.GetFaceVertexIndicesAttr().Set( dst_indicies )

    return lookup_uniform, lookup_faceVarying


def GetNextFace(src_counts, src_indicies, src_points):
    faceOffset = 0
    vertOffset = 0
    while vertOffset < len(src_indicies):
        sideCount = src_counts[faceOffset]
        pointsLookup = src_indicies[vertOffset : vertOffset + sideCount]
        subPoints = [src_points[corner] for corner in pointsLookup]
        yield (faceOffset, vertOffset, subPoints)
        faceOffset += 1
        vertOffset += sideCount


def TriangulateFace(points):
    sideCount = len(points)
    faceCounts = []
    cornerIDs = []

    if sideCount <= 3:
        return [sideCount], list(range(sideCount))
    
    elif sideCount == 4:
        faceCounts, cornerIDs = SplitQuad(points)
        
    else:
        ngonSplitter = NgonSplitter(points)
        faceCounts, cornerIDs = ngonSplitter.Triangulate()
    
    return faceCounts, cornerIDs


def UpdatePrimvar(primvar : UsdGeom.Primvar, lookup):
    lookup_uniform, lookup_faceVarying = lookup
    src_primvar = []
    dst_primvar = []

    if primvar.GetInterpolation() == UsdGeom.Tokens.faceVarying:
        if primvar.IsIndexed():
            src_primvar = primvar.GetIndices()
            dst_primvar = [src_primvar[index] for index in lookup_faceVarying]
            primvar.SetIndices( dst_primvar )
        else:
            src_primvar = primvar.Get()
            dst_primvar = [src_primvar[index] for index in lookup_faceVarying]
            primvar.Set( dst_primvar )
    elif primvar.GetInterpolation() == UsdGeom.Tokens.uniform:
        if primvar.IsIndexed():
            src_primvar = primvar.GetIndices()
            dst_primvar = [src_primvar[index] for index in lookup_uniform]
            primvar.SetIndices( dst_primvar )
        else:
            src_primvar = primvar.Get()
            dst_primvar = [src_primvar[index] for index in lookup_uniform]
            primvar.Set( dst_primvar )


def UpdadeNormalsAttr(mesh : UsdGeom.Mesh, lookup):
    if src_normals := mesh.GetNormalsAttr().Get():
        lookup_uniform, lookup_faceVarying = lookup
        if mesh.GetNormalsInterpolation() == UsdGeom.Tokens.faceVarying:
            dst_normals = [src_normals[index] for index in lookup_faceVarying]
        elif mesh.GetNormalsInterpolation() == UsdGeom.Tokens.uniform:
            dst_normals = [src_normals[index] for index in lookup_uniform]
        mesh.GetNormalsAttr().Set(dst_normals)


if __name__ == "__main__":

    fileOriginal = 'testing_mesh_src.usda'
    fileOutput = 'testing_mesh_dst.usda'
    fileContainer = 'testing_mesh_container.usda'
    stage = CreateStage(fileOriginal, fileOutput, fileContainer)

    for prim in stage.Traverse():
        if mesh := UsdGeom.Mesh(prim):
            
            print(prim.GetPath())

            primvar_lookup = TriangulateMesh(mesh)
            
            UpdadeNormalsAttr(mesh, primvar_lookup)
            primvarAPI = UsdGeom.PrimvarsAPI(prim)
            for primvar in primvarAPI.GetPrimvarsWithValues():
                UpdatePrimvar(primvar, primvar_lookup)
                
    stage.GetRootLayer().Save()
    print('END')