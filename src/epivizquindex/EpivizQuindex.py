import os
from hilbertcurve.hilbertcurve import HilbertCurve

import pickle
import sys
import math
import json
import pandas
from epivizquindex.utils import hcoords, range2bbox
from epivizquindex.QuadTree import Index
# from utils import hcoords, range2bbox
# from QuadTree import Index
from epivizFileParser import BigWig
from epivizFileParser.utils import toDataFrame
import struct

__author__ = "Jayaram Kancherla"
__copyright__ = "Jayaram Kancherla"
__license__ = "mit"


class EpivizQuindex(object):

    def __init__(self, genome, max_depth=20, max_items=256, base_path = os.path.join(os.getcwd(), 'quIndex/')):
        '''
        Initialization of Quindex object.

            Parameters:
            - **genome (dict)**:     dictionary with size of each chromosome in the genome.
            - **max_depth (int)**: maximum depth of the Quindex.
            - **max_items (int)**: maximum number of items in a node before splitting.
            - **base_path (str)**: path to the index folder. If the index is precomputed, you need to set this path to the folder to load the Quindex.

            Returns:
                    
        '''
        self.file_mapping = []
        self.file_objects = {}
        # self.file_chrids = {}
        self.genome = genome
        self.max_items = max_items
        self.max_depth = max_depth
        self.base_path = base_path
        self.file_counter = 0
        self.trees = {}
        if not os.path.exists(base_path):
            os.mkdir(base_path)


    def get_file_btree(self, file, zoomlvl = -2):
        '''
        Return the btree of the bigwig file at the lowest level.

            Parameters:
            - **file (str)**:       file path .
            - **zoomlvl (int)**:    zoom level of the btree.

            Returns:
            - **tree (bytes)**:       btree of the bigwig file in the given zoom level.
            - **bw (object)**:        bigwig file object.
        '''
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
        '''
        Return the node header of the given offest in the btree

            Parameters:
            - **tree (bytes)**:     btree from bigwig file.
            - **offset (int)**:     offest to the node in btree.
            - **endian (char)**:    endian of the parse file.

            Returns:
            - **result (dict)**:    header of the node.            
        '''
        data = tree[offset:offset + 4]
        (rIsLeaf, rReserved, rCount) = struct.unpack(endian + "BBH", data)
        return {"rIsLeaf": rIsLeaf, "rCount": rCount, "rOffset": offset + 4}

    def traverse_nodes(self, node, zoomlvl = -2, tree = None, result = [], fullIndexOffset = None, endian="="):
        '''
        Recursively traverse and return the value in the btree.

            Parameters:
            - **node (dict)**:            node header.
            - **zoomlvl (int)**:          zoomlevel of the node.
            - **tree (bytes)**:           btree from bigwig file.
            - **result (list)**:          recursive result array to store the parsed leaf nodes.
            - **fullIndexOffset (int)**:  full index offset of the bigwig file.
            - **endian (char)**:          endian of the parse file.

            Returns:
            - **result (list)**:          recursive result array to store the parsed leaf nodes.        
        '''
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
        '''
        read the leaf node in the bigwig btree.

            Parameters:
            - **tree (bytes)**:    btree from bigwig file.
            - **bw (object)**:     bigwig file object.
            - **zoomlvl (int)**:   zoomlevel of the node.

            Returns:
            - **df (DataFrame)**:  Data frame of btree nodes' values.        
        '''
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
        '''
        Return the chromosomes in the given bigwig file.

            Parameters:
            - **bw (object)**:     bigwig file object.

            Returns:
            - **chrmIds (dict)**:  dictionary mapping of chromosome to IDs in the file.        
        '''
        bw.getId("chr2")
        return bw.chrmIds

    def add_to_index(self, file, zoomlvl = -2):
        '''
        Add a file to Quindex.

            Parameters:
            - **file (str)**:     file path.

            Returns:
                           
        '''
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
        '''
        Save the current index to the path that is stored when creating the Quindex object.

            Parameters:

            Returns:
       
        '''
        for chrm in self.trees.keys():
            if self.trees.get(chrm) != None:
                self.trees[chrm].to_disk(os.path.join(self.base_path,  "quadtree."+ chrm + ".index"))
        with open(os.path.join(self.base_path, "quadtreeKeys.index"), 'wb') as pickle_file:
            pickle.dump(list(self.trees.keys()), pickle_file)
        with open(os.path.join(self.base_path,  "quadtreeFileMaps.index"), 'wb') as pickle_file:
            pickle.dump(self.file_mapping, pickle_file)

    def from_disk(self, load = True):
        '''
        load the current index to the path that is stored when creating the Quindex object.

            Parameters:
            - **load (bool)**: a boolean indicating whether the Index backbone is newly created. By default this should be true.

            Returns:
       
        '''
        with open(os.path.join(self.base_path, "quadtreeKeys.index"), 'rb') as pickle_file:
            keys = pickle.load(pickle_file)
        with open(os.path.join(self.base_path,  "quadtreeFileMaps.index"), 'rb') as pickle_file:
            self.file_mapping = pickle.load(pickle_file)
        for chrm in keys:
            path = os.path.join(self.base_path,  "quadtree."+ chrm + ".index")
            # this check might not be necessary
            if os.path.exists(path):
                # print(path, load)
                self.trees[chrm] = Index(disk = path, first_run = load)

    def fetch_entries(self, fileid, df, chrm, start, end, zoomlvl):
        '''
        Fetch entries from a file.

            Parameters:
            - **fileid (int)**: id of the file stored in Quindex.
            - **df (DataFrame)**: Data Frame contains results from Quindex query.
            - **chrm (str)**: target chromosome.
            - **start (int)**: start location of the query range.
            - **end (int)**: end location of the query range.
            - **zoomlvl (int)**: zoom lvl of the query range.

            Returns:
                result (Data Frame): Data Frame containing the fetched entries sorte by start location.
       
        '''
        df_search = df[df["fileid"] == fileid]
        file = self.file_mapping[fileid]
        if self.file_objects.get(file) != None:
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
        '''
        Query the given range in the Quindex.

            Parameters:
            - **chrm (str)**: target chromosome.
            - **start (int)**: start location of the query range.
            - **end (int)**: end location of the query range.
            - **zoomlvl (int)**: zoom lvl of the query range.
            - **in_memory (bool)**: Boolean indicating whether the search in performed in memory.
            - **file (string)**: path to the file. If this is provided, the query will only return searches related to this file.

            Returns:
                result (Data Frame): Data Frame containing the fetched entries sorte by start location.
       '''
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
            return pandas.concat(dfs, axis = 0) if len(dfs) > 0 else pandas.DataFrame()


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