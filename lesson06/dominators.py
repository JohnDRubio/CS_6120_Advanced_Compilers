import cfg

'''
    input: CFG

    output: map: label -> set of labels
            where label represents some node
            in CFG, A, and set of labels are the nodes
            that dominate A
'''
def getDominators(c, predecessors):
    dom = {}        # map from label to set
    changing = True

    while changing:
        prevDom = dom.copy()
        for vertex in c:
            dominatorsOfPredecessors = []   # list of sets
            for predecessor in cfg.getPredecessors(vertex,predecessors):
                if predecessor in dom:
                    dominatorsOfPredecessors.append(dom[predecessor])
            intersection = set.intersection(*dominatorsOfPredecessors) if dominatorsOfPredecessors else set()
            intersection.add(vertex)
            dom[vertex] = intersection.copy()
            changing = prevDom == dom
    return dom

def doesStrictlyDominate(A, B, dom):
    return A in dom[B] and A != B

def doesImmediatelyDominate(A, B, dom):
    if A not in dom[B] or A == B:
        return False
    
    strictlyDominatesB = set()
    for vertex in dom:
        if doesStrictlyDominate(vertex, B, dom):
            strictlyDominatesB.add(vertex)

    for vertex in strictlyDominatesB:
        if doesStrictlyDominate(A, vertex, dom):
            return False

    return True

def getDominatorTree(dom):
    domTree = {}
    for vertex in dom:
        for dominator in dom[vertex]:
            if doesImmediatelyDominate(dominator,vertex,dom):
                if dominator not in domTree:
                    domTree[dominator] = set()
                domTree[dominator].add(vertex)
    return domTree

def inDominanceFrontier(A, B, dom, predecessors):
    if doesStrictlyDominate(A,B,dom) or A == B:
        return False  
    preds = cfg.getPredecessors(B, predecessors)

    # Here, we ran into a weird situation where: 
    #     A is a pred of B 
    #     A does not dominate B 
    #     BUT A dominates itself therefore B is in the dom frontier of A
    for pred in preds:
        if A in dom[pred]: 
            return True
    return False

def getDominanceFrontier(dom,predecessors):
    domFrontier = {}
    for A in dom:
        for B in dom:
            if inDominanceFrontier(A,B,dom,predecessors):
                if A not in domFrontier:
                    domFrontier[A] = set()
                domFrontier[A].add(B)
    return domFrontier 