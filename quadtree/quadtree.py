import htmllistparse as ftp
from epivizfileserver.parser import BigWig
from joblib import Parallel, delayed
import struct
import pandas
import json
import pickle

url = "https://egg2.wustl.edu/roadmap/data/byFileType/signal/consolidated/macs2signal/foldChange/"
cwd, files = ftp.fetch_listing(url)

print("total files - ", len(files))

def get_file_index(file, baseurl):
    print("processing file - ", file.name)
    bw = BigWig(baseurl + file.name)
    print("\t getting zoom headers")
    bw.getZoomHeader()
    print("\t get tree for full data offset")
    tree = bw.getTree(-2)
    bw.getId("chr1")
    ofile = open("objects/" + file.name + ".pickle",  'wb')
    pickle.dump(bw, ofile)
    # ifile = "trees/" + file.name + ".fulltreeindex"
    # print("\t writing index ", ifile)
    # with open(ifile, "wb") as f:
    #     f.write(tree)

# This will download the index from all the files
Parallel(n_jobs = 10) (delayed(get_file_index)(file, url) for file in files)

def traverse_nodes(node, zoomlvl = -2, tree = None, result = [], fullIndexOffset = None, endian="="):
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
            childNode = read_node(tree, rdataOffset - diffOffset, endian)
            traverse_nodes(childNode, zoomlvl, result=result, tree = tree, 
                fullIndexOffset = fullIndexOffset, endian = endian)
    return result

def read_node(tree, offset, endian="="):
    data = tree[offset:offset + 4]
    (rIsLeaf, rReserved, rCount) = struct.unpack(endian + "BBH", data)
    return {"rIsLeaf": rIsLeaf, "rCount": rCount, "rOffset": offset + 4}

def traverse_tree(file, baseurl):
    print("processing file - ", file.name)
    bw = BigWig(baseurl + file.name)
    print("\t getting headers")
    findexOffset = bw.header.get("fullIndexOffset")
    # bw.getZoomHeader()
    ifile = "trees/" + file.name + ".fulltreeindex"
    f = open(ifile, "rb")
    # bw.tree[str(-2)] = f.read()
    tree = f.read()
    f.close()
    # print(tree)
    offset = 48
    print("\t endian - ", bw.endian)
    print("\t fullindexoffset - ", findexOffset)
    root = read_node(tree, offset, endian = bw.endian)
    # print("\t root - ", root)
    records = traverse_nodes(root, -2, tree = tree, fullIndexOffset = findexOffset, endian = bw.endian)
    pfile = "processed/" + file.name + ".leaves"
    df = pandas.DataFrame(records, columns=["rStartChromIx", "rStartBase", "rEndChromIx", "rEndBase", 
                        "rdataOffset", "rDataSize"])
    df.to_csv(pfile, index=False)

# This will extract the leaf nodes from all the files
# Parallel(n_jobs = 10) (delayed(traverse_tree)(file, url) for file in files[1000:])

def get_file_chr(file, baseurl):
    # print("processing file - ", file.name)
    bw = BigWig(baseurl + file.name)
    # print("\t getting zoom headers")
    bw.getZoomHeader()
    bw.getId("chr1")
    # print("\t chrom tree")
    return bw.chrmIds

# Parallel(n_jobs = 10) (delayed(get_file_chr)(file, url) for file in files)

# result = {}
# for file in files:
#     print("processing file - ", file.name)
#     result[file.name] = get_file_chr(file, url)

# with open("chrmids.json", "w") as f:
#     f.write(json.dumps(result))

# def build_quadtree(file, baseurl, chrmid):


