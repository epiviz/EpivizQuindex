import os
from hilbertcurve.hilbertcurve import HilbertCurve
from .QuadTree import Index
import pickle
import sys
import math
import json
import pandas
from epivizfileserver.parser import BigWig
import struct

class EpivizQuindex(object):

    def __init__(self, genome, max_depth=20, max_items=256, base_path = os.getcwd()):
        self.item_size = 72
        self.file_mapping = {}
        self.file_objects = {}
        # self.file_chrids = {}
        self.genome = genome
        self.max_items = max_items
        self.max_depth = max_depth
        self.base_path = base_path
        self.file_counter = 0

    def hcoords(self, x, chromLength, dims = 2):
        hlevel = math.ceil(math.log2(chromLength)/dims)
        # print("hlevel, ", hlevel)
        hilbert_curve = HilbertCurve(hlevel, dims)
        [x,y] = hilbert_curve.coordinates_from_distance(x)
        return x, y, hlevel

    def get_file_btree(self, file, zoomlvl):
        bw = BigWig(file)
        bw.getZoomHeader()
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
        records = self.traverse_nodes(root, zoomlvl, tree = tree, fullIndexOffset = findexOffset, endian = bw.endian)
        df = pandas.DataFrame(records, columns=["rStartChromIx", "rStartBase", "rEndChromIx", "rEndBase", 
                    "rdataOffset", "rDataSize"])
        return df

    def get_file_chr(self, bw):
        bw.getId("chr1")
        return bw.chrmIds

    def add_to_index(self, file, zoomlvl = -2):
        tree, bw = self.get_file_btree(file, zoomlvl)
        df = self.get_leaf_nodes(tree, bw, zoomlvl)
        chrmTree = self.get_file_chr(bw)

        self.file_mapping[file] = self.file_counter
        self.file_counter += 1
        self.file_objects[file] = bw

        for chrm in chrmTree.keys():
            chromLength = self.genome[chrm]
            dims = 2
            hlevel = math.ceil(math.log2(chromLength)/dims)
            # print("hlevel", hlevel)
            x_y_dim = math.ceil(math.pow(2, hlevel))
            # print("max x|y =", x_y_dim)
            tree = Index(bbox=(0, 0, x_y_dim, x_y_dim), disk = base_path + "quadtree." + chrm + ".index")

            chrmId = chrmTree[chrm]
            df = df[df["rStartChromIx"] == chrmId]
            # print("\t df shape - ", df.shape)
            for i, row in df.iterrows():
                x, y, _ = hcoords(row["rStartBase"], chromLength)
                tree.insert((row["rStartBase"], row["rEndBase"], row["rdataOffset"], row["rDataSize"], fileIds[file]), (x, y, x+1, y+1))

    def query(self, file, chr, start, end, zoomlvl = -2):
        chromLength = self.genome[chr]
        dims = 2
        hlevel = math.ceil(math.log2(chromLength)/dims)
        # print("hlevel", hlevel)
        x_y_dim = math.ceil(math.pow(2, hlevel))
        # print("max x|y =", x_y_dim)
        tree = Index(bbox=(0, 0, x_y_dim, x_y_dim), disk = base_path + "quadtree." + chr + ".index")

        xstart, ystart, _ = hcoords(start, chromLength)
        xend, yend, _ = hcoords(end, chromLength)

        overlapbbox = (start - 1, start - 1, end + 1, end + 1)
        matches = tree.intersect(overlapbbox)

        df = pandas.DataFrame(matches, columns=["start", "end", "offset", "size", "fileid"])
        df = df[df["fileid"] == self.file_mapping[file]]

        bw = self.file_objects[file]
        chrmId = bw.chrmIds[chr]

        result = []
        for i, row in df.iterrows():
            result += bw.parseLeafDataNode(chrmId, start, end, zoomlvl, chrmId, row["start"], chrmId, row["end"], row["offset"], row["size"])

        result = toDataFrame(values, bw.columns)
        result["chr"] = chr

        return result
