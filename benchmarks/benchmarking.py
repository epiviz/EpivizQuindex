# bw = BigWig("tests/test.bw")

# # extract header and zoom levels from the file
# print(bw.header, bw.zooms)

# # query the file
# res, err = bw.getRange(chr="chr1", start=10000000, end=10020000)


# local file

from epivizFileParser import BigWig
from epivizquindex import EpivizQuindex
from epivizquindex.utils import get_genome
import pandas as pd
import time, random
import argparse
import os

parser = argparse.ArgumentParser(description='Quindex benchmark.')

parser.add_argument("--query_range", dest='query_range', help="benchmark query range.", default=5000)
parser.add_argument("--query_times", dest='query_times', help="benchmark query times.", default=10)
parser.add_argument("--files_names", dest='files_names', help="benchmark file names.", default='./large_test_data/index')
parser.add_argument("--files_path", dest='files_path', help="benchmark file folder path.", default='./large_test_data/')
parser.add_argument("--index_path", dest='index_path', help="benchmark index path.", default='./index_data/')
parser.add_argument("--remove_index", dest='remove_index', help="clean index folder after benchmark.", default=False)

args = parser.parse_args()



query_range = int(args.query_range)
query_times = int(args.query_times)
files_names = args.files_names
files_path = args.files_path
index_path = args.index_path
remove_index = bool(args.remove_index)

if os.path.exists(index_path):
    print("Warning: Index path is not empty. Will load index from index_path")

print('benchmark query range length: ', query_range)
print('benchmark query runs: ', query_times)

files = []
with open(files_names, 'r') as f:
    for line in f:
        files.append(line.strip())


# generate queries
genomes = get_genome('mm10')
chrs = list(genomes.keys())
chrs.remove('chrM')
queries = []
for _ in range(0, query_times):
    chromosome = random.choice(chrs)
    r = genomes[chromosome]
    start = random.randint(0, r - query_range - 1)
    queries.append((chromosome, start))

#file parser
t = time.time()
bws = []
for f in files:
    bws.append(BigWig(files_path + f))
setup_t = time.time()-t

t = time.time()
dfs = []
for chromosome, start in queries:
    for bw,f in zip(bws,files):
        res, err = bw.getRange(chr=chromosome, start=start, end=start + query_range, zoomlvl = -2)
        res["file"] = f
        dfs.append(res)
dfs = pd.concat(dfs, axis = 0)
read_t = time.time()-t

print("FileParser setup time:", setup_t)
print("FileParser read time:", read_t)


# Quindex 

t = time.time()
genome = get_genome('mm10')
base_path=index_path

if os.path.exists(index_path):
    index = EpivizQuindex.EpivizQuindex(genome, base_path=base_path)
    index.from_disk()
else:
    index = EpivizQuindex.EpivizQuindex(genome, base_path=base_path)
    for f in files:
        print(f)
        index.add_to_index(files_path + f)
    index.to_disk()
setup_t = time.time()-t

t = time.time()
for chromosome, start in queries:
    index.query(chromosome, start, start + query_range)
read_t = time.time()-t

print("Quindex setup time:", setup_t)
print("Quindex in-memory search time:", read_t)


t = time.time()
for chromosome, start in queries:
    index.query(chromosome, start, start + query_range, in_memory = False)
read_t = time.time()-t

print("Quindex file-based search time:", read_t)

if remove_index:
    print('cleaning index')
    for f in os.listdir(index_path):
        os.remove(os.path.join(index_path, f))

    os.rmdir(index_path) 
