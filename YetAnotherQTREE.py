#PYTHON VERSION CHECK
import sys
from struct import *
from shapely.geometry import Polygon

MAX_ITEMS = 256
MAX_DEPTH = 20
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

    def __init__(self, x, y, width, height, max_items, max_depth, _depth=0):
        self.nodes = []
        self.children = []
        self.isLeaf = True
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
                self.isLeaf == False 
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

            # print(lx, x, rx)
            # print(by, y, ty)
            # print(rect)
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

    def quadron_polygon(self):
        # calculate left-x, right-x, top-y, bottom-y coordinate of the current
        # node
        x = self.center[0]
        y = self.center[1]
        lx = x - self.width/2
        rx = x + self.width/2
        ty = y + self.height/2
        by = y - self.height/2
        # create polygon object of the 4 quadron
        q1 = Polygon([(lx, y), (lx, ty), (x, ty), (x, y)])
        q2 = Polygon([(x, y), (x, ty), (rx, ty), (rx, y)])
        q3 = Polygon([(lx, by), (lx, y), (x, y), (x, by)])
        q4 = Polygon([(x, by), (x, y), (rx, y), (rx, by)])

        return (q1, q2, q3, q4)

    def _intersect(self, rect, f_path, offset = None, results=None):
        # print(rect)
        if results is None:
            # rect = _normalize_rect(rect)
            results = []
        if offset is -1:
            # print("found empty")
            return results
        if offset is None:
            raise Exception("memory search not implemented")
        with open(f_path, 'rb') as f:
            # print("offset: ", offset)
            f.seek(offset)
            a = f.read(48 + 1)
            if offset < 64:
                raise Exception()
            # print(len(a))
            (x, y, width, height, depth, num_items, isLeaf) = unpack("ddddll?", a)
            # print(x,y,width,height, num_items, isLeaf)
            # search children
            if not isLeaf:
                children = unpack("llll", f.read(32))
                # print(children)
                # if rect[0] <= self.center[0]:
                #     if rect[1] <= self.center[1]:
                #         # self.children[0]._intersect(rect, results, uniq)
                #         self._intersect(rect, f_path, children[0], results)

                #     if rect[3] >= self.center[1]:
                #         # self.children[1]._intersect(rect, results, uniq)
                #         self._intersect(rect, f_path, children[1], results)
                # if rect[2] >= self.center[0]:
                #     if rect[1] <= self.center[1]:
                #         # self.children[2]._intersect(rect, results, uniq)
                #         self._intersect(rect, f_path, children[2], results)
                #     if rect[3] >= self.center[1]:
                #         # self.children[3]._intersect(rect, results, uniq)
                #         self._intersect(rect, f_path, children[3], results)
                if self.box_intersect(rect, (x - width/2, y, x, y + height/2)):
                    self._intersect(rect, f_path,children[1], results)
                if self.box_intersect(rect, (x - width/2, y - height/2, x, y)):
                    self._intersect(rect, f_path, children[2], results)
                if self.box_intersect(rect, (x, y - height/2, x + width/2, y)):
                    self._intersect(rect, f_path, children[3], results)
                if self.box_intersect(rect, (x, y, x + width/2, y + height/2)):
                    self._intersect(rect, f_path, children[0], results)
            # If at leaf, search and compare if uniq
            # this can be removed. Need test
            # else:
                # print("intersect some leaf levels")
            nodes = []
            counter = 0
            # (num_items) = unpack("l", f.read(8))
            # print(num_items, (x, y, width, height, depth, isLeaf))
            while counter < num_items:
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
                    results.append(node[0])
                        # uniq.add(_id)
        return results

    # def _insert_into_children(self, item, rect):
    #     if rect[0] <= self.center[0]:
    #         if rect[1] <= self.center[1]:
    #             self.children[0]._insert(item, rect)
    #             return
    #         elif rect[3] >= self.center[1]:
    #             self.children[1]._insert(item, rect)
    #             return
    #     elif rect[2] > self.center[0]:
    #         if rect[1] <= self.center[1]:
    #             self.children[2]._insert(item, rect)
    #             return
    #         elif rect[3] >= self.center[1]:
    #             self.children[3]._insert(item, rect)
    #             return
    #     raise Exception()

    # def _remove_from_children(self, item, rect):
    #     # if rect spans center then insert here
    #     if (rect[0] <= self.center[0] and rect[2] >= self.center[0] and
    #         rect[1] <= self.center[1] and rect[3] >= self.center[1]):
    #         node = _QuadNode(item, rect)
    #         self.nodes.remove(node)
    #     else:
    #         # try to remove from children
    #         if rect[0] <= self.center[0]:
    #             if rect[1] <= self.center[1]:
    #                 self.children[0]._remove(item, rect)
    #             if rect[3] >= self.center[1]:
    #                 self.children[1]._remove(item, rect)
    #         if rect[2] > self.center[0]:
    #             if rect[1] <= self.center[1]:
    #                 self.children[2]._remove(item, rect)
    #             if rect[3] >= self.center[1]:
    #                 self.children[3]._remove(item, rect)

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
            # call insert again, which would evoke insert into 
            # children if appropriate
            self._insert(node.item, node.rect)

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
        barray += pack('l', len(self.nodes))
        # print(len(barray))
        if len(self.children) is not 0:
            # print("parent")
            # parent node
            barray += pack('?', 0)
            children = self.children
            children_position = []
            for c in self.children:
                children_position.append(position)
                # print(children_position)
                if len(c.children) is not 0:
                    position += 48 + 1 + 32 + (len(c.nodes) * item_size)
                elif len(c.nodes) is not 0:
                    position += 48 + 1 + ((len(c.nodes)) * item_size)
                else: 
                    # print("empty")
                    children_position[-1] = -1
            # # print("out loop")
            # print(children_position)
            # print(len(barray))
            barray += pack('llll', children_position[0], children_position[1], children_position[2], children_position[3])
        else:
            # leaf node
            # print("writing a leaf node")
            # print(self.center[0], self.center[1], self.width, self.height, self._depth)
            barray += pack('?', 1)
            # print(len(self.nodes), position)
            if len(self.nodes) == 0:
                return bytearray(), [], position
            children = []

        # print("barray before item, ", len(barray))

        for node in self.nodes:
            (item, rect) = (node.item, node.rect)
            # print("item:", item)
            barray += pack("llllldddd", item[0], item[1], item[2], item[3], item[4], rect[0], rect[1], rect[2], rect[3])
            # pad to leaf node length
            # print(unpack("ddddl?", barray[0:41]))
        (x, y, width, height, depth, num_items, isLeaf) = unpack("ddddll?", barray[0:49])
        # print(x,y,width,height, num_items, isLeaf)
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
            self.bbox = bbox
            width, height = abs(x2-x1), abs(y2-y1)
            midx, midy = x1+width/2.0, y1+height/2.0
            
                # print(len(pack('qiiiqqqqq', 0x45504951, MAX_ITEMS, 64, 64,x1,y1,x2,y2,0)))
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
            x1, y1, x2, y2 = self.bbox
            f.write(pack('qiiiqqqqq', 0x45504951, MAX_ITEMS, 64, 64,x1,y1,x2,y2,0))
            position = 64
            f.seek(64)
            # print(len(self.nodes))
            if not super(Index, self).IsParent():
                position += 48 + 1 + 32 + (len(self.nodes) * item_size)
            else:
                position += 48 + 1 + (len(self.nodes) * item_size)
            # print(position-64)
            while q:
                t = q.pop(0)
                barray, children, position = t.convert_to_disk(position)
                # print("in to_disk:", len(barray))
                # print(position)
                f.write(barray)
                q += children
        return self.disk
