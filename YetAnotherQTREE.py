#PYTHON VERSION CHECK
import sys
from struct import *
from shapely.geometry import Polygon

MAX_ITEMS = 10
MAX_DEPTH = 20
item_size = 72
leaf_size = 40 + 1 + ((MAX_ITEMS) * item_size)
parent_size = 40 + 1 + 32

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

    def __init__(self, x, y, width, height, max_items, max_depth, _depth=0):
        self.nodes = []
        self.children = []
        self.isLeaf = False
        self.center = (x, y)
        self.width, self.height = width, height
        self.max_items = max_items
        self.max_depth = max_depth
        self._depth = _depth

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
                self.isLeaf == True 
                self._split()
        else:
            self._insert_into_children(item, rect)

    def _remove(self, item, bbox):
        rect = _normalize_rect(bbox)
        if len(self.children) == 0:
            node = _QuadNode(item, rect)
            self.nodes.remove(node)
        else:
            self._remove_from_children(item, rect)

    def box_intersect(self, box1, box2):
        # print(box1, box2)
        p1 = Polygon([(box1[0], box1[1]), (box1[0], box1[3]), (box1[2], box1[3]), (box1[2], box1[1])])
        p2 = Polygon([(box2[0], box2[1]), (box2[0], box2[3]), (box2[2], box2[3]), (box2[2], box2[1])])
        return p1.intersects(p2)

    def _intersect(self, rect, f_path, offset = None, results=None):
        if results is None:
            rect = _normalize_rect(rect)
            results = []
        if offset is -1:
            # print("found empty")
            return []
        if offset is None:
            raise Exception("memory search not implemented")
        with open(f_path, 'rb') as f:
            # print("offset: ", offset)
            f.seek(offset)
            a = f.read(41)
            if offset < 64:
                raise Exception()
            # print(len(a))
            (x, y, width, height, depth, isLeaf) = unpack("ddddl?", a)
            # print(x,y,width,height,isLeaf)
            # search children
            if not isLeaf:
                children = unpack("llll", f.read(32))
                # print(children)
                # if rect[0] <= self.center[0]:
                #     if rect[1] <= self.center[1]:
                #         self.children[0]._intersect(rect, results, uniq)
                #     if rect[3] >= self.center[1]:
                #         self.children[1]._intersect(rect, results, uniq)
                # if rect[2] >= self.center[0]:
                #     if rect[1] <= self.center[1]:
                #         self.children[2]._intersect(rect, results, uniq)
                #     if rect[3] >= self.center[1]:
                #         self.children[3]._intersect(rect, results, uniq)
                if self.box_intersect(rect, (x - width/2, y, x, y + height/2)):
                    self._intersect(rect, f_path,children[1], results)
                if self.box_intersect(rect, (x - width/2, y - height/2, x, y)):
                    self._intersect(rect, f_path, children[0], results)
                if self.box_intersect(rect, (x, y - height/2, x + width/2, y)):
                    self._intersect(rect, f_path, children[2], results)
                if self.box_intersect(rect, (x, y, x + width/2, y + height/2)):
                    self._intersect(rect, f_path, children[3], results)
            # If at leaf, search and compare if uniq
            # this can be removed. Need test
            else:
                # print("intersect some leaf levels")
                nodes = []
                counter = 0
                while counter < MAX_ITEMS:
                    counter += 1
                    node = unpack("llllldddd", f.read(72))
                    # print(node)
                    if node[2] == 0:
                        break
                    else:
                        nodes.append(((node[0], node[1], node[2], node[3], node[4]), (node[5], node[6], node[7], node[8])))

                for node in nodes:
                    # _id = id(node.item)
                    # print(node)
                    if self.box_intersect(rect, node[1]):
                    # (
                        # _id not in uniq and
                        # node.rect[2] >= rect[0] and node.rect[0] <= rect[2] and
                        # node.rect[3] >= rect[1] and node.rect[1] <= rect[3]):
                        results.append(node[1])
                        # uniq.add(_id)
        return results

    def _insert_into_children(self, item, rect):
        if rect[0] <= self.center[0]:
            if rect[1] <= self.center[1]:
                self.children[0]._insert(item, rect)
            if rect[3] >= self.center[1]:
                self.children[1]._insert(item, rect)
        if rect[2] > self.center[0]:
            if rect[1] <= self.center[1]:
                self.children[2]._insert(item, rect)
            if rect[3] >= self.center[1]:
                self.children[3]._insert(item, rect)

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
        self.children = [_QuadTree(x1, y1, halfwidth, halfheight,
                                   self.max_items, self.max_depth, new_depth),
                         _QuadTree(x1, y2, halfwidth, halfheight,
                                   self.max_items, self.max_depth, new_depth),
                         _QuadTree(x2, y1, halfwidth, halfheight,
                                   self.max_items, self.max_depth, new_depth),
                         _QuadTree(x2, y2, halfwidth, halfheight,
                                   self.max_items, self.max_depth, new_depth)]
        nodes = self.nodes
        self.nodes = []
        for node in nodes:
            self._insert_into_children(node.item, node.rect)

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

    def convert_to_disk(self, position):
        # return a pack of bites and children objects if exist
        # print("pos: ", position)
        barray = pack('ddddl', self.center[0], self.center[1], self.width, self.height, self._depth)
        # print("in ctd:", len(barray))
        if not self.isLeaf and not self.hasData():
            # parent node
            barray += pack('?', 0)
            children = self.children
            # print(self.nodes)
            if not self.children:
                # print(self.center[0], self.center[1], self.width, self.height, self._depth)
                # skip this node
                return (bytearray(),[],position)
            children_position = []
            for c in self.children:
                children_position.append(position)
                # print(children_position)
                if len(c.children) is not 0:
                    position += parent_size
                elif len(c.nodes) is not 0:
                    position += leaf_size
                else: 
                    # print("empty")
                    children_position[-1] = -1
            # print("out loop")
            # print(children_position)
            barray += pack('llll', children_position[0], children_position[1], children_position[2], children_position[3])
        else:
            # leaf node
            # print("writing a leaf node")
            barray += pack('?', 1)
            # print("in ctd:", len(barray))
            # print(unpack("ddddl?", barray))
            children = []
            # print(self.nodes)
            for node in self.nodes:
                (item, rect) = (node.item, node.rect)
                barray += pack("llllldddd", item[0], item[1], item[2], item[3], item[4], rect[0], rect[1], rect[2], rect[3])
            # pad to leaf node length
            # now this is for easy file location calculation, we can probably design more
            # delicate structure to save some space
            barray += (MAX_ITEMS - len(self.nodes)) * pack("llllldddd", 0,0,0,0,0,0,0,0,0)
            # print(unpack("ddddl?", barray[0:41]))
        return barray, children, position



class Index(_QuadTree):
    """
    The top spatial index to be created by the user. Once created it can be
    populated with geographically placed members that can later be tested for
    intersection with a user inputted geographic bounding box. Note that the
    index can be iterated through in a for-statement, which loops through all
    all the quad instances and lets you access their properties.
    Example usage:
    >>> spindex = Index(bbox=(0, 0, 100, 100))
    >>> spindex.insert('duck', (50, 30, 53, 60))
    >>> spindex.insert('cookie', (10, 20, 15, 25))
    >>> spindex.insert('python', (40, 50, 95, 90))
    >>> results = spindex.intersect((51, 51, 86, 86))
    >>> sorted(results)
    ['duck', 'python']
    """

    # def __init__(self, bbox=None, x=None, y=None, width=None, height=None, max_items=MAX_ITEMS, max_depth=MAX_DEPTH):
    def __init__(self, bbox=None, x=None, y=None, width=None, height=None, max_items=MAX_ITEMS, max_depth=MAX_DEPTH, disk = "./f.b", first_run=False):
        """
        Initiate by specifying either 1) a bbox to keep track of, or 2) with an xy centerpoint and a width and height.
        Parameters:
        - **bbox**: The coordinate system bounding box of the area that the quadtree should
            keep track of, as a 4-length sequence (xmin,ymin,xmax,ymax)
        - **x**:
            The x center coordinate of the area that the quadtree should keep track of.
        - **y**
            The y center coordinate of the area that the quadtree should keep track of.
        - **width**:
            How far from the xcenter that the quadtree should look when keeping track.
        - **height**:
            How far from the ycenter that the quadtree should look when keeping track
        - **max_items** (optional): The maximum number of items allowed per quad before splitting
            up into four new subquads. Default is 10.
        - **max_depth** (optional): The maximum levels of nested subquads, after which no more splitting
            occurs and the bottommost quad nodes may grow indefinately. Default is 20.
        """
        self.disk = disk
        if bbox is not None:
            

            x1, y1, x2, y2 = bbox
            width, height = abs(x2-x1), abs(y2-y1)
            midx, midy = x1+width/2.0, y1+height/2.0
            with open(self.disk, 'wb') as f:
                f.write(pack('qiiiqqqqq', 0x45504951, MAX_ITEMS, 64, 64,x1,y1,x2,y2,0))
                print(len(pack('qiiiqqqqq', 0x45504951, MAX_ITEMS, 64, 64,x1,y1,x2,y2,0)))
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
        # print("calling insert")
        self._insert(item, bbox)

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
        return self._intersect(bbox, self.disk, 64)

    def to_disk(self):
        # defualt filepointer.tell() probably will not work as python reads bytes into 
        # buffer (maybe it works). To keep things undercontrol, we use a manual byte counter.
        q = [self]
        position = 0
        fp = 0
        farray = bytearray()
        with open(self.disk, 'wb') as f:
            position = 64
            f.seek(64)
            if not super(Index, self).IsParent():
                position += parent_size
            else:
                position += leaf_size
            while q:
                t = q.pop(0)
                barray, children, position = t.convert_to_disk(position)
                # print("in to_disk:", len(barray))
                # print(leaf_size)
                f.write(barray)
                q += children
        return self.disk
