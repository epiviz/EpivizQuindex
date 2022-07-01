.. These are examples of badges you might want to add to your README:
   please update the URLs accordingly

    .. image:: https://api.cirrus-ci.com/github/<USER>/EpivizQuindex.svg?branch=main
        :alt: Built Status
        :target: https://cirrus-ci.com/github/<USER>/EpivizQuindex
    .. image:: https://readthedocs.org/projects/EpivizQuindex/badge/?version=latest
        :alt: ReadTheDocs
        :target: https://EpivizQuindex.readthedocs.io/en/stable/
    .. image:: https://img.shields.io/coveralls/github/<USER>/EpivizQuindex/main.svg
        :alt: Coveralls
        :target: https://coveralls.io/r/<USER>/EpivizQuindex
    .. image:: https://img.shields.io/pypi/v/EpivizQuindex.svg
        :alt: PyPI-Server
        :target: https://pypi.org/project/EpivizQuindex/
    .. image:: https://img.shields.io/conda/vn/conda-forge/EpivizQuindex.svg
        :alt: Conda-Forge
        :target: https://anaconda.org/conda-forge/EpivizQuindex
    .. image:: https://pepy.tech/badge/EpivizQuindex/month
        :alt: Monthly Downloads
        :target: https://pepy.tech/project/EpivizQuindex
    .. image:: https://img.shields.io/twitter/url/http/shields.io.svg?style=social&label=Twitter
        :alt: Twitter
        :target: https://twitter.com/EpivizQuindex

.. image:: https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold
    :alt: Project generated with PyScaffold
    :target: https://pyscaffold.org/

|

=============
EpivizQuindex
=============


    Genomic analysis pipelines and workflows often use specialized file formats for manipulating and quickly finding data on potential genomic regions of interest. These file formats contain an index as part of the specification and allows users to perform random access queries. When we have a collection of these files, it's time consuming to read every single file and extract the data for a region of interest. The goal with Quindex approach is to "index the index" from these files and provide fast access to large collections of genomic data across files.

Usage
====

To import the package, simply run:

.. code-block:: python
    import EpivizQuindex

Define the genome range, and set the path to a folder where you want to hold the index:

.. code-block:: python
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
    base_path='indices/'
    index = EpivizQuindex.EpivizQuindex(genome, base_path=base_path)

Add files to index with a simple function call:

.. code-block:: python
    f1 = "/path_to_your_file/some.bigwig"
    f2 = "/path_to_your_file/someOther.bigwig"
    # adding file to index
    index.add_to_index(f1)
    index.add_to_index(f2)

Invoke the query in a specific chromosome and range:

.. code-block:: python
    index.query("chr2", 0, 900000)

You can also require which file you are looking for:

.. code-block:: python
    index.query("chr2", 0, 900000, file = f1)

Store the index to disk and load index to memory with ```to_disk()``` and ```from_disk()```:

.. code-block:: python
    # storing the precomputed index to cwd
    index.to_disk()
    # reading a precomputed set of indecies
    index = EpivizQuindex.EpivizQuindex(genome, base_path=base_path)
    index.from_disk()

We can also perform search without loading the index to memory:
.. code-block:: python
    memory = False
    index = EpivizQuindex.EpivizQuindex(genome, base_path=base_path)
    index.from_disk(load = memory)
    index.query("chr2", 0, 900000, in_memory = memory)


.. _pyscaffold-notes:

Note
====

This project has been set up using PyScaffold 4.2.3. For details and usage
information on PyScaffold see https://pyscaffold.org/.
