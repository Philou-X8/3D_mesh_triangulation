Documentation is still WIP
# 3D mesh triangulation
This script is a solution to the challenge of triangulating a mesh containing polygons of weird shape and side count. It uses the Universal Scene Description (USD) format to represent 3D models.

### Table Of Content
1. Triangulation process

    1.1 N-gon triangulation

    1.2 Quad triangulation

2. Code implementation


# Triangulation Process
Two triangulation algorithm are offered: one for quads and one for n-gon.

## N-gon triangulation
The triangulation algorithm of n-gon is inspired by the ear clipping algorithm for triangulating 2D polygons. The full refeference can be found [https://www.geometrictools.com/Documentation/TriangulationByEarClipping.pdf](here).

Simply put, if you take any corner of the polygon, you can form a triangle with this corner and its two adjacent corners. 
Then, if you remove this corner, you can close the polygon by conecting the left adjacent corner to the right adjacent corner.
This form a new side. 
You now have a triangle and a new new polygon with one less sides. You can repeat this process until you only have triangles.

The question that arrise is: *How do you chose which corner to remove?*

The 2D algorithm checks two things: \
(A) the corner is convex (its inside angle is less than 180 deg).\
(B) there is no other point (corner) inside the triangle formed by the 3 adjacent corners.

Both of these checks do not translate well to 3D. New constraints must be defined.

To address point (A), we can simply compare the face normal vector of the would-be triangle to the face normal vector of the original polygon. 
If they are pointing in the same direction, we have a convex corner. Otherwise, we have a concave corner.
We can tell that they are pointing in the same direction if the dot product of the two vector is greater than 0.

To address point (B), well, we cannot. At least, not in any light to compute way I know of. 
However, we can estimate if a given triangle should be safe to remove.
To do that, we check the angle of the corner and the lenght of the triangle's hypotenuse.
Small angle and small hypotenuse mean small triangles, which are overall less likely to contain another corner inside them.
It is also impossible for the smallest triangle to contain an even smaller one inside of it.

With those new metrics, it is now possible to trianglulate 3D n-gon. 
First assign a score to all corner based on the three metrics mentionned above (alignement of the triangle's normal, sharpness of the corner's angle, lenght of the formed hypothenus).
Then iteratively remove the corner with the highest score until you only have triangles.


## Quad triangulation
The triangulation process for quad is quite different, but the objective of providing a clean triangulation even with concave polygon remains the same.
Their occurence frequency and the strong prospect for optimisation are the driving factor behind the use of a different algorithm for them.

Quads will always have four sides, four corners and two diagonals. This mean there's always only 4 inputs and only 2 possible outcomes. 
As such, the goal of thier triangulation is simply to find which of the two diagonals should be used to split them in two.

What we are scoring, however, is not the diagonal itself, but the two corners on both sides of this diagonal.
If the average of their angle is small, their common hypothenus makes for a good diagonal. 
And a large angle make for a bad diagonal. 

To translate this to 3D, instead of finding the actual angle, we simply compute the dot product using the adjacent sides as vectors.
Now, to reduce the number of dot product needed, we put opposing sides end to end.
This adds up their vectors and give us one vector per pair. With only two vectors, the dot product is calculated only once.
The result of this dot product is the score of that diagonal.

The process is then repeated for the other diagonal, and the two score are compared. 
The quad is split along the diagonal with the highest (most positive) score.

# Code implementation
general information

## main.py
[triangulate_main.py]() is responsible for reading, writing and traversing USD files. Individual faces are passed to [triangulate_ngon.py]() or [triangulate_main.py]() for the triangulation process.

## quad.py
[triangulate_quads.py]() offer a light but efficient way of triangulating quads (4 sided polygons). It ensure that concave polygons are respected by choosing the best diagonal.

## ngon.py
[triangulate_ngon.py]() triangulate n-gon (polygons with more than 4 sides) in the most natural way it can. Once again, concavity is respected.
