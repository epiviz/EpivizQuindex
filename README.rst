FIQIT
=======

usage

::

    tree = Index(disk = file_path, first_run = True)

this evokes a construction from file for pre-built index. The index file will be read into memory.

::

    tree = Index(disk = file_path)

This evokes a construction where only the file path is stored. This allows only file based search. 

::

	tree = Index(bbox=(0, 0, x_y_dim, x_y_dim))

This evokes a construction of an empty quad tree with the given dimensions.

::

	tree.insert((startIndex, endIndex, dataOffset, Datasize, fileID), bbox)

This inserts an item into the tree WHILE IT IS IN MEMORY. Note that currently it only supports the above item format, which is 5 indexes. In the future, full support is possible.

::

	tree.to_disk(file_path)

The to_disk method takes a file name, and writes the data into that file. After this operation, the data in the tree will be cleaned (releasing memory hopefully).

::

	matches = tree.intersect(bbox, in_memory = True, debug = True)

The in_memory = True will evoke the in_memory seach (make sure things are still in memory before calling this method), in_memory = False will evoke a file based search, which only works when the quad tree is linked to a pre-constructed index (see the second type of construction). debug = true enables the search output result to include the bounding boxed of each item. When set to false, it only outputs the items that fall in the search range.
