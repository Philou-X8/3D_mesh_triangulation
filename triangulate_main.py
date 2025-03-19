'''
-----------------------------------------------------------------------------------------
File: triangulate_main.py
source: https://github.com/Philou-X8/3D_mesh_triangulation

[triangulate_main.py] is responsible for reading, writing and traversing USD files.
-----------------------------------------------------------------------------------------
'''

from pxr import Usd, UsdGeom
from triangulate_quad import *
from triangulate_ngon import *


def CreateStage(baseFileName : str, outFileName : str = 'testing_mesh_dst.usda', containerFile : str = 'testing_mesh_container.usda') -> Usd.Stage:
    """
    Open and create the USD files.

    args:
        baseFileName - Name of the file to read from.
        outFileName - Name of the file to write to.
        containerFile - Name of a container file where both USD are overlapped for easy comparison. (Can be empty to skip.)
    return:
        Usd.Stage - USD Stage for triangulated meshes.
    """
    baseStage = Usd.Stage.Open(baseFileName)
    baseIdentifier = baseStage.GetRootLayer().identifier

    # make output file
    writeStage = Usd.Stage.CreateNew(outFileName)
    writeStage.GetRootLayer().subLayerPaths.append(baseIdentifier)
    outIdentifier = writeStage.GetRootLayer().identifier
    
    # make container file
    if (containerFile != None) and (containerFile != ''):
        container = Usd.Stage.CreateNew(containerFile)
        container.GetRootLayer().subLayerPaths.append(outIdentifier)
        container.GetRootLayer().subLayerPaths.append(baseIdentifier)
        container.GetRootLayer().Save()

    return writeStage


def TriangulateMesh(mesh : UsdGeom.Mesh):
    """
    Triangulate a mesh and regenerate Lookup Tables for primvars of this mesh

    args:
        mesh - mesh to triangulate.
    return:
        lookup_uniform (list) - LUT used to triangulate attribute/primvars of uniform interpolation.
        lookup_faceVarying (list) - LUT used to triangulate attribute/primvars of faceVarying interpolation.
    """
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
    """
    For iterating through a mesh and dividing it up in polygons.

    args:
        src_counts - list of number of side per face.
        src_indicies - list of all vertex indicies.
        src_points - list of points of the mesh.
    return:
        faceOffset (int) - index of the face.
        vertOffset (int) - index of the first vertex of the face.
        subPoints (list) - list of points making up the face.
    """
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
    """
    Triangulate a face.

    args:
        points - list of points making up the face.
    return:
        faceCounts (list) - list of number of side per generated triangles.
        cornerIDs (list) - list pointing to vertex of the original polygon.
    """
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
    """
    Apply the triangulation to a primvar
    """
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
    """
    Apply the triangulation to the Normals attribute
    """
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