# -*- coding: utf-8 -*-
"""v26 最终：不放大任何图集，只在原有贴图空白处填中文；短文案(UI)用字优先。"""
import sys,os,json,struct,re,collections
ROOT=r"C:\Users\A.Aitherine\Documents\Codex\2026-10-10\s"
sys.path.insert(0,ROOT+r"\outputs"); sys.path.insert(0,ROOT+r"\work")
import skullgirls_gfs as G
from gdi_font import render
from dxt5enc import make_dds
VAN=r"E:\SteamLibrary\steamapps\common\Skullgirls\_sg_chs_backup_v2\data01_ui-win.gfs"
FACE="SimHei"
FONTS=["Main Menu Desc","Default Font","Dialogue Text","Confirm Label","Menu Text",
       "Comic Dialogue","Team Select Body Text","News Banner Body","Online Data","Gamertag"]
def dec(b):
    w=struct.unpack_from("<I",b,16)[0]; h=struct.unpack_from("<I",b,12)[0]
    d=b[128:]; bw=(w+3)//4; bh=(h+3)//4; al=bytearray(w*h); o=0
    for by in range(bh):
        for bx in range(bw):
            a0=d[o]; a1=d[o+1]; bits=int.from_bytes(d[o+2:o+8],"little")
            if a0>a1: tab=[a0,a1]+[((7-i)*a0+i*a1)//7 for i in range(1,7)]
            else: tab=[a0,a1]+[((5-i)*a0+i*a1)//5 for i in range(1,5)]+[0,255]
            for i in range(16):
                k=(bits>>(3*i))&7; x=bx*4+(i%4); y=by*4+(i//4)
                if x<w and y<h: al[y*w+x]=tab[k]
            o+=16
    return w,h,al
def blocks(d):
    out=[]
    for m in re.finditer(b"TNFG",d):
        i=m.start(); noff=i+12
        nm=d[noff:noff+64].split(b"\x00")[0]
        if not(2<=len(nm)<=40 and all(32<=c<127 for c in nm)): continue
        h=struct.unpack_from("<6I",d,noff+64)
        if not(h[1]==h[2] and h[1] in (256,512,1024,2048) and 0<h[5]<60000): continue
        if struct.unpack_from("<I",d,i+4)[0]!=100+40*h[5]: continue
        tbl=noff+88
        recs=[list(struct.unpack_from("<10I",d,tbl+40*k)) for k in range(h[5])]
        ns=1
        for k in range(1,h[5]):
            if 0<recs[k][0]<0x110000 and recs[k][0]>recs[k-1][0]: ns=k+1
            else: break
        out.append({"name":nm.decode("latin1"),"tag":i,"noff":noff,"h":list(h),"recs":recs,"ns":ns,"tbl":tbl})
    return out
cn={n:bytes(d) for n,d in G.iter_files(ROOT+r"\outputs\patch2\core.gfs")}
jc=json.loads(cn["core/localization/en_loc.json"].decode("utf-8"))
short=[];longc=[];s0=set();l0=set()
for v in jc.values():
    if not isinstance(v,str): continue
    tgt=short if len(v)<30 else longc; seen=tgt is short and s0 or l0
    for c in v:
        if 127<ord(c)<0x110000 and c not in seen: seen.add(c); tgt.append(c)
cnt=collections.Counter()
for v in jc.values():
    if isinstance(v,str): cnt.update(v)
rank=short+longc+[c for c,_ in cnt.most_common() if 127<ord(c)<0x110000 and c not in s0 and c not in l0]
seen=set(); order=[]
for c in rank:
    if c not in seen: seen.add(c); order.append(c)
print("候选字 %d（UI优先 %d）"%(len(order),len(short)))
entries=[(n,bytes(d)) for n,d in G.iter_files(VAN)]
idx={n:i for i,(n,b) in enumerate(entries)}
ref={}
for n,b in entries:
    if not n.endswith(".gbs"): continue
    for bl in blocks(b):
        if bl["name"] not in ref: ref[bl["name"]]=bl
add={}
skipped=[]
for f in FONTS:
    if f not in ref: continue
    key="ui/Win/Fonts/%s_0.dds"%f
    if key not in idx: continue
    if ref[f]["ns"]<ref[f]["h"][5]:
        skipped.append(f); continue
    W,H,al=dec(entries[idx[key]][1]); h=ref[f]["h"]; L=h[1]; S=W/float(L)
    occ=bytearray(W*H)
    for r in ref[f]["recs"][:ref[f]["ns"]]:
        tx,ty,tw,th=int(r[2]*S),int(r[3]*S),int(r[4]*S),int(r[5]*S)
        for y in range(max(0,ty-2),min(H,ty+th+2)):
            for x in range(max(0,tx-2),min(W,tx+tw+2)): occ[y*W+x]=1
    CT=max(12,int(round(h[0]*0.55*S)))
    per=W//CT; cells=[]
    for cyi in range(per):
        for cxi in range(per):
            cx,cy=cxi*CT,cyi*CT; free=True
            for y in range(cy,cy+CT):
                for x in range(cx,cx+CT):
                    if occ[y*W+x]: free=False; break
                if not free: break
            if free: cells.append((cx,cy))
    n=min(len(order),len(cells)); recs=[]
    for i in range(n):
        cx,cy=cells[i]
        w2,h2,px=render([order[i]],FACE,int(CT*0.9),CT,CT,1)
        for y in range(CT):
            d0=(cy+y)*W+cx
            al[d0:d0+CT]=px[y*w2:y*w2+CT]
        recs.append([ord(order[i]),0,int(round(cx/S)),int(round(cy/S)),int(round(CT/S)),int(round(CT/S)),h[3],int(round(CT/S)),1,0])
    entries[idx[key]]=(key,make_dds(bytes(al),W,H))
    add[f]=recs
    print("  %-24s 图%dx%d(未变) 格%2dpx 可放%5d 填%5d"%(f,W,H,CT,len(cells),n))
for e,(n,b) in enumerate(entries):
    if not n.endswith(".gbs"): continue
    data=bytearray(b); dirty=False
    for bl in sorted(blocks(bytes(data)),key=lambda x:-x["tag"]):
        f=bl["name"]
        if f not in add: continue
        tbl=bl["noff"]+88; ns=bl["ns"]; h=bl["h"]
        have=set(r[0] for r in bl["recs"][:ns])
        a2=[r for r in add[f] if r[0] not in have]
        if not a2: continue
        allg=sorted(bl["recs"][:ns]+a2,key=lambda r:r[0]); tail=bl["recs"][ns:]
        delta=40*len(a2); ins=tbl+40*ns
        data[ins:ins]=b"\x00"*delta
        for off in (0x04,0x28,0x2C,0x30,0x34):
            v=struct.unpack_from("<I",data,off)[0]
            if v>ins: struct.pack_into("<I",data,off,v+delta)
        hh=list(h); hh[5]=len(allg)+len(tail)
        struct.pack_into("<6I",data,bl["noff"]+64,*hh)
        struct.pack_into("<I",data,bl["tag"]+4,100+40*hh[5])
        for k,r in enumerate(allg+tail): struct.pack_into("<10I",data,tbl+40*k,*r)
        dirty=True
    if dirty: entries[e]=(n,bytes(data))
os.makedirs(ROOT+r"\outputs\patch23",exist_ok=True)
open(ROOT+r"\outputs\patch23\ui-win.gfs","wb").write(G.build(entries))
open(ROOT+r"\outputs\patch23\core.gfs","wb").write(G.build([(n,bytes(d)) for n,d in G.iter_files(ROOT+r"\outputs\patch2\core.gfs")]))
print("跳过(带块尾数据):",skipped)
print("built patch23")
