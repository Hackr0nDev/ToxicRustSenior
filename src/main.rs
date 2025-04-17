f = open("9-253.txt")
count = 0
k = 0
for i in f:
    s = i.split()
    a = sorted([int(x) for x in s])
    a1 = [x for x in a if a.count(x) == 3]
    a2 = [x for x in a if a.count(x) == 1]
    a3 = [x for x in a1 if a1.count(x) == 3]
    if len(a3) == 6 and sum(a3)/6 < a2[0]:
        k = k +a2[0]
print(k)
