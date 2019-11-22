"""
# Pyqtree

Pyqtree is a pure Python spatial index for GIS or rendering usage.
It stores and quickly retrieves items from a 2x2 rectangular grid area,
and grows in depth and detail as more items are added.
The actual quad tree implementation is adapted from
[Matt Rasmussen's compbio library](https://github.com/mdrasmus/compbio/blob/master/rasmus/quadtree.py)
and extended for geospatial use.


## Platforms

Python 2 and 3.


## Dependencies

Pyqtree is written in pure Python and has no dependencies.


## Installing It

Installing Pyqtree can be done by opening your terminal or commandline and typing:

    pip install pyqtree

Alternatively, you can simply download the "pyqtree.py" file and place
it anywhere Python can import it, such as the Python site-packages folder.


## Example Usage

Start your script by importing the quad tree.

    from pyqtree import Index

Setup the spatial index, giving it a bounding box area to keep track of.
The bounding box being in a four-tuple: (xmin, ymin, xmax, ymax).

    spindex = Index(bbox=(0, 0, 100, 100))

Populate the index with items that you want to be retrieved at a later point,
along with each item's geographic bbox.

    # this example assumes you have a list of items with bbox attribute
    for item in items:
        spindex.insert(item, item.bbox)

Then when you have a region of interest and you wish to retrieve items from that region,
just use the index's intersect method. This quickly gives you a list of the stored items
whose bboxes intersects your region of interests.

    overlapbbox = (51, 51, 86, 86)
    matches = spindex.intersect(overlapbbox)

There are other things that can be done as well, but that's it for the main usage!


## More Information:

- [Home Page](http://github.com/karimbahgat/Pyqtree)
- [API Documentation](https://karimbahgat.github.io/Pyqtree/)


## License:

This code is free to share, use, reuse, and modify according to the MIT license, see LICENSE.txt.


## Credits:

- Karim Bahgat
- Joschua Gandert

"""

__version__ = "1.0.0"
disk = "./f.b"
nodeSize = 864
itemSize = 72

#PYTHON VERSION CHECK
import sys, os
from struct import *
PYTHON3 = int(sys.version[0]) == 3
if PYTHON3:
    xrange = range


def _normalize_rect(rect):
    if len(rect) == 2:
        x1, y1 = rect
        x2, y2 = rect
    else:
        x1, y1, x2, y2 = rect
    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1
    return (x1, y1, x2, y2)


def _loopallchildren(parent):
    for child in parent.children:
        if child.children:
            for subchild in _loopallchildren(child):
                yield subchild
        yield child


class _QuadNode(object):
    def __init__(self, item, rect):
        self.item = item
        self.rect = rect

    def __eq__(self, other):
        return self.item == other.item and self.rect == other.rect

    def __hash__(self):
        return hash(self.item)


class _QuadTree(object):
    """
    Internal backend version of the index.
    The index being used behind the scenes. Has all the same methods as the user
    index, but requires more technical arguments when initiating it than the
    user-friendly version.
    """

    # def __init__(self, x, y, width, height, max_items, max_depth, _depth=0, fileOffset):
    def __init__(self, x, y, width, height, max_items, max_depth, _depth, offset):

        with open(disk, 'rb+') as f:
            f.seek(offset)
            output = pack('ddddl', x, y, width, height, _depth)
            for x in range(0, max_items + 1):
                # pad items
                output += pack('llllldddd', 0, 0, 0, 0, 0, 0, 0, 0, 0)
            output += pack('llll', 0,0,0,0)
            f.write(output)


        # self.nodes = []
        # self.children = []
        # self.center = (x, y)
        # self.width, self.height = width, height
        self.max_items = max_items
        self.max_depth = max_depth
        # self._depth = _depth

    def __iter__(self):
        for child in _loopallchildren(self):
            yield child

    def hasChildren(self, offset):
        if offset == 0:
            # print()
            raise(Exception(os.path.getsize(disk)))
        c = False
        with open(disk, 'rb+') as f:
            f.seek(offset + 40 + (MAX_ITEMS + 1) * itemSize)
            print(offset)
            c = unpack("l", f.read(8))[0] is not 0
            f.seek(-8, 1)
            print("at hasChildren ", offset, unpack("llll", f.read(32)), c)
        return c


    def _insert(self, item, bbox, offset):
        rect = _normalize_rect(bbox)
        if not self.hasChildren(offset):
            node = (item, rect)
            print(offset)
            # self.nodes.append(node)
            with open(disk, 'rb+') as f:
                f.seek(offset + 40)
                counter = 0
                while True:
                    counter += 1
                    a = unpack("llllldddd",f.read(72))
                    print(a)
                    if a[2] == 0:
                        f.seek(-72, 1)
                        f.write(pack("llllldddd", item[0], item[1], item[2], item[3], item[4], rect[0], rect[1], rect[2], rect[3]))
                        break
            # if counter > self.max_items and self._depth < self.max_depth:
            if counter > self.max_items:
                self._split(offset)
        else:
            # print(item, rect, offset)
            self._insert_into_children(item, rect, offset)

    def _remove(self, item, bbox):
        rect = _normalize_rect(bbox)
        if len(self.children) == 0:
            node = _QuadNode(item, rect)
            self.nodes.remove(node)
        else:
            self._remove_from_children(item, rect)

    def _intersect(self, rect, offset, results=None, uniq=None):
        if results is None:
            rect = _normalize_rect(rect)
            results = []
            uniq = set()
        # search children
        with open(disk, 'rb+') as f:
            if self.hasChildren(offset):
                f.seek(offset)
                (x, y, width, height, depth) = unpack("ddddl", f.read(40))
                f.seek((MAX_ITEMS + 1) * nodeSize, 1)
                children = unpack("llll", f.read(32))
                if rect[0] <= x:
                    if rect[1] <= y:
                        self._intersect(rect, children[0], results, uniq)
                    if rect[3] >= y:
                        self._intersect(rect, children[1], results, uniq)
                if rect[2] >= x:
                    if rect[1] <= y:
                        self._intersect(rect, children[2], results, uniq)
                    if rect[3] >= y:
                        self._intersect(rect, children[3], results, uniq)
            # search node at this level

            f.seek(offset + 40)
            counter = 0
            nodes = []
            while True and counter < 11:
                counter += 1
                node = unpack("llllldddd", f.read(72))
                if node[2] == 0:
                    break
                else:
                    nodes.append(((node[0], node[1], node[2], node[3], node[4]), (node[5], node[6], node[7], node[8])))

            for node in nodes:
                _id = id(node[0])
                if (_id not in uniq and
                    node[1][2] >= rect[0] and node[1][0] <= rect[2] and
                    node[1][3] >= rect[1] and node[1][1] <= rect[3]):
                    results.append(node[0])
                    uniq.add(_id)
        return results

    def _insert_into_children(self, item, rect, offset):
        with open(disk, 'rb+') as f:
            f.seek(offset)                
            # print(offset)
            # print(os.path.getsize(disk))
            (x, y, width, height, depth) = unpack("ddddl", f.read(40))

            # if rect spans center then insert here
            if (rect[0] <= x and rect[2] >= x and
                rect[1] <= y and rect[3] >= y):
                # when exceeds 11 items it discards it
                # TODO: fix this
                counter = 0
                while counter < 11:
                    counter += 1
                    if unpack("llllldddd", f.read(72))[2] == 0:
                        f.seek(-72, 1)
                        f.write(pack("llllldddd", item[0], item[1], item[2], item[3], item[4], rect[0], rect[1], rect[2], rect[3]))
                        break
            else:
                # try to insert into children
                f.seek(offset + 40 + (MAX_ITEMS + 1) * itemSize)
                children = unpack("llll", f.read(32))
                if rect[0] <= x:
                    if rect[1] <= y:
                        print(offset)
                        print(offset + 40 + (MAX_ITEMS + 1) * itemSize)
                        f.seek(1760)
                        print(f.read(32))
                        print("print children")
                        print(children)
                        self._insert(item, rect, children[0])
                    if rect[3] >= y:
                        self._insert(item, rect, children[1])
                if rect[2] > x:
                    if rect[1] <= y:
                        self._insert(item, rect, children[2])
                    if rect[3] >= y:
                        self._insert(item, rect, children[3])

    def _remove_from_children(self, item, rect):
        # if rect spans center then insert here
        if (rect[0] <= self.center[0] and rect[2] >= self.center[0] and
            rect[1] <= self.center[1] and rect[3] >= self.center[1]):
            node = _QuadNode(item, rect)
            self.nodes.remove(node)
        else:
            # try to remove from children
            if rect[0] <= self.center[0]:
                if rect[1] <= self.center[1]:
                    self.children[0]._remove(item, rect)
                if rect[3] >= self.center[1]:
                    self.children[1]._remove(item, rect)
            if rect[2] > self.center[0]:
                if rect[1] <= self.center[1]:
                    self.children[2]._remove(item, rect)
                if rect[3] >= self.center[1]:
                    self.children[3]._remove(item, rect)

    def _split(self, offset):
        with open(disk, 'rb+') as f:
            print(offset)
            f.seek(offset)
            (x, y, width, height, depth) = unpack("ddddl", f.read(40))

            quartwidth = width / 4.0
            quartheight = height / 4.0
            halfwidth = width / 2.0
            halfheight = height / 2.0
            x1 = x - quartwidth
            x2 = x + quartwidth
            y1 = y - quartheight
            y2 = y + quartheight
            new_depth = depth + 1

            c1 = os.path.getsize(disk)
            _QuadTree(x1, y1, halfwidth, halfheight,
                       self.max_items, self.max_depth, new_depth, c1),
            _QuadTree(x1, y2, halfwidth, halfheight,
                       self.max_items, self.max_depth, new_depth, c1 + nodeSize),
            _QuadTree(x2, y1, halfwidth, halfheight,
                       self.max_items, self.max_depth, new_depth, c1 + nodeSize*2),
            _QuadTree(x2, y2, halfwidth, halfheight,
                       self.max_items, self.max_depth, new_depth, c1 + nodeSize*3)
            # write nodes info to disk
            f.seek(offset + 40 + (MAX_ITEMS + 1) * itemSize)
            # print("at split", c1)
            f.write(pack("llll", c1, c1 + nodeSize, c1 + nodeSize*2, c1 + nodeSize*3))

            # nodes = self.nodes
            # self.nodes = []

            # read nodes, there should be 11 of them at this point
            f.seek(offset + 40)
            nodes = []
            for x in range(0,11):
                (start, end, fOffset, length, fileName, x1,y1,x2,y2) = unpack("llllldddd", f.read(72))
                f.seek(-72,1)
                f.write(pack("llllldddd", 0,0,0,0,0,0,0,0,0))
                nodes.append(((start, end, fOffset, length, fileName), (x1,y1,x2,y2)))
            for node in nodes:
                print(node)
                print(offset)
                print(offset + 40 + (MAX_ITEMS + 1) * itemSize)
                f.seek(1760)
                a = f.read(32)
                print(f.read(32))
                print(unpack("llll", a))
                self._insert_into_children(node[0], node[1], offset)

    def __len__(self):
        """
        Returns:

        - A count of the total number of members/items/nodes inserted
        into this quadtree and all of its child trees.
        """
        size = 0
        for child in self.children:
            size += len(child)
        size += len(self.nodes)
        return size


MAX_ITEMS = 10
MAX_DEPTH = 20


class Index(_QuadTree):

    def __init__(self, bbox=None, x=None, y=None, width=None, height=None, max_items=MAX_ITEMS, max_depth=MAX_DEPTH):
        if bbox is not None:
                
            x1, y1, x2, y2 = bbox
            with open(disk, 'wb') as f:
                f.write(pack('qiiiqqqqq', 0x45504951, MAX_ITEMS, 64, 64,x1,y1,x2,y2,0))
                # mgic, max children, offset to start, offset to next, x1 y1 x2 y2, padding
            width, height = abs(x2-x1), abs(y2-y1)
            midx, midy = x1+width/2.0, y1+height/2.0
            super(Index, self).__init__(midx, midy, width, height, max_items, max_depth, 0, 64)

        elif None not in (x, y, width, height):
            super(Index, self).__init__(x, y, width, height, max_items, max_depth)

        else:
            raise Exception("Either the bbox argument must be set, or the x, y, width, and height arguments must be set")

    def get():
        pass
    def insert(self, item, bbox):
        """
        Inserts an item into the quadtree along with its bounding box.

        Parameters:
        - **item**: The item to insert into the index, which will be returned by the intersection method
        - **bbox**: The spatial bounding box tuple of the item, with four members (xmin,ymin,xmax,ymax)
        """
        self._insert(item, bbox, 64)

    def remove(self, item, bbox):
        """
        Removes an item from the quadtree.

        Parameters:
        - **item**: The item to remove from the index
        - **bbox**: The spatial bounding box tuple of the item, with four members (xmin,ymin,xmax,ymax)

        Both parameters need to exactly match the parameters provided to the insert method.
        """
        self._remove(item, bbox)

    def intersect(self, bbox):
        """
        Intersects an input boundingbox rectangle with all of the items
        contained in the quadtree.

        Parameters:
        - **bbox**: A spatial bounding box tuple with four members (xmin,ymin,xmax,ymax)

        Returns:
        - A list of inserted items whose bounding boxes intersect with the input bbox.
        """
        return self._intersect(bbox, 64)
