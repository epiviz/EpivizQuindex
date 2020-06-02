FIQIT
=======

usage

1. Initializes an empty QuadTree Index

::

    tree = EpivizQuadIndex()

2. Add files to the index. by default the library uses the unbinned (raw) data from 
the BigWig file to create the index. 

::

    tree.add_to_index(file=<LINK TO BNIGWIG FILE>, zoomlvl = -2)


3. The index is usually built in memory. One can also write the index to disk 

::

	tree.to_disk(file_path=<>)

This allows persistence storage of the index and reusability. The package also supports 
querying quadindex on disk without loading the entire index into memory.