# Name of items and range of tiers they have also if they have enchants
items = {"BAG" : (4,8,True,"Bags","Bags"),
         "2H_TOOL_KNIFE" : (4,8,False,"Gathering Equipment","Hide"),
         "CAPE" : (4,8,True,"Capes","Cape"),
         "HEAD_GATHERER_HIDE" : (4,8,True,"Gathering Equipment","Hide"),
         "ARMOR_GATHERER_HIDE" : (4,8,True,"Gathering Equipment","Hide"),
         "SHOES_GATHERER_HIDE" : (4,8,True,"Gathering Equipment","Hide"),
         "BACKPACK_GATHERER_HIDE" : (4,8,True,"Gathering Equipment","Hide"),
         "LEATHER" : (2,8,False,"Resources","Refined Resources"),
         "PLANKS" : (2,8,False,"Resources","Refined Resources"),
         "METALBAR" : (2,8,False,"Resources","Refined Resources"),
         "STONEBLOCK" : (2,8,False,"Resources","Refined Resources")}
tiers = ["T" + str(c) for c in range(1,9)]

# Returns the list of all item_id's from the items dictionary according to their specifications
def getAllItemsList(items = items, tiers = tiers):
    res = []
    for i in items:
        for t in range(items[i][0],(items[i][1]+1)):
            res.append(f"{tiers[t-1]}_{i}")
            if (items[i][2] == True):
                for e in range(1,5):
                    res.append(f"{tiers[t-1]}_{i}@{e}")
    return res

# Get all of the item details in a dictionary which corresponds to the 
def getAllItemDetailsDict(items = items, tiers = tiers):
    res = {
        'item_id' : [],
        'name' : [],
        'tier' : [],
        'enchantment' : [],
        'category' : [],
        'subcategory' : []
    }
    for i in items:
        for t in range(items[i][0], (items[i][1] + 1)):
            res['item_id'].append(f"{tiers[t-1]}_{i}")
            res['name'].append(i)
            res['tier'].append(t)
            res['enchantment'].append(0)
            res['category'].append(items[i][3])
            res['subcategory'].append(items[i][4])
            if (items[i][2] == True):
                for e in range(1,5):
                    res['item_id'].append(f"{tiers[t-1]}_{i}@{e}")
                    res['name'].append(i)
                    res['tier'].append(t)
                    res['enchantment'].append(e)
                    res['category'].append(items[i][3])
                    res['subcategory'].append(items[i][4])
    return res