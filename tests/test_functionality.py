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

    index = EpivizQuindex.EpivizQuindex(genome, base_path='./large_test_data/')
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
    assert len(index.query("chrX", 0, 3195790, file_names = [f1])) == 2

    # querying for a range in all files
    assert len(index.query("chrX", 0, 3195790)) == 45



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
    assert len(index.query("chrX", 0, 3195790, file_names = [f1])) == 2

    # querying for a range in all files
    assert len(index.query("chrX", 0, 3195790)) == 45

    # linking a precomputed set of indecies from cwq
    # note that using load = False, EpvizQuindex does not 
    # read the index into memory.
    memory = False
    index = EpivizQuindex.EpivizQuindex(genome, base_path=base_path)
    index.from_disk(load = memory)


    # querying a range in 1 file without loading it to memory
    # here, the in_memory parameter must be set to false
    assert len(index.query("chrX", 0, 3195790, file_names = [f1], in_memory = memory)) == 2

    # querying for a range in all files without loading it to memory
    # again, the in_memory parameter must be set to false
    assert len(index.query("chrX", 0, 3195790, in_memory = memory)) == 45

    # remove the folder and path

    for f in os.listdir(base_path):
        os.remove(os.path.join(base_path, f))

    os.rmdir(base_path) 


def test_in_memory_equal_file_query():
    '''
    Test if in_memory query is the same as file_based query.
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

    index.to_disk()

    # querying a range in 1 file
    assert index.query("chrX", 0, 3195790, in_memory = False).equals(index.query("chrX", 0, 3195790))

    # querying for a range in all files
    assert index.query("chrX", 0, 3195790, file_names = [f1], in_memory = False).equals(index.query("chrX", 0, 3195790, file_names = [f1]))

    # remove the folder and path

    for f in os.listdir(base_path):
        os.remove(os.path.join(base_path, f))

    os.rmdir(base_path) 