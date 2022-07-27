## heavily modefied quadtree implementation from
## https://github.com/karimbahgat/Pyqtree

import sys
from struct import *
from shapely.geometry import Polygon

MAX_ITEMS = 50
MAX_DEPTH = 20
# size of each item
# leaf_size = 48 + 1 + ((Item_numbers) * self.item_size)
# parent_size = 48 + 1 + 32 + ((Item_numbers) * self.item_size)

def _normalize_rect(rect):
    '''
    Fix the format of the query rectangular box to lower left x, y and top right x, y.

        Parameters:
        - **rect (array)**: Array of coordinates.

        Returns:
        - **coordinates (x1, y1, x2, y2) **: lower left x, y and top right x, y coordinates.
    '''
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
    '''
    helper method to loop the children.

        Parameters:
        - **parent (_Quadtree)**: _Quadtree node object
    '''
    for child in parent.children:
        if child.children:
            for subchild in _loopallchildren(child):
                yield subchild
        yield child


def box_intersect(box1, box2):
    '''
    Determin whether the two bounding box intersect.

        Parameters:
        - **box1 (tuple)**: bottom left, top right coordinate of a bounding box.
        - **box2 (tuple)**: bottom left, top right coordinate of a bounding box.

        Returns:
        - **box_intersect (bool)**: Whether the two bounding box intersect.
   
    '''
    p1 = Polygon([(box1[0], box1[1]), (box1[0], box1[3]), (box1[2], box1[3]), (box1[2], box1[1])])
    p2 = Polygon([(box2[0], box2[1]), (box2[0], box2[3]), (box2[2], box2[3]), (box2[2], box2[1])])

    return p1.intersects(p2)

def box_contains(box1, box2):
    '''
    Determin whether the box 1 contains box 2.

        Parameters:
        - **box1 (tuple)**: bottom left, top right coordinate of a bounding box.
        - **box2 (tuple)**: bottom left, top right coordinate of a bounding box.

        Returns:
        - **box_contains (bool)**: whether the box 1 contains box 2.
   
    '''

    # print(box1, box2)
    return (box1[0] <= box2[0]) and (box1[1] <= box2[1]) and (box1[2] >= box2[2]) and (box1[3] >= box2[3])


class _QuadNode(object):
    '''
    Quadtree node object that contains the data and the rectangular bounding box..

        Parameters:
        - **parent (_Quadtree)**: _Quadtree node object
    '''
    def __init__(self, item, rect):
        self.item = item
        self.rect = rect

    def __eq__(self, other):
        return self.item == other.item and self.rect == other.rect

    def __hash__(self):
        return hash(self.item)

    def pack_items(self, mappings):
        b_array = bytes()
        for i, t in zip(self.item, mappings.values()):
            f = None
            if t == int:
                f = 'l'
            elif t == float:
                f = 'd'
            b_array += pack(f, i)
        return b_array



class _QuadTree(object):
    """
    Internal backend version of the index.
    The index being used behind the scenes. Has all the same methods as the user
    index, but requires more technical arguments when initiating it than the
    user-friendly version.
    """

    def __init__(self, x = None, y = None, width = None, height = None, max_items = None, max_depth = None, _depth=0 , path = None, offset = None, extra = [], field_str = None):
        '''
        Initialize the current node.

            Parameters:
            - **x (int)**: x coordinate of the center of the node's bounding box.
            - **y (int)**: y coordinate of the center of the node's bounding box.
            - **width (int)**: width of the the node's bounding box.
            - **height (int)**: height of the node's bounding box.
            - **max_items (int)**: maximum number of items in a node before splitting.
            - **max_depth (int)**: maximum depth of the index. the index will stop splitting after reaching max depth.
            - **_depth (int)**: depth of the current node.
            - **path (str)**: path to the precomputed index. If None, node will be computed in memory.
            - **offset (int)**: file offset to the node. 

       
        '''
        self.nodes = []
        self.children = []
        self.isLeaf = True
        self.center = (x, y)
        self.extra = {}
        self.width, self.height = width, height
        self.max_items = max_items
        self.max_depth = max_depth
        self._depth = _depth
        self.item_size = 4 * 8
        self.field_str = field_str
        for function in ["start", "end", "offset", "size", "fileid"]:

            self.add_field(function, int)
        if path:
            self._from_disk(path, offset)

    def __iter__(self):
        for child in _loopallchildren(self):
            yield child

    def add_field(self, function, t):
        self.extra[function] = t
        if t == int or t == float:
            self.item_size += 8
        else:
            exception('type not supported')

    def get_field_str(self):
        field_str = ""
        for t in self.extra.values():
            if t == int:
                field_str += 'l'
            elif t == float:
                field_str += 'd'
            else:
                exception('type not supported')
        return bytes(field_str, 'utf-8')


    def IsParent(self):
        '''
        Helper method to determin whether the node is a parent node..

            Parameters:

            Returns:
            -**IsParent (bool)**: Whether the node is a parent node.
       
        '''
        return len(self.children) == 0

    def hasData(self):
        '''
        Helper method to determin whether the node contains data.

            Parameters:

            Returns:
            - **hasData (bool)**: Whether the node contains data.
       
        '''
        return len(self.nodes) != 0

    def _insert(self, item, bbox):
        '''
        Insert the item into the index.

            Parameters:
            - **item**: data to be inserted.
            - **bbox (tuple)**: bounding box of the item.

            Returns:
       
        '''
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



    def _intersect_memory(self, rect, results = None, debug = False, parent_contains = False):
        '''
        Recursively return nodes that intersect with the bounding box in memory. This method requires the index preloaded in memory.

            Parameters:
            - **rect (tuple)**: a tuple that represents the bottom left, top right coorinates of a bounding box.
            - **results (list)**:   recursive result array to store the parsed leaf nodes.     
            - **debug (bool)**: When true, the results also include the bounding box of each entry. 
            Returns:
            - **results (list)**:   recursive result array to store the parsed leaf nodes.    
       
        '''
        if results == None:
            results = []

        contains = parent_contains or box_contains(rect, (self.center[0] - self.width/2, self.center[1] - self.height/2, self.center[0] + self.width/2, self.center[1] + self.height/2))
        # print(contains)


        if not self.isLeaf:
            if (self.children[1] != None) and (contains or box_intersect(rect, (self.center[0] - self.width/2, self.center[1], self.center[0], self.center[1] + self.height/2))):
                self.children[1]._intersect_memory(rect, results, parent_contains = contains)
            if (self.children[2] != None) and (contains or box_intersect(rect, (self.center[0] - self.width/2, self.center[1] - self.height/2, self.center[0], self.center[1]))):
                self.children[2]._intersect_memory(rect, results, parent_contains = contains)
            if (self.children[3] != None) and (contains or box_intersect(rect, (self.center[0], self.center[1] - self.height/2, self.center[0] + self.width/2, self.center[1]))):
                self.children[3]._intersect_memory(rect, results, parent_contains = contains)
            if (self.children[0] != None) and (contains or box_intersect(rect, (self.center[0], self.center[1], self.center[0] + self.width/2, self.center[1] + self.height/2))):
                self.children[0]._intersect_memory(rect, results, parent_contains = contains)


        # if not self.isLeaf:
        #     if self.children[1] and box_intersect(rect, (self.center[0] - self.width/2, self.center[1], self.center[0], self.center[1] + self.height/2)):
        #         self.children[1]._intersect_memory(rect, results)
        #     if self.children[2] and box_intersect(rect, (self.center[0] - self.width/2, self.center[1] - self.height/2, self.center[0], self.center[1])):
        #         self.children[2]._intersect_memory(rect, results)
        #     if self.children[3] and box_intersect(rect, (self.center[0], self.center[1] - self.height/2, self.center[0] + self.width/2, self.center[1])):
        #         self.children[3]._intersect_memory(rect, results)
        #     if self.children[0] and box_intersect(rect, (self.center[0], self.center[1], self.center[0] + self.width/2, self.center[1] + self.height/2)):
        #         self.children[0]._intersect_memory(rect, results)

        for node in self.nodes:
            if box_intersect(rect, node.rect):
            # (
                if debug:
                    results.append(node.item + node.rect)
                else:
                    results.append(node.item)
        return results

    def _intersect_file(self, rect, f_path, offset = None, results=None, debug = False, parent_contains = False):
        '''
        Recursively return nodes that intersect with the bounding box in the index located in a file.

            Parameters:
            - **rect (tuple)**: a tuple that represents the bottom left, top right coorinates of a bounding box.
            - **f_path (str)**: path to the index.
            - **offset (int)**: byte offset to the node.
            - **results (list)**:   recursive result array to store the parsed leaf nodes.     
            - **debug (bool)**: When true, the results also include the bounding box of each entry. 
            Returns:
            - **results (list)**:   recursive result array to store the parsed leaf nodes.    
       
        '''
        if results == None:
            results = []
        if offset == -1:
            return results
        # if offset is None:
        #     raise Exception("memory search not implemented")
        with open(f_path, 'rb') as f:
            f.seek(offset)
            a = f.read(48 + 1)
            if offset < 80:
                raise Exception()
            (x, y, width, height, depth, num_items, isLeaf) = unpack("ddddll?", a)

            contains = parent_contains or box_contains(rect, (x - width/2, y - height/2, x + width/2, y + height/2))

            # search children
            if not isLeaf:
                children = unpack("llll", f.read(32))
                if contains or box_intersect(rect, (x - width/2, y, x, y + height/2)):
                    # print(1)
                    self._intersect_file(rect, f_path,children[1], results, parent_contains = contains)
                if contains or box_intersect(rect, (x - width/2, y - height/2, x, y)):
                    # print(2)
                    self._intersect_file(rect, f_path, children[2], results, parent_contains = contains)
                if contains or box_intersect(rect, (x, y - height/2, x + width/2, y)):
                    # print(3)
                    self._intersect_file(rect, f_path, children[3], results, parent_contains = contains)
                if contains or box_intersect(rect, (x, y, x + width/2, y + height/2)):
                    # print(4)
                    self._intersect_file(rect, f_path, children[0], results, parent_contains = contains)
            # if not isLeaf:
            #     children = unpack("llll", f.read(32))
            #     if box_intersect(rect, (x - width/2, y, x, y + height/2)):
            #         # print(1)
            #         self._intersect_file(rect, f_path,children[1], results)
            #     if box_intersect(rect, (x - width/2, y - height/2, x, y)):
            #         # print(2)
            #         self._intersect_file(rect, f_path, children[2], results)
            #     if box_intersect(rect, (x, y - height/2, x + width/2, y)):
            #         # print(3)
            #         self._intersect_file(rect, f_path, children[3], results)
            #     if box_intersect(rect, (x, y, x + width/2, y + height/2)):
            #         # print(4)
            #         self._intersect_file(rect, f_path, children[0], results)
            nodes = []
            counter = 0

            while counter < num_items:
                counter += 1
                node_item = unpack(self.field_str, f.read(self.item_size - 4*8))
                node_rect = unpack("dddd", f.read(4*8))
                if node_item[2] == 0:
                    break
                else:
                    nodes.append((node_item, node_rect))
            for node in nodes:
                if box_intersect(rect, node[1]):
                    if debug:
                        results.append(node[0] + node[1])
                    else:
                        results.append(node[0])
        return results

    def _split(self):
        '''
        convert the current node into a parent node, spawn 4 child nodes and insert the current node's data into children.

            Parameters:

            Returns:
       
        '''
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
        '''
        pack the current node into binary, and prepare the children node if there is any.

            Parameters:
            - **position (int)**: position to the offest in the file, this is to compute the file offest for the children nodes.

            Returns:
            - **barray (bytes)**: bytes of the current node.
            - **children (_QuadTree)**: children node objects if any.
            - **position (int)**: byte position to the current end of file after adding the current node.
       
        '''
        barray = pack('ddddl', self.center[0], self.center[1], self.width, self.height, self._depth)
        barray += pack('l', len(self.nodes))
        if len(self.children) != 0:
            # parent node
            barray += pack('?', 0)
            children = self.children
            children_position = []
            for c in self.children:
                children_position.append(position)
                if len(c.children) != 0:
                    position += 48 + 1 + 32 + (len(c.nodes) * self.item_size)
                elif len(c.nodes) != 0:
                    position += 48 + 1 + ((len(c.nodes)) * self.item_size)
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
            # barray += pack("lllll", item[0], item[1], item[2], item[3], item[4])
            barray += node.pack_items(self.extra)
            barray += pack("dddd", rect[0], rect[1], rect[2], rect[3])
        return barray, children, position

    def _from_disk(self, f_path, offset):
        '''
        load a node from file.

            Parameters:
            - **f_path (str)**: path to the pre-computed index.
            - **offset (int)**: position to the offest in the file. This offset contains the location of the node

            Returns:
       
        '''
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
                node = unpack(self.field_str, f.read(self.item_size - 4*8))
                rect = unpack("dddd", f.read(4*8))
                node = _QuadNode(node, rect)
                self.nodes.append(node)

        # parse the children outside so that no multiple file pointers opened 
        self.children = []
        for child in children:
            if child != -1:
                self.children.append(_QuadTree(path = f_path, offset = child, field_str = self.field_str))
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
        # print(disk, first_run)
        if disk and first_run:
            self.from_disk(disk)
        elif disk:
            self.disk = disk
        elif bbox != None:
            
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
            t = self._intersect_memory(bbox, debug = debug)
            return t
        else:
            self.read_header()
            t = self._intersect_file(bbox, self.disk, 80+len(self.field_str), debug = debug)
            return t

    def read_header(self):
        header = None
        with open(self.disk, 'rb') as f:
            header = unpack('qiiiqqqqqll', f.read(80))
            (magic, max_item, _, _, x1, y1, x2, y2, _, item_size, field_str_len) = header
            
            if magic != 0x45504951:
                raise Exception("File magic mismatch")
            self.item_size = item_size
            self.bbox = (x1, y1, x2, y2)
            self.max_item = max_item
            self.field_str = f.read(field_str_len).decode("utf-8")

    def from_disk(self, f_path):
        '''
        Constructs a quadtree index from a precomputed file and store it in the current node.
        Parameters:
        - **f_path**: a string containing the path to the precomputed index.

        '''
        self.disk = f_path
        self.read_header()
        self.nodes = []
        self._from_disk(f_path, 80+len(self.field_str))

    def to_disk(self, path):
        '''
        Converts a quadtree index to file format and output it to disk.
        Parameter:
        - **path**: a string that contains the path to which the tree will be stored at.
    
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
            field_str = self.get_field_str()
            f.write(pack('qiiiqqqqqll', 0x45504951, MAX_ITEMS, 64, 64,x1,y1,x2,y2,0, self.item_size, len(field_str)))
            f.write(field_str)
            position = 80 + len(field_str)
            f.seek(position)
            if not super(Index, self).IsParent():
                position += 48 + 1 + 32 + (len(self.nodes) * self.item_size)
            else:
                position += 48 + 1 + (len(self.nodes) * self.item_size)

            while q:
                t = q.pop(0)
                barray, children, position = t._to_disk(position)
                f.write(barray)
                q += children
        return self.disk
