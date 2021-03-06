=============
EpivizQuindex
=============


Usage
=====

1. Initialize an EpivizQuindex object

::

    tree = EpivizQuindex()

2. Add files to the index. by default the library uses the unbinned (raw) data from 
the BigWig file to create the index. 

::

    tree.add_to_index(file=<LOCATION OF BIGWIG FILE>, zoomlvl = -2)


3. The index is built in memory but can also be written to disk.

::

	tree.to_disk(file_path=<>)

This allows persistence storage of the index and reusability. The package also supports 
querying quadindex on disk without loading the entire index into memory.

Note
====

This project has been set up using PyScaffold 3.2.3. For details and usage
information on PyScaffold see https://pyscaffold.org/.
