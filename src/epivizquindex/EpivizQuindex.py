import os
from hilbertcurve.hilbertcurve import HilbertCurve

import pickle
import sys
import math
import json
import pandas
import seaborn as sns
pandas.set_option('display.width', 1000)
from epivizquindex.utils import hcoords, range2bbox
from epivizquindex.QuadTree import Index
# from utils import hcoords, range2bbox
# from QuadTree import Index
from epivizFileParser import BigWig
from epivizFileParser.utils import toDataFrame
import matplotlib.ticker as ticker
import struct
import time

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
                # x_start, y_start, _ = hcoords(row["rStartBase"], chromLength)
                _, _, hlevel = hcoords(row["rEndBase"], chromLength)
                bbox = range2bbox(hlevel, {"start":row["rStartBase"], "end":row["rEndBase"]})
                # print("\t\t bbox", bbox)
                # bbox = (x_start, y_start, x_end, y_end)
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

    def fetch_entries(self, file_name, df, chrm, start, end, zoomlvl):
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

        df_search = df[df["file_name"] == file_name]
        if self.file_objects.get(file_name) != None:
            bw = self.file_objects[file_name]
        else:
            bw = BigWig(file_name)
            # bw.getHeader()
            # bw.getId("chr2")
            self.file_objects[file_name] = bw
        chrmId = bw.getId(chrm)

        result = []
        for i, row in df_search.iterrows():
            result += bw.parseLeafDataNode(chrmId, start, end, zoomlvl, chrmId, row["start"], chrmId, row["end"], row["offset"], row["size"])

        # result = toDataFrame(result, bw.columns)
        # result["chr"] = chrm
        # result = result.sort_values(by = ['start'])

        return result, bw.columns

    def get_records(self, chrm, start, end, zoomlvl = -2, in_memory = True, debug = False):
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
        # t = time.time()
        matches = tree.intersect(overlapbbox, in_memory = in_memory, debug = debug)
        # print("tree times: ", time.time() - t)
        df = pandas.DataFrame(matches, columns=["start", "end", "offset", "size", "fileid"]) if not debug else pandas.DataFrame(matches, columns=["start", "end", "offset", "size", "fileid", 'r1', 'r2', 'r3', 'r4'])
        df = df.loc[df['start'] <= end]
        df = df.loc[df['end'] >= start]
        df = df.replace({"fileid": {v: k for v, k in enumerate(self.file_mapping)}}).rename(columns={"fileid": "file_name"})

        return df


    def has_data(self, chrm, start, end, zoomlvl = -2, in_memory = True, file_names = None):
        records = self.get_records(chrm, start, end, zoomlvl, in_memory).drop(columns=['offset', 'size'])
        if file_names is not None:
            return records.loc[records['file_name'].isin(file_names)]
        return records

    def hit(self, chrm, start, end, zoomlvl = -2, in_memory = True, file_names = None):
        records = self.get_records(chrm, start, end, in_memory=in_memory).drop(columns=['offset', 'size'])
        file_names = self.file_mapping if file_names == None else file_names
        result = [len(records.loc[records['file_name'] == f]) > 0 for f in file_names]
        return pandas.DataFrame({'file_name': file_names, 'hit': result})

    def query(self, chrm, start, end, zoomlvl = -2, in_memory = True, file_names = None):
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
        records = self.get_records(chrm, start, end, zoomlvl, in_memory)

        # if file_names != None:
        #     entries, columns = self.fetch_entries(file_names, records, chrm, start, end, zoomlvl)
        #     result = toDataFrame(entries, columns)
        #     result["chr"] = chrm
        #     result = result.sort_values(by = ['start'])
        #     return result
        #     # print(fileid)
        #     # print(matches)

        # # returning all files
        # else:
        dfs = []
        partial_result = []
        # t = time.time()
        for file_name in records.file_name.unique():
            if (file_names is not None) and not (file_name in file_names):
                continue
            entries, columns = self.fetch_entries(file_name, records, chrm, start, end, zoomlvl)
            partial_result=pandas.DataFrame(entries, columns=columns)
            partial_result["file_name"] = file_name
            dfs.append(partial_result)

        dfs = pandas.concat(dfs, axis = 0) if len(dfs) > 0 else pandas.DataFrame()
        dfs["chr"] = chrm

        return dfs.sort_values(by = ['file_name', 'start']) if len(dfs) > 0 else dfs

    def plot_helpper(self, chrm, start, end, zoomlvl = -2, in_memory = True, file_names = None, num_bins = 100, show_missing = True):
        records = self.query(chrm, start, end, in_memory = in_memory, file_names = file_names)
        show_missing = -1 if show_missing else 0
        entries = {}
        bin_size = (end-start)/num_bins
        file_names = self.file_mapping if file_names == None else file_names
        for file_name in file_names:
            entries[file_name] = []
            e = records.loc[records['file_name'] == file_name]
            x = start
            while x < end:
                # print(x,min(x+bin_size, end))
                tb = e.loc[e['start'] <= min(x+bin_size, end)]
                tb = tb.loc[tb['end'] > x]
                score = 0
                pointer = x
                for i, j in tb.iterrows():
                    next_pointer = min(x+bin_size, j['end'])
                    width = next_pointer - pointer
                    pointer = next_pointer
                    score += width * j['score']
                # print(x+bin_size - pointer)
                
                if score < 0:
                    print('file ', file_name, ' score ', score, ' position ', position)
                score += show_missing * (x+bin_size - pointer)
                entries[file_name].append(score/bin_size)
                x += bin_size
        columns = []
        formatter = ticker.EngFormatter()
    
        x = start
        while x < end:
            columns.append(formatter.format_eng(int(min(x+bin_size, end))))
            x += bin_size
        values = pandas.DataFrame(entries).transpose()
        values.columns = columns

        return values

    def region_plot(self, chrm, start, end, meta_data = None, column = 'type', zoomlvl = -2, in_memory = True, file_names = None, num_bins = 100, fig_size = (15,10), show_missing=True):
        values = self.plot_helpper(chrm, start, end, zoomlvl, in_memory, file_names, num_bins, show_missing)
        if meta_data is not None:
            values = values.join(meta_data[[column]]).groupby(column).mean()
        sns.set(rc={'figure.figsize':fig_size})
        if show_missing:
            return sns.heatmap(values, cmap="bwr", center=0, vmin=-1)
        else:
            return sns.heatmap(values, cmap="hot_r")



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