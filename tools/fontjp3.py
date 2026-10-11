# -*- coding: utf-8 -*-
"""v20(日文槽·顶替)：把 _JP 字体原有字形记录改写成中文，图集/页数/条数全不变。"""
import sys,os,json,struct,re,collections
ROOT=r"C:\Users\A.Aitherine\Documents\Codex\2026-10-10\s"
sys.path.insert(0,ROOT+r"\outputs"); sys.path.insert(0,ROOT+r"\work")
import skullgirls_gfs as G
from gdi_font import render
from dxt5enc import make_dds
VAN=r"E:\SteamLibrary\steamapps\common\Skullgirls\_sg_chs_backup_v2\data01_ui-win.gfs"
FACE="SimHei"
def decode_alpha(b):
    w=struct.unpack_from("<I",b,16)[0]; h=struct.unpack_from("<I",b,12)[0]
    data=b[128:]; bw=(w+3)//4; bh=(h+3)//4
    al=bytearray(w*h); off=0
    for by in range(bh):
        for bx in range(bw):
            a0=data[off]; a1=data[off+1]; bits=int.from_bytes(data[off+2:off+8],"little")
            if a0>a1: tab=[a0,a1]+[((7-i)*a0+i*a1)//7 for i in range(1,7)]
            else: tab=[a0,a1]+[((5-i)*a0+i*a1)//5 for i in range(1,5)]+[0,255]
            for i in range(16):
                k=(bits>>(3*i))&7; x=bx*4+(i%4); y=by*4+(i//4)
                if x<w and y<h: al[y*w+x]=tab[k]
            off+=16
    return w,h,al
def blocks(data):
    out=[]
    for m in re.finditer(b"TNFG",data):
        i=m.start(); noff=i+12
        nm=data[noff:noff+64].split(b"\x00")[0]
        if not(2<=len(nm)<=40 and all(32<=c<127 for c in nm)): continue
        h=struct.unpack_from("<6I",data,noff+64)
        if not(h[1]==h[2] and h[1] in (256,512,1024,2048) and 0<h[5]<60000): continue
        if struct.unpack_from("<I",data,i+4)[0]!=100+40*h[5]: continue
        tbl=noff+88
        recs=[list(struct.unpack_from("<10I",data,tbl+40*k)) for k in range(h[5])]
        out.append({"name":nm.decode("latin1"),"tag":i,"noff":noff,"h":list(h),"recs":recs,"tbl":tbl})
    return out
cn={n:bytes(d) for n,d in G.iter_files(ROOT+r"\outputs\patch2\core.gfs")}
jc=json.loads(cn["core/localization/en_loc.json"].decode("utf-8"))
cnt=collections.Counter()
for v in jc.values():
    if isinstance(v,str): cnt.update(v)
longc=[];seen0=set()
for v in jc.values():
    if isinstance(v,str) and len(v)>=30:
        for c in v:
            if 127<ord(c)<0x110000 and c not in seen0: seen0.add(c); longc.append(c)
rank=list(longc)+[c for c,_ in cnt.most_common() if 127<ord(c)<0x110000 and c not in seen0]
seen=set(); order=[]
for c in rank:
    if c not in seen: seen.add(c); order.append(c)
print("汉字 %d"%len(order))
entries=[(n,bytes(d)) for n,d in G.iter_files(VAN)]
idx={n:i for i,(n,b) in enumerate(entries)}
ref={}
for n,b in entries:
    if not n.endswith(".gbs"): continue
    for bl in blocks(b):
        if bl["name"] not in ref: ref[bl["name"]]=bl
jpfonts=[k for k in ref if k.endswith("_JP")]
print("_JP 字体 %d 个"%len(jpfonts))
newrec={}
for f in jpfonts:
    key="ui/Win/Fonts/%s_0.dds"%f
    if key not in idx: continue
    h=ref[f]["h"]; recs=ref[f]["recs"]; L=h[1]
    W,H,al=decode_alpha(entries[idx[key]][1]); S=W/float(L)
    k0=0
    for j in range(len(recs)):
        if recs[j][0]>=0x2000: k0=j; break
    slots=len(recs)-k0
    K=min(len(order),slots)
    out=list(recs)
    for i in range(K):
        r=recs[k0+i]; cx,cy,tw,th=int(r[2]*S),int(r[3]*S),int(r[4]*S),int(r[5]*S)
        tw=max(6,min(tw,H-cy)); th=max(6,min(th,H-cy))
        if tw<6 or th<6 or cx+tw>W or cy+th>H: continue
        px=render([order[i]],FACE,int(min(tw,th)*0.95),tw,th,1)[2]
        for y in range(cy,cy+th):
            d0=y*W+cx
            al[d0:d0+tw]=px[(y-cy)*tw:(y-cy)*tw+tw]
        out[k0+i]=[ord(order[i]),r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9]]
    newrec[f]=out
    entries[idx[key]]=(key,make_dds(bytes(al),W,H))
    print("  %-24s 原有%5d 拉丁保留%3d 顶替CJK%5d/%d (贴图%dx%d 未变)"%(f,len(recs),k0,K,slots,W,H))
for e,(n,b) in enumerate(entries):
    if not n.endswith(".gbs"): continue
    data=bytearray(b); dirty=False
    for bl in blocks(bytes(data)):
        f=bl["name"]
        if f not in newrec: continue
        tbl=bl["noff"]+88
        for i,r in enumerate(newrec[f]): struct.pack_into("<10I",data,tbl+40*i,*r)
        dirty=True
    if dirty: entries[e]=(n,bytes(data))
os.makedirs(ROOT+r"\outputs\patch16",exist_ok=True)
open(ROOT+r"\outputs\patch16\ui-win.gfs","wb").write(G.build(entries))
entries2=[(n,(cn["core/localization/en_loc.json"] if n=="core/localization/jp_loc.json" else bytes(d))) for n,d in G.iter_files(ROOT+r"\outputs\patch2\core.gfs")]
open(ROOT+r"\outputs\patch16\core.gfs","wb").write(G.build(entries2))
print("built patch16")
