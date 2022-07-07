from hilbertcurve.hilbertcurve import HilbertCurve
import requests
import math

avaliable_typles = ['mm10', 'mm9', 'hg19', 'hg38']

def hcoords(x, chromLength, dims = 2):
    '''
    Returns hilbert space coordinate of the input query.

            Parameters:
            - **x (int)**:            A integer representing the query location in a chromosome.
            - **chromLength (int)**:  The total length of the chromosome.
            - **dims (int)**:         dimension of the hilbert space, by default we use 2d hilbert space.

            Returns:
            - **x (int)**:        x coordinate in hilbert space.
            - **y (int)**:        y coordinate in hilbert space.
            - **hlevel (int)**:   level of the hilbert space.
    '''
    hlevel = math.ceil(math.log2(chromLength)/dims)
    # print("hlevel, ", hlevel)
    hilbert_curve = HilbertCurve(hlevel, dims)
    [x,y] = hilbert_curve.points_from_distances([x])[0]
    return x, y, hlevel

# query : dictionary with 2 items, start and end
def range2bbox(hlevel, query, dims = 2, margin = 0):
    '''
    Convert the input query chromosome range to query bounding box in hilbert space.

            Parameters:
            - **hlevel (int)**:       level of the hilbert space, calculated by the size of the chromosome.
            - **query (dict)**:       dictionary of a query range, with "start" and "end" representing the query range in a chromosome.
            - **dims (int)**:         dimension of the hilbert space, by default we use 2d hilbert space.
            - **margin (int)**:       margin of the query box in hilbert space.

            Returns:
            - **bbox (tuple)**: 4 integers representing the lower left and top right coordinate. The order is lower left x, y, then top right x, y.
    '''
    # now = time.time()
    # query = {
    #     "start": 0,
    #     "end":  127074
    #     }
    hilbert_curve = HilbertCurve(hlevel, dims)
    inc = 0
    # ite = 0
    start = query["start"]+1
    points = []
    if start%4 == 1:
        points.append(start)
        start += 1
    if start%4 == 2:
        points.append(start)
        start += 1
    if start%4 == 3: 
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
    # for point in points:
    for h_point in hilbert_curve.points_from_distances(points):
        [x, y] = h_point
        # print(x, y, point)
        hillcorX.append(x)
        hillcorY.append(y)
    bbox = (min(hillcorX) - margin, min(hillcorY) - margin, max(hillcorX) + margin, max(hillcorY) + margin)
    # print(bbox)
    # print(time.time() - now)
    return bbox

def get_genome(t):
    '''
    Get the range of chromosomes of the given type. Currently these are read from hgdownload.cse.ucsc.edu.

            Parameters:
            - **t (str)**:       type of gene.

            Returns:
            - **genome (dict)**: Dictionary of the range of the chromosome for the given type.
    '''
    genome = {}
    if t not in avaliable_typles:
        exception('unsupported genome type')
    target_url = "http://hgdownload.cse.ucsc.edu/goldenpath/{}/bigZips/{}.chrom.sizes".format(t, t)
    response = requests.get(target_url)
    data = response.text
    for line in data.split('\n'):
        if 'random' in line or len(line) < 3:
            continue
        chrm, num = line.split('\t')
        genome[chrm] = int(num)
    return genome