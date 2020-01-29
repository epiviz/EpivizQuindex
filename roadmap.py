from pyqtree import Index
import pickle
import sys
import math
from hilbertcurve.hilbertcurve import HilbertCurve
import json
import pandas
import pickle
import time
import numpy
import zlib
import struct
from joblib import Parallel, delayed
import struct
import pandas
import json
import pickle

def hcoords(x, chromLength, dims = 2):
    hlevel = math.ceil(math.log2(chromLength)/dims)
    # print("hlevel, ", hlevel)
    hilbert_curve = HilbertCurve(hlevel, dims)
    [x,y] = hilbert_curve.coordinates_from_distance(x)
    return x, y, hlevel

chromosomes = {
    "chr1": 249250621, 
    "chr10": 135534747, 
    "chr11": 135006516, 
    "chr12": 133851895, 
    "chr13": 115169878, 
    "chr14": 107349540, 
    "chr15": 102531392, 
    "chr16": 90354753, 
    "chr17": 81195210, 
    "chr18": 78077248, 
    "chr19": 59128983, 
    "chr2": 243199373, 
    "chr20": 63025520, 
    "chr21": 48129895, 
    "chr22": 51304566, 
    "chr3": 198022430, 
    "chr4": 191154276, 
    "chr5": 180915260, 
    "chr6": 171115067, 
    "chr7": 159138663, 
    "chr8": 146364022, 
    "chr9": 141213431, 
    "chrM": 16571, 
    "chrX": 155270560, 
    "chrY": 59373566
}

f = open("quadtree/chrmids.json")
chromIndexes = json.loads(f.read())

fileIds = {}
idFiles = []
id = 0
for file in chromIndexes.keys():
    fileIds[file] = id
    idFiles.append(file)
    id = id + 1

def create_quadTree(chr):
    print("processing ", chr)
    chromLength = chromosomes[chr]
    dims = 2
    hlevel = math.ceil(math.log2(chromLength)/dims)
    print("hlevel", hlevel)
    x_y_dim = math.ceil(math.pow(2, hlevel))
    print("max x|y =", x_y_dim)

    # f = open("quadtree/chrmids.json")
    # chromIndexes = json.loads(f)
    
    tree = Index(bbox=(0, 0, x_y_dim, x_y_dim), disk="quadtree/indexes/roadmap." + chr + ".quadtree.index", first_run=True)

    for file in chromIndexes.keys():
        print("\t file - ", file)
        if chr in chromIndexes[file]:
            chrmId = chromIndexes[file][chr]
            df = pandas.read_csv("quadtree/processed/" + file + ".leaves", 
                    header=0)
            df = df[df["rStartChromIx"] == chrmId]
            print("\t df shape - ", df.shape)
            for i, row in df.iterrows():
                # print(row)
                x_start, y_start, _ = hcoords(row["rStartBase"], chromLength)
                x_end, y_end, _ = hcoords(row["rEndBase"], chromLength)
                tree.insert((row["rStartBase"], row["rEndBase"], row["rdataOffset"], row["rDataSize"], fileIds[file]), (x_start, y_start, x_end, y_end))
        else:
            print("\t !!!!!!! chrm doesn't exist - ", file)

# for chr in chromosomes.keys():
# create_quadTree("chr10")

# Parallel(n_jobs = 5) (delayed(create_quadTree)(chr) for chr in chromosomes.keys())

def query_quadtree(chr, start, end, files):
    chromLength = chromosomes[chr]
    print("chromLength", chromLength)
    dims = 2
    hlevel = math.ceil(math.log2(chromLength)/dims)
    print("hlevel", hlevel)
    x_y_dim = math.ceil(math.pow(2, hlevel))
    print("max x|y =", x_y_dim)
    tree = Index(bbox=(0, 0, x_y_dim, x_y_dim), disk = "quadtree/indexes/roadmap." + chr + ".quadtree.index")

    xstart, ystart, _ = hcoords(start, chromLength)
    xend, yend, _ = hcoords(end, chromLength)

    print("xstart, ystart, xend, yend", xstart, ystart, xend, yend)
    margin = 10
    overlapbbox = (xstart - margin, ystart - margin, xend + margin, yend + margin)
    matches = tree.intersect(overlapbbox)

    df = pandas.DataFrame(matches, columns=["start", "end", "offset", "size", "fileid"])
    print("before file filter")
    print(df.shape)
    print(df)
    df = df[df["fileid"].isin(files)]
    print("after file filter")
    print(df.shape)
    print(df)
    return df

# chr = "chrY"
# start = 1000
# end =  100000

ranges = [
    # {
    #     "chr": "chr2",
    #     "start": 304689,
    #     "end":   318568
    # },
    {
        "chr": "chr10",
        "start": 100000,
        "end":  171000
    }
    # {
    #     "chr": "chrY",
    #     "start": 1000,
    #     "end":  5000
    # },
    # {
    #     "chr": "chr5",
    #     "start": 135000,
    #     "end":  156000
    # },
    # {
    #     "chr": "chr11",
    #     "start": 180000,
    #     "end":  190000
    # }
]

def get_file(file_id):
    print("file name is ", idFiles[file_id])
    f = open("quadtree/objects/" + idFiles[file_id] + ".pickle", "rb")
    bw = pickle.load(f)
    return(bw)

zoomlvl = -2
stime = time.time()
tfiles = [61, 354] 
# 159, 253, 186, 876]
for trange in ranges:
    print(trange)
    df = query_quadtree(trange["chr"], trange["start"], trange["end"], files = tfiles)
    # print(df.shape)
    # print(df.head())
    # result = []
    # print(numpy.unique(df["fileid"]))
    for i, row in df.iterrows():
        # print(row)
        bw = get_file(row["fileid"])
        # print(bw)
        file = idFiles[row["fileid"]]
        chrmId = chromIndexes[file][trange["chr"]]
        result = bw.parseLeafDataNode(chrmId, trange["start"], trange["end"], 
                        zoomlvl, chrmId, row["start"], chrmId, row["end"], 
                        row["offset"], row["size"])
        resultDf = pandas.DataFrame(result, columns = ["chr", "start", "end", "score"])
        print(resultDf.head())
        # exit();
    # print(result)
    
        # exit()
quadTime = time.time() - stime
print("using quadtree total time for 5 range queries across 6 files - ", quadTime)

# stime = time.time()
# for tfile in tfiles:
#     print(tfile)
#     bw = get_file(tfile)
#     for trange in ranges:
#         print(trange)
#         res, _ = bw.getRange(trange["chr"], trange["start"], trange["end"], zoomlvl = -2)
#         print(res.head())

# nTime = time.time() - stime
# print("individually parsing bigwigs. total time for 5 range queries across 6 files - ", nTime)


# print(df.shape)
# print(df.head())

# bw = self.file_objects[file]
# chrmId = bw.chrmIds[chr]

# result = []
# for i, row in df.iterrows():
#     result += bw.parseLeafDataNode(chrmId, start, end, zoomlvl, chrmId, row["start"], chrmId, row["end"], row["offset"], row["size"])

# result = toDataFrame(values, bw.columns)
# result["chr"] = chr

# overlapbbox = (0, 0, 2860, 2860)
# matches = tree.intersect(overlapbbox)
# print("intersect comes back")

# print(len(matches))

# # print(matches[0])
# print("all matched nodes")
# print("format is (start, end, offset, length, fileName)")
# for item in matches:    
#     print(item)
#     print(sys.getsizeof(item))
# # print(sys.getsizeof(data))