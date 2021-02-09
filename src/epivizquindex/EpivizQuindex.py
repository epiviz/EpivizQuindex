import os
from hilbertcurve.hilbertcurve import HilbertCurve
from QuadTree import Index
import pickle
import sys
import math
import json
import pandas
from epivizfileserver.parser import BigWig
from epivizfileserver.parser.utils import toDataFrame
import struct

__author__ = "Jayaram Kancherla"
__copyright__ = "Jayaram Kancherla"
__license__ = "mit"

def hcoords(x, chromLength, dims = 2):
    hlevel = math.ceil(math.log2(chromLength)/dims)
    # print("hlevel, ", hlevel)
    hilbert_curve = HilbertCurve(hlevel, dims)
    [x,y] = hilbert_curve.coordinates_from_distance(x)
    return x, y, hlevel

# query : dictionary with 2 items, start and end
def range2bbox(hlevel, query, dims = 2, margin = 0):
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

class EpivizQuindex(object):

    def __init__(self, genome, max_depth=20, max_items=256, base_path = os.getcwd()):
        self.item_size = 72
        self.file_mapping = []
        self.file_objects = {}
        # self.file_chrids = {}
        self.genome = genome
        self.max_items = max_items
        self.max_depth = max_depth
        self.base_path = base_path
        self.file_counter = 0
        self.trees = {}


    def get_file_btree(self, file, zoomlvl):
        bw = BigWig(file)
        bw.getHeader()
        bw.zooms = {}
        totalLevels = bw.header.get("zoomLevels")
        if totalLevels <= 0:
            return -2, bw.header.get("fullIndexOffset")
            
        data = bw.zoomBin
        # if data is None:
        #     data = self.get_bytes(64, totalLevels * 24)
        
        for level in range(0, totalLevels):
            ldata = data[level*24:(level + 1)*24]
            (reductionLevel, reserved, dataOffset, indexOffset) = struct.unpack(bw.endian + "IIQQ", ldata)
            bw.zooms[level] = [reductionLevel, indexOffset, dataOffset]
            
        # buffer placeholder for the last zoom level
        bw.zooms[totalLevels - 1].append(-1)
        # set buffer size for other zoom levels
        for level in range(0, totalLevels - 1):
            bw.zooms[level].append(bw.zooms[level + 1][2] - bw.zooms[level][1])        
        tree = bw.getTree(-2)
        return tree, bw
    
    def read_node(self, tree, offset, endian="="):
        data = tree[offset:offset + 4]
        (rIsLeaf, rReserved, rCount) = struct.unpack(endian + "BBH", data)
        return {"rIsLeaf": rIsLeaf, "rCount": rCount, "rOffset": offset + 4}

    def traverse_nodes(self, node, zoomlvl = -2, tree = None, result = [], fullIndexOffset = None, endian="="):
        offset = node.get("rOffset")
        if node.get("rIsLeaf"):
            for i in range(0, node.get("rCount")):
                data = tree[offset + (i * 32) : offset + ( (i+1) * 32 )]
                (rStartChromIx, rStartBase, rEndChromIx, rEndBase, rdataOffset, rDataSize) = struct.unpack(endian + "IIIIQQ", data)
                result.append((rStartChromIx, rStartBase, rEndChromIx, rEndBase, rdataOffset, rDataSize))
        else:
            for i in range(0, node.get("rCount")):
                data = tree[offset + (i * 24) : offset + ( (i+1) * 24 )]
                (rStartChromIx, rStartBase, rEndChromIx, rEndBase, rdataOffset) = struct.unpack(endian + "IIIIQ", data)
                
                # remove index offset since the stored binary starts from 0
                diffOffset = fullIndexOffset
                childNode = self.read_node(tree, rdataOffset - diffOffset, endian)
                self.traverse_nodes(childNode, zoomlvl, result=result, tree = tree, 
                    fullIndexOffset = fullIndexOffset, endian = endian)
        return result

    def get_leaf_nodes(self, tree, bw, zoomlvl):
        findexOffset = bw.header.get("fullIndexOffset")
        offset = 48
        root = self.read_node(tree, offset, endian = bw.endian)
        records = self.traverse_nodes(root, zoomlvl, tree = tree, result = [], fullIndexOffset = findexOffset, endian = bw.endian)
        # print(hex(id(records)))
        df = pandas.DataFrame(records, columns=["rStartChromIx", "rStartBase", "rEndChromIx", "rEndBase", 
                    "rdataOffset", "rDataSize"])

        # print(root)
        return df

    def get_file_chr(self, bw):
        bw.getId("chr2")
        return bw.chrmIds

    def add_to_index(self, file, zoomlvl = -2):
        tree, bw = self.get_file_btree(file, zoomlvl)
        df = self.get_leaf_nodes(tree, bw, zoomlvl)
        chrmTree = self.get_file_chr(bw)

        self.file_mapping.append(file)
        
        self.file_objects[file] = bw

        for chrm in chrmTree.keys():
            # print(chrm)
            chromLength = self.genome[chrm]
            
            if self.trees.get(chrm) == None:
                dims = 2
                hlevel = math.ceil(math.log2(chromLength)/dims)
                # print("hlevel", hlevel)
                x_y_dim = math.ceil(math.pow(2, hlevel))
                # print("max x|y =", x_y_dim)
                tree = Index(bbox=(0, 0, x_y_dim, x_y_dim))
                self.trees[chrm] = tree
            tree = self.trees[chrm]


            chrmId = chrmTree[chrm]
            df_chrmId = df[df["rStartChromIx"] == chrmId]
            # print(chrmId, df.head())
            # print("\t df shape - ", df.shape)
            for i, row in df_chrmId.iterrows():
                # x, y, _ = hcoords(row["rStartBase"], chromLength)
                x_start, y_start, _ = hcoords(row["rStartBase"], chromLength)
                x_end, y_end, hlevel = hcoords(row["rEndBase"], chromLength)
                # bbox = range2bbox(hlevel, {"start":row["rStartBase"], "end":row["rEndBase"]})
                # print("\t\t bbox", bbox)
                bbox = (x_start, y_start, x_end, y_end)
                tree.insert((row["rStartBase"], row["rEndBase"], row["rdataOffset"], row["rDataSize"], self.file_counter), bbox)
                # tree.insert((row["rStartBase"], row["rEndBase"], row["rdataOffset"], row["rDataSize"], fileIds[file]), (x, y, x+1, y+1))
            
        
        self.file_counter += 1

    def to_disk(self):
        for chrm in self.trees.keys():
            if self.trees.get(chrm) != None:
                self.trees[chrm].to_disk(self.base_path + "quadtree." + chrm + ".index")
        with open(self.base_path + "quadtreeKeys.index", 'wb') as pickle_file:
            pickle.dump(list(self.trees.keys()), pickle_file)
        with open(self.base_path + "quadtreeFileMaps.index", 'wb') as pickle_file:
            pickle.dump(self.file_mapping, pickle_file)

    def from_disk(self, load = True):
        with open(self.base_path + "quadtreeKeys.index", 'rb') as pickle_file:
            keys = pickle.load(pickle_file)
        with open(self.base_path + "quadtreeFileMaps.index", 'rb') as pickle_file:
            self.file_mapping = pickle.load(pickle_file)
        for chrm in keys:
            path = self.base_path + "quadtree." + chrm + ".index"
            # this check might not be necessary
            if os.path.exists(path):
                # print(path, load)
                self.trees[chrm] = Index(disk = path, first_run = load)

    def fetch_entries(self, fileid, df, chrm, start, end, zoomlvl):
        df_search = df[df["fileid"] == fileid]
        file = self.file_mapping[fileid]
        if self.file_objects.get(file) is not None:
            bw = self.file_objects[file]
        else:
            bw = BigWig(file)
            bw.getHeader()
            bw.getId("chr2")
            self.file_objects[file] = bw
        chrmId = bw.chrmIds[chrm]

        result = []
        for i, row in df_search.iterrows():
            result += bw.parseLeafDataNode(chrmId, start, end, zoomlvl, chrmId, row["start"], chrmId, row["end"], row["offset"], row["size"])

        result = toDataFrame(result, bw.columns)
        result["chr"] = chrm

        return result.sort_values(by = ['start'])

    def query(self, chrm, start, end, zoomlvl = -2, in_memory = True, file = None):
        chromLength = self.genome[chrm]
        dims = 2
        hlevel = math.ceil(math.log2(chromLength)/dims)
        # print("hlevel", hlevel)
        x_y_dim = math.ceil(math.pow(2, hlevel))
        # print("max x|y =", x_y_dim)
        # if in_memory:
        tree = self.trees[chrm]
        # else:
        #     tree = Index(bbox=(0, 0, x_y_dim, x_y_dim), disk = self.base_path + "quadtree." + chrm + ".index", first_run = True)

        xstart, ystart, _ = hcoords(start, chromLength)
        xend, yend, _ = hcoords(end, chromLength)
        overlapbbox = range2bbox(hlevel, {"start":start, "end":end}, margin = 0)
        # overlapbbox = (xstart - 1, ystart - 1, end + 1, end + 1)
        matches = tree.intersect(overlapbbox, in_memory = in_memory)

        df = pandas.DataFrame(matches, columns=["start", "end", "offset", "size", "fileid"])
        if file:
            fileid = self.file_mapping.index(file)
            return self.fetch_entries(fileid, df, chrm, start, end, zoomlvl)
            # print(fileid)
            # print(matches)

        # returning all files
        else:
            dfs = []
            for fileid in df.fileid.unique():
                partial_result = self.fetch_entries(fileid, df, chrm, start, end, zoomlvl)
                partial_result["file"] = self.file_mapping[fileid]
                dfs.append(partial_result)
            return pandas.concat(dfs, axis = 0)


# This is aiming for a generic index that can be used for generally all
# indices

# then we probabily need another format storing how item is stored

class genericIndex(object):
    """docstring for genericIndex"""
    def __init__(self, max_depth=20, max_items=256, base_path = os.getcwd()):
        # self.item_size = 72
        # self.file_mapping = {}
        # self.file_objects = {}
        # self.file_chrids = {}
        self.max_items = max_items
        self.max_depth = max_depth
        self.base_path = base_path
        # self.file_counter = 0