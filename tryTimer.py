import time
import numpy as np
import gc

a=[]
start=time.time()
for i in range(10000000):
    a.extend([[i,i+1,i+2]])
end=time.time()
print(end-start)

a=[]
start=time.time()
for i in range(10000000):
    a.append([i,i+1,i+2])
end=time.time()
print(end-start)

a=[]
start=time.time()
gc.disable()
for i in range(10000000):
    a.append([i,i+1,i+2])
gc.enable()
end=time.time()
print(end-start)

# a=[]
# start=time.time()
# for i in range(10000000):
#     a.insert(0,[i,i+1,i+2])
# end=time.time()
# print(end-start)


a=np.zeros(10000000).tolist()
start=time.time()
for i in range(10000000):
    a[i]=[i,i+1,i+2]
end=time.time()
print(end-start)

from collections import deque
from queue import Queue
class LifoQueue(Queue):

    def _init(self, maxsize):
        self.queue = []

    def _qsize(self):
        return len(self.queue)

    def _put(self, item):
        self.queue.append(item)

    def _get(self):
        return self.queue.pop()
        
start=time.time()
a=LifoQueue()
for i in range(10000000):
    a._put([i,i+1,i+2])
end=time.time()
print(end-start)