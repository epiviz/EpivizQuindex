from pyqtree import Index
import pickle
import sys
class Point(object):

    def __init__(self, start, end, offset, length, fileName):
        x = start//16000
        y = start%16000
        self.bbox = (x, y, x+1, y+1)
        self.start = start
        self.end = end
        self.offset = offset
        self.length = length
        self.fileName = fileName

    def __repr__(self):
        return str((self.start, self.end, self.offset, self.fileName))

tree = Index(bbox=(0, 0, 16001, 16001))

data = pickle.load(open( "result1.p", "rb"))
print(len(data))
for entry in data:
    # print(entry)
    (start, end, offset, length, fileName) = (entry[0], entry[1], entry[2], entry[3], 1)
    tree.insert((start, end, offset, length, fileName), (start//16000, start%16000, start//16000 + 1, start%16000 + 1))

data = pickle.load(open( "result2.p", "rb"))
print(len(data))
for entry in data:
    # print(entry)
    (start, end, offset, length, fileName) = (entry[1], entry[3], entry[4], entry[5], 2)
    tree.insert((start, end, offset, length, fileName), (start//16000, start%16000, start//16000 + 1, start%16000 + 1))

# repeating to see overhead
data = pickle.load(open( "result1.p", "rb"))
print(len(data))
for entry in data:
    # print(entry)
    (start, end, offset, length, fileName) = (entry[0], entry[1], entry[2], entry[3], 3)
    tree.insert((start, end, offset, length, fileName), (start//16000, start%16000, start//16000 + 1, start%16000 + 1))


# need to store the mapping of file names to node ids
map = {
    39033: 1,
    39031: 2
}

overlapbbox = (1, 1, 860, 860)
matches = tree.intersect(overlapbbox)
print("intersect comes back")

print(len(matches))

# print(matches[0])
print("all matched nodes")
print("format is (start, end, offset, length, fileName)")
for item in matches:    
    print(item)
    print(sys.getsizeof(item))
# print(sys.getsizeof(data))