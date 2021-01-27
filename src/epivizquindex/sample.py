import QuadTree
import EpivizQuindex

genome = {
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

index = EpivizQuindex.EpivizQuindex(genome)
f1 = "../testData/39033.bigwig"
f2 = "../testData/39031.bigwig"

# adding file to index
index.add_to_index(f1)
index.add_to_index(f2)

# storing the precomputed index to cwd
index.to_disk()

# reading a precomputed set of indecies from cwq
index = EpivizQuindex.EpivizQuindex(genome)
index.from_disk()

# querying for 1 file
f1 = "../testData/39033.bigwig"
print(index.query("chr2", 0, 900000, f1))

# querying for all files
print(index.query("chr2", 0, 900000))

# and I guess we can add a option for querying for a set of files later