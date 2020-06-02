from hilbertcurve.hilbertcurve import HilbertCurve

def hcoords(x, chromLength, dims = 2):
    hlevel = math.ceil(math.log2(chromLength)/dims)
    print("hlevel, ", hlevel)
    hilbert_curve = HilbertCurve(hlevel, dims)
    [x,y] = hilbert_curve.coordinates_from_distance(x)
    return x, y, hlevel


# query : dictionary with 2 items, start and end
# query = {
#     "start": 0,
#     "end":  127074
#     }

def range2bbox(hlevel, query, dims = 2, margin = 0):
    
    hilbert_curve = HilbertCurve(hlevel, dims)
    inc = 0
    # ite = 0
    start = query["start"]+1
    points = []
    if start%4 is 1:
        points.append(start)
        start += 1
    if start%4 is 2:
        points.append(start)
        start += 1
    if start%4 is 3: 
        points.append(start)
        start += 1 
    points.append(start)

    # assume at this ppoint, start is always at the end of a level 0
    while start < query["end"] + 1:
        # ite += 1
        # print(inc)
        # locate the proper power incrementer
        # the incrementor indicates the maximum power of 4
        while start % (4**(inc+1)) == 0:
            inc += 1
        while inc >= 0:
            # to get min x, min y, max x, max y, it is necessary to
            # locate the diagnol coordinates.
            # the 3rd point of the thrid sub-quadrons is always diagnol
            # to the starting point.
            if start + (4**inc) <= query["end"] + 1:
                points.append(start + 1)
                displacement = 0
                for x in range(inc - 1, -1, -1):
                    # the following lines are equivalent, and does not
                    # improve any speed
                    # displacement = displacement | (0b01 << (2 * x))
                    displacement += 2 * 4 ** x
                points.append(start + displacement + 1)
                start += 4 ** inc
                break
            else:
                inc = inc - 1

    # print(points)
    hillcorX = []
    hillcorY = []
    for point in points:
        [x, y] = hilbert_curve.coordinates_from_distance(point)
        # print(x, y, point)
        hillcorX.append(x)
        hillcorY.append(y)
    bbox = (min(hillcorX) - margin, min(hillcorY) - margin, max(hillcorX) + margin, max(hillcorY) + margin)
    # print(bbox)
    # print(time.time() - now)
    return bbox