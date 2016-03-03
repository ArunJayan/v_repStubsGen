from function import *
from struct import *
from variable import *

a1 = Variable('s','const char*','NULL')
f = Function('foo', args=[a1], body='if(s) print(s); else print("Hello world!");')
s = Struct('Bar', fields=[a1])

objs = [f, s]

for obj in objs:
    print(obj.declaration())

for obj in objs:
    print(obj.definition())
