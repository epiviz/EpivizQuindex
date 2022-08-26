import QuadTree
from epivizquindex import EpivizQuindex
from epivizquindex.utils import get_genome
import os


# genome = {
#     "chr1": 249250621, 
#     "chr10": 135534747, 
#     "chr11": 135006516, 
#     "chr12": 133851895, 
#     "chr13": 115169878, 
#     "chr14": 107349540, 
#     "chr15": 102531392, 
#     "chr16": 90354753, 
#     "chr17": 81195210, 
#     "chr18": 78077248, 
#     "chr19": 59128983, 
#     "chr2": 243199373, 
#     "chr20": 63025520, 
#     "chr21": 48129895, 
#     "chr22": 51304566, 
#     "chr3": 198022430, 
#     "chr4": 191154276, 
#     "chr5": 180915260, 
#     "chr6": 171115067, 
#     "chr7": 159138663, 
#     "chr8": 146364022, 
#     "chr9": 141213431, 
#     "chrM": 16571, 
#     "chrX": 155270560, 
#     "chrY": 59373566
# }
genome = get_genome('mm10')
base_path='./large_test_data/'


# # # f1 = "../../large_test_data/39033.bigwig"
# # # f2 = "../../large_test_data/39033.bigwig"
f1 = 'http://renlab.sdsc.edu/yangli/downloads/mousebrain/bigwig/VPIA3.bw'
f2 = 'http://renlab.sdsc.edu/yangli/downloads/mousebrain/bigwig/PVM.bw'
f3 = 'http://renlab.sdsc.edu/yangli/downloads/mousebrain/bigwig/OBGL4.bw'
f4 = 'http://renlab.sdsc.edu/yangli/downloads/mousebrain/bigwig/OBGL5.bw'


# index = EpivizQuindex.EpivizQuindex(genome, base_path=base_path)
# # # adding file to index
# index.add_to_index(f1)
# index.add_to_index(f2)
# index.add_to_index(f3)
# index.add_to_index(f4)

# # storing the precomputed index to cwd
# index.to_disk()

# reading a precomputed set of indecies
index = EpivizQuindex.EpivizQuindex(genome, base_path=base_path)
index.from_disk()

# querying a range in 1 file
print('performing query')
# print(index.query("chrX", 0, 3195790, file = f1))
print(index.query("chr12", 4352, 5004352, file = f1))
print('end of query')

# querying for a range in all files
# print(index.query("chrX", 0, 3195790))

# print('pass memory')

# # linking a precomputed set of indecies from cwq
# # note that using load = False, EpvizQuindex does not 
# # read the index into memory.
memory = False
index = EpivizQuindex.EpivizQuindex(genome, base_path=base_path)
index.from_disk(load = memory)


# querying a range in 1 file without loading it to memory
# here, the in_memory parameter must be set to false
print(len(index.query("chrX", 0, 3195790, file = f1, in_memory = memory)))

# # querying for a range in all files without loading it to memory
# # again, the in_memory parameter must be set to false
# print(len(index.query("chr13", 0, 3195794, in_memory = memory)))


# for f in os.listdir(base_path):
#     os.remove(os.path.join(base_path, f))

# os.rmdir(base_path) 

# and I guess we can add a option for querying for a set of files later
