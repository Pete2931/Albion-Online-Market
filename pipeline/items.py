# Name of items and range of tiers they have also if they have enchants
items = {"BAG" : (4,8,True),
         "2H_TOOL_KNIFE" : (4,8,False),
         "CAPE" : (4,8,True)}
tiers = ["T" + str(c) for c in range(1,9)]

def getAllItemsList(items = items, tiers = tiers):
    res = []
    for i in items:
        for t in range(items[i][0],(items[i][1]+1)):
            res.append(f"{tiers[t-1]}_{i}")
            if (items[i][2] == True):
                for e in range(1,5):
                    res.append(f"{tiers[t-1]}_{i}@{e}")
    return res