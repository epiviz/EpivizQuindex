## heavily modefied quadtree implementation from
## https://github.com/karimbahgat/Pyqtree

import sys
from struct import *
from shapely.geometry import Polygon

MAX_ITEMS = 256
MAX_DEPTH = 20
# size of each item
item_size = 72
# leaf_size = 48 + 1 + ((Item_numbers) * item_size)
# parent_size = 48 + 1 + 32 + ((Item_numbers) * item_size)

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

    def __init__(self, x = None, y = None, width = None, height = None, max_items = None, max_depth = None, _depth=0 , path = None, offset = None):
        self.nodes = []
        self.children = []
        self.isLeaf = True
        self.center = (x, y)
        self.width, self.height = width, height
        self.max_items = max_items
        self.max_depth = max_depth
        self._depth = _depth
        if path:
            self._from_disk(path, offset)

    def __iter__(self):
        for child in _loopallchildren(self):
            yield child

    def IsParent(self):
        return len(self.children) == 0

    def hasData(self):
        return len(self.nodes) != 0

    def _insert(self, item, bbox):
        rect = _normalize_rect(bbox)
        if len(self.children) == 0:
            node = _QuadNode(item, rect)
            self.nodes.append(node)

            if len(self.nodes) > self.max_items and self._depth < self.max_depth:
                self.isLeaf = False 
                self._split()
        else:
            # calculate left-x, right-x, top-y, bottom-y coordinate of the current
            # node
            x = self.center[0]
            y = self.center[1]
            lx = x - self.width/2
            rx = x + self.width/2
            ty = y + self.height/2
            by = y - self.height/2

            if (x > rect[2] and lx < rect[0] and ty > rect[3] and y < rect[1]):
                self.children[1]._insert(item, rect)
            elif (rx > rect[2] and x < rect[0] and ty > rect[3] and y < rect[1]):
                self.children[0]._insert(item, rect)
            elif (x > rect[2] and lx < rect[0] and y > rect[3] and by < rect[1]):
                self.children[2]._insert(item, rect)
            elif (rx > rect[2] and x < rect[0] and y > rect[3] and by < rect[1]):
                self.children[3]._insert(item, rect)
            else:
            # none of the childrens FULLY contains the node, insert at this level
                node = _QuadNode(item, rect)
                self.nodes.append(node)

    def box_intersect(self, box1, box2):
        p1 = Polygon([(box1[0], box1[1]), (box1[0], box1[3]), (box1[2], box1[3]), (box1[2], box1[1])])
        p2 = Polygon([(box2[0], box2[1]), (box2[0], box2[3]), (box2[2], box2[3]), (box2[2], box2[1])])

        return p1.intersects(p2)

    def _intersect_memory(self, rect, results = None, debug = False):
        if results is None:
            results = []

        if not self.isLeaf:
            if self.children[1] and self.box_intersect(rect, (self.center[0] - self.width/2, self.center[1], self.center[0], self.center[1] + self.height/2)):
                self.children[1]._intersect_memory(rect, results)
            if self.children[2] and self.box_intersect(rect, (self.center[0] - self.width/2, self.center[1] - self.height/2, self.center[0], self.center[1])):
                self.children[2]._intersect_memory(rect, results)
            if self.children[3] and self.box_intersect(rect, (self.center[0], self.center[1] - self.height/2, self.center[0] + self.width/2, self.center[1])):
                self.children[3]._intersect_memory(rect, results)
            if self.children[0] and self.box_intersect(rect, (self.center[0], self.center[1], self.center[0] + self.width/2, self.center[1] + self.height/2)):
                self.children[0]._intersect_memory(rect, results)

        for node in self.nodes:
            if self.box_intersect(rect, node.rect):
            # (
                if debug:
                    results.append(node.item + node.rect)
                else:
                    results.append(node.item)
        return results

    def _intersect_file(self, rect, f_path, offset = None, results=None, debug = False):
        if results is None:
            results = []
        if offset is -1:
            return results
        # if offset is None:
        #     raise Exception("memory search not implemented")
        with open(f_path, 'rb') as f:
            f.seek(offset)
            a = f.read(48 + 1)
            if offset < 64:
                raise Exception()
            (x, y, width, height, depth, num_items, isLeaf) = unpack("ddddll?", a)
            # search children
            if not isLeaf:
                children = unpack("llll", f.read(32))
                if self.box_intersect(rect, (x - width/2, y, x, y + height/2)):
                    self._intersect_file(rect, f_path,children[1], results)
                if self.box_intersect(rect, (x - width/2, y - height/2, x, y)):
                    self._intersect_file(rect, f_path, children[2], results)
                if self.box_intersect(rect, (x, y - height/2, x + width/2, y)):
                    self._intersect_file(rect, f_path, children[3], results)
                if self.box_intersect(rect, (x, y, x + width/2, y + height/2)):
                    self._intersect_file(rect, f_path, children[0], results)
            nodes = []
            counter = 0
            while counter < num_items:
                counter += 1
                node = unpack("llllldddd", f.read(72))
                if node[2] == 0:
                    break
                else:
                    nodes.append(((node[0], node[1], node[2], node[3], node[4]), (node[5], node[6], node[7], node[8])))

            for node in nodes:
                if self.box_intersect(rect, node[1]):
                    if debug:
                        results.append(node[0] + node[1])
                    else:
                        results.append(node[0])
        return results

    def _split(self):
        quartwidth = self.width / 4.0
        quartheight = self.height / 4.0
        halfwidth = self.width / 2.0
        halfheight = self.height / 2.0
        x1 = self.center[0] - quartwidth
        x2 = self.center[0] + quartwidth
        y1 = self.center[1] - quartheight
        y2 = self.center[1] + quartheight
        new_depth = self._depth + 1
        self.children = [_QuadTree(x2, y2, halfwidth, halfheight,
                                   self.max_items, self.max_depth, new_depth),
                         _QuadTree(x1, y2, halfwidth, halfheight,
                                   self.max_items, self.max_depth, new_depth),
                         _QuadTree(x1, y1, halfwidth, halfheight,
                                   self.max_items, self.max_depth, new_depth),
                         _QuadTree(x2, y1, halfwidth, halfheight,
                                   self.max_items, self.max_depth, new_depth)]
        nodes = self.nodes
        self.nodes = []
        for node in nodes:
            # self._insert_into_children(node.item, node.rect)
            # call insert again, which would invoke insert into 
            # children if appropriate
            self._insert(node.item, node.rect)

    def _to_disk(self, position):
        # return a pack of bites and children objects if exist
        barray = pack('ddddl', self.center[0], self.center[1], self.width, self.height, self._depth)
        barray += pack('l', len(self.nodes))
        if len(self.children) is not 0:
            # parent node
            barray += pack('?', 0)
            children = self.children
            children_position = []
            for c in self.children:
                children_position.append(position)
                if len(c.children) is not 0:
                    position += 48 + 1 + 32 + (len(c.nodes) * item_size)
                elif len(c.nodes) is not 0:
                    position += 48 + 1 + ((len(c.nodes)) * item_size)
                else: 
                    children_position[-1] = -1
            barray += pack('llll', children_position[0], children_position[1], children_position[2], children_position[3])
        else:
            # leaf node
            barray += pack('?', 1)
            if len(self.nodes) == 0:
                return bytearray(), [], position
            children = []

        for node in self.nodes:
            (item, rect) = (node.item, node.rect)
            barray += pack("llllldddd", item[0], item[1], item[2], item[3], item[4], rect[0], rect[1], rect[2], rect[3])
        return barray, children, position

    def _from_disk(self, f_path, offset):
        children = []
        self.center = (0,0)
        with open(f_path, 'rb') as f:
            f.seek(offset)
            a = f.read(49)
            # print(offset, a)
            (x, y, self.width, self.height, self._depth, num_node, self.isLeaf) = unpack("ddddll?", a)
            self.center= (x, y)
            if not self.isLeaf:
                children = unpack("llll", f.read(32))

            for x in range(0, num_node):
                item = unpack("llllldddd", f.read(item_size))
                node_item = item[0:5]
                node_rect = item[5:]
                node = _QuadNode(node_item, node_rect)
                self.nodes.append(node)

        # parse the children outside so that no multiple file pointers opened 
        self.children = []
        for child in children:
            if child is not -1:
                self.children.append(_QuadTree(path = f_path, offset = child))
            else:
                self.children.append(None)

class Index(_QuadTree):
    """
    The wrapper of the root quad tree node, which represents a spatial index. 
    """

    def __init__(self, bbox=None, x=None, y=None, width=None, height=None, max_items=MAX_ITEMS, max_depth=MAX_DEPTH, disk = None, first_run=False):
        """
        Initiate by specifying either 1) a bbox to keep track of, or 2) with an xy centerpoint and a width and height,
        3, a disk path to pre-computed index.
        Parameters:
        - **bbox** (optional): The coordinate system bounding box of the area that the quadtree should
            keep track of, as a 4-length sequence (xmin,ymin,xmax,ymax)
        - **x** (optional):
            The x center coordinate of the area that the quadtree should keep track of.
        - **y** (optional):
            The y center coordinate of the area that the quadtree should keep track of.
        - **width** (optional):
            How far from the xcenter that the quadtree should look when keeping track.
        - **height** (optional):
            How far from the ycenter that the quadtree should look when keeping track
        - **max_items** (optional): The maximum number of items allowed per quad before splitting
            up into four new subquads. Default is 10.
        - **max_depth** (optional): The maximum levels of nested subquads, after which no more splitting
            occurs and the bottommost quad nodes may grow indefinately. Default is 20.
        - **disk** (optional): The path to which this index is prestored.
        - **first_run** (optional): Setting it to true invokes a reconstruction from a precomputed file to memory when the object is created. 
        """
        if disk and first_run:
            self.from_disk(disk)
        elif disk:
            self.disk = disk
        elif bbox is not None:
            
            x1, y1, x2, y2 = bbox
            self.bbox = bbox
            width, height = abs(x2-x1), abs(y2-y1)
            midx, midy = x1+width/2.0, y1+height/2.0
            
            super(Index, self).__init__(midx, midy, width, height, max_items, max_depth)

        elif None not in (x, y, width, height):
            super(Index, self).__init__(x, y, width, height, max_items, max_depth)

        else:
            raise Exception("Either the bbox argument must be set, or the x, y, width, and height arguments must be set")

    def insert(self, item, bbox):
        """
        Inserts an item into the quadtree along with its bounding box.
        Parameters:
        - **item**: The item to insert into the index, which will be returned by the intersection method
        - **bbox**: The spatial bounding box tuple of the item, with four members (xmin,ymin,xmax,ymax)
        """
        self._insert(item, bbox)

    def intersect(self, bbox, in_memory = False, debug = False):
        """
        Intersects an input boundingbox rectangle with all of the items
        contained in the quadtree.
        Parameters:
        - **bbox**: A spatial bounding box tuple with four members (xmin,ymin,xmax,ymax)
        - **in_memory** (optional): A flag for using in_memory search with respect to file based search.
        - **debug** (optional): A flag that allows extra output when debugging.
        Returns:
        - A list of inserted items whose bounding boxes intersect with the input bbox.
        """
        if in_memory:
            return self._intersect_memory(bbox, debug = debug)
        else:
            return self._intersect_file(bbox, self.disk, 64, debug = debug)

    def from_disk(self, f_path):
        '''
        Constructs a quadtree index from a precomputed file and store it in the current node.
        Parameters:
        - ***f_path***: a string containing the path to the precomputed index.

        '''
        header = None
        self.nodes = []
        with open(f_path, 'rb') as f:
            header = unpack('qiiiqqqqq', f.read(64))
        (magic, max_item, _, _, x1, y1, x2, y2, _) = header
        if magic != 0x45504951:
            raise Exception("File magic mismatch")
        self.bbox = (x1, y1, x2, y2)
        self.max_item = max_item

        self._from_disk(f_path, 64)

    def to_disk(self, path):
        '''
        Converts a quadtree index to file format and output it to disk.
        Parameter:
        - ***path***: a string that contains the path to which the tree will be stored at.
    
        '''
        # defualt filepointer.tell() probably will not work as python reads bytes into 
        # buffer (maybe it works). To keep things undercontrol, we use a manual byte counter.
        q = [self]
        position = 0
        fp = 0
        farray = bytearray()
        self.disk = path
        with open(path, 'wb') as f:
            x1, y1, x2, y2 = self.bbox
            f.write(pack('qiiiqqqqq', 0x45504951, MAX_ITEMS, 64, 64,x1,y1,x2,y2,0))
            position = 64
            f.seek(64)
            if not super(Index, self).IsParent():
                position += 48 + 1 + 32 + (len(self.nodes) * item_size)
            else:
                position += 48 + 1 + (len(self.nodes) * item_size)

            while q:
                t = q.pop(0)
                barray, children, position = t._to_disk(position)
                f.write(barray)
                q += children
        return self.disk
