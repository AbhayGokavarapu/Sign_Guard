"""Rank plausible region pairs and balance comparisons across page pairs."""
from collections import defaultdict
from itertools import combinations
import math
import numpy as np
from PIL import Image


def _fingerprint(candidate):
    image=np.asarray(candidate.crop.convert('L').resize((32,16),Image.Resampling.BILINEAR),dtype=np.float32)
    # Normalised darkness is insensitive to image dimensions and overall paper brightness.
    image=(255-image).reshape(-1)
    return image/(np.linalg.norm(image)+1e-8)


def select_pairs(candidates,limit):
    ordered=sorted(candidates,key=lambda c:(int(c.page),tuple(map(int,c.bbox))))
    features=[_fingerprint(c) for c in ordered]
    groups=defaultdict(list)
    for i,j in combinations(range(len(ordered)),2):
        a,b=ordered[i],ordered[j]
        aw,ah=a.crop.size;bw,bh=b.crop.size
        aspect=math.exp(-abs(math.log(max(aw/ah,1e-6)/max(bw/bh,1e-6))))
        scale=math.exp(-abs(math.log(max(aw*ah,1)/max(bw*bh,1)))/2)
        appearance=float(np.dot(features[i],features[j]))
        score=.65*appearance+.25*aspect+.10*scale
        groups[(a.page,b.page)].append((score,i,j))
    for pairs in groups.values():pairs.sort(key=lambda p:(-p[0],p[1],p[2]))
    selected=[]
    # One best pair from each page-pair group before allocating additional comparisons.
    while groups and len(selected)<limit:
        round_keys=sorted(groups,key=lambda key:(-groups[key][0][0],key))
        for key in round_keys:
            score,i,j=groups[key].pop(0)
            selected.append((ordered[i],ordered[j],round(score,6)))
            if not groups[key]:del groups[key]
            if len(selected)>=limit:break
    return selected
