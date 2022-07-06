import pytest
import os

from epivizquindex import QuadTree
from epivizquindex import EpivizQuindex
from epivizquindex.utils import get_genome

__author__ = "Yifan_Yang"
__copyright__ = "Yifan_Yang"
__license__ = "MIT"


def test_get_genome():

    genome = get_genome('mm10')
    assert type(genome.get('chr1')) == int


def test_in_memory_query():
    '''
    Test index creation, and in_memory query.
    '''
    genome = get_genome('mm10')

    index = EpivizQuindex.EpivizQuindex(genome, base_path=None)
    f1 = 'http://renlab.sdsc.edu/yangli/downloads/mousebrain/bigwig/VPIA3.bw'
    f2 = 'http://renlab.sdsc.edu/yangli/downloads/mousebrain/bigwig/PVM.bw'
    f3 = 'http://renlab.sdsc.edu/yangli/downloads/mousebrain/bigwig/OBGL4.bw'
    f4 = 'http://renlab.sdsc.edu/yangli/downloads/mousebrain/bigwig/OBGL5.bw'

    # adding file to index
    index.add_to_index(f1)
    index.add_to_index(f2)
    index.add_to_index(f3)
    index.add_to_index(f4)

    # querying a range in 1 file
    assert len(index.query("chr10", 0, 900000, file = f1)) == 1

    # querying for a range in all files
    assert len(index.query("chr2", 0, 900000)) == 4



def test_save_load_file_query():
    '''
    Test index creation, saving the index to disk, loading the index from disk, and performing search without loading.
    '''
    genome = get_genome('mm10')
    base_path='./large_test_data/'

    index = EpivizQuindex.EpivizQuindex(genome, base_path=base_path)
    f1 = 'http://renlab.sdsc.edu/yangli/downloads/mousebrain/bigwig/VPIA3.bw'
    f2 = 'http://renlab.sdsc.edu/yangli/downloads/mousebrain/bigwig/PVM.bw'
    f3 = 'http://renlab.sdsc.edu/yangli/downloads/mousebrain/bigwig/OBGL4.bw'
    f4 = 'http://renlab.sdsc.edu/yangli/downloads/mousebrain/bigwig/OBGL5.bw'

    # adding file to index
    index.add_to_index(f1)
    index.add_to_index(f2)
    index.add_to_index(f3)
    index.add_to_index(f4)

    # storing the precomputed index to cwd
    index.to_disk()

    # reading a precomputed set of indecies
    index = EpivizQuindex.EpivizQuindex(genome, base_path=base_path)
    index.from_disk()

    # querying a range in 1 file
    assert len(index.query("chr10", 0, 900000, file = f1)) == 1

    # querying for a range in all files
    assert len(index.query("chr2", 0, 900000)) == 4

    # linking a precomputed set of indecies from cwq
    # note that using load = False, EpvizQuindex does not 
    # read the index into memory.
    memory = False
    index = EpivizQuindex.EpivizQuindex(genome, base_path=base_path)
    index.from_disk(load = memory)


    # querying a range in 1 file without loading it to memory
    # here, the in_memory parameter must be set to false
    assert len(index.query("chrX", 0, 900000, file = f1, in_memory = memory)) == 1

    # querying for a range in all files without loading it to memory
    # again, the in_memory parameter must be set to false
    assert len(index.query("chr13", 0, 900000, in_memory = memory)) == 4

    # remove the folder and path

    for f in os.listdir(base_path):
        os.remove(os.path.join(base_path, f))

    os.rmdir(base_path) 
