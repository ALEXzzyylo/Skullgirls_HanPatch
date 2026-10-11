# -*- coding: utf-8 -*-
"""最终版：逐字体选放大倍数k，装全量汉字；advance=字号（全角）。"""
import sys,os,json,struct,re,collections,math,zlib,subprocess
ROOT=r"C:\Users\A.Aitherine\Documents\Codex\2026-10-10\s"
sys.path.insert(0,ROOT+r"\outputs"); sys.path.insert(0,ROOT+r"\work")
import skullgirls_gfs as G
from gdi_font import render
from dxt5enc import make_dds
VAN=r"E:\SteamLibrary\steamapps\common\Skullgirls\_sg_chs_backup_v2\data01_ui-win.gfs"
FACE="SimHei"
FONTS=["Dialogue Text","Default Font","Main Menu Desc","Confirm Label","Guilded Header",
       "Data Frame Text","RityRemix Ingame Hud","SelznickTitleTexOtl","News Banner Body","AttractText"]
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
        out.append({"name":nm.decode("latin1"),"tag":i,"noff":noff,"h":list(h)})
    return out
cn={n:bytes(d) for n,d in G.iter_files(ROOT+r"\outputs\patch2\core.gfs")}
jc=json.loads(cn["core/localization/en_loc.json"].decode("utf-8"))
ch=json.load(open(ROOT+r"\outputs\patch2\characters.json",encoding="utf-8"))
cnt=collections.Counter()
for v in jc.values():
    if isinstance(v,str): cnt.update(v)
long_chars=[]
for v in jc.values():
    if isinstance(v,str) and len(v)>=40:
        for c in v:
            if 127<ord(c)<0x110000 and c not in long_chars: long_chars.append(c)
rank=[];seen=set()
for c in long_chars:
    if c not in seen: seen.add(c); rank.append(c)
for c,_ in cnt.most_common():
    if c not in seen and 127<ord(c)<0x110000: seen.add(c); rank.append(c)
for c in ch["cjk"]:
    if c not in seen: seen.add(c); rank.append(c)
print("汉字 %d"%len(rank))
entries=[(n,bytes(d)) for n,d in G.iter_files(VAN)]
idx={n:i for i,(n,b) in enumerate(entries)}
ref={}
for n,b in entries:
    if not n.endswith(".gbs"): continue
    for bl in blocks(b):
        if bl["name"] not in ref: ref[bl["name"]]=bl
add={}; stats=[]
for f in FONTS:
    if f not in ref: continue
    key="ui/Win/Fonts/%s_0.dds"%f
    if key not in idx: continue
    W,H,al=decode_alpha(entries[idx[key]][1])
    L=ref[f]["h"][1]; S=W/float(L); fs=ref[f]["h"][0]
    CT=max(13,int(round(fs*(0.72 if fs<64 else 0.5)*S)))
    if CT>200: CT=200
    need=len(rank)
    k=1
    while k<4 and (W*k)**2- W*W < need*CT*CT: k+=1
    T2=W*k
    newimg=bytearray(T2*T2)
    for y in range(H):
        d0=y*T2; newimg[d0:d0+W]=al[y*W:(y+1)*W]
    per=T2//CT
    cells=[(cx*CT,cy*CT) for cy in range(per) for cx in range(per) if (cy*CT)>=H]
    n=min(need,len(cells)); recs=[]
    adv=int(round(fs*0.9))
    for i in range(n):
        cx,cy=cells[i]
        w2,h2,px=render([rank[i]],FACE,int(CT*0.92),CT,CT,1)
        for y in range(CT):
            d0=(cy+y)*T2+cx
            newimg[d0:d0+CT]=px[y*w2:y*w2+CT]
        recs.append([ord(rank[i]),0,int(round(cx/S)),int(round(cy/S)),int(round(CT/S)),int(round(CT/S)),ref[f]["h"][3],adv,1,0])
    entries[idx[key]]=(key,make_dds(bytes(newimg),T2,T2))
    add[f]=recs; stats.append((f,fs,CT,k,n))
    print("  %-24s 字号%3d 贴图%dx%d(×%d) 格%3dpx 排入%5d"%(f,fs,T2,T2,k,CT,n))
SKIP={"ui/Win/CutsceneTest1.gbs","ui/Win/ThanksForPlaying.gbs"}
for e,(n,b) in enumerate(entries):
    if not n.endswith(".gbs") or n in SKIP: continue
    data=bytearray(b); dirty=False
    for bl in sorted(blocks(bytes(data)),key=lambda x:-x["tag"]):
        f=bl["name"]
        if f not in add: continue
        tbl=bl["noff"]+88; h=bl["h"]; oldn=h[5]
        recs_old=[list(struct.unpack_from("<10I",data,tbl+40*k)) for k in range(oldn)]
        have=set(r[0] for r in recs_old if 0<r[0]<0x110000)
        add2=[r for r in add[f] if r[0] not in have]
        if not add2: continue
        allg=sorted(recs_old+add2,key=lambda r:r[0])
        delta=40*len(add2); ins=tbl+40*oldn
        data[ins:ins]=b"\x00"*delta
        for off in (0x04,0x28,0x2C,0x30,0x34):
            v=struct.unpack_from("<I",data,off)[0]
            if v>ins: struct.pack_into("<I",data,off,v+delta)
        k=k if False else None
        mult=int(stats[[s[0] for s in stats].index(f)][3]) if f in [s[0] for s in stats] else 2
        hh=list(h); hh[1]=hh[2]=h[1]*mult; hh[5]=len(allg)
        struct.pack_into("<6I",data,bl["noff"]+64,*hh)
        struct.pack_into("<I",data,bl["tag"]+4,100+40*hh[5])
        for i2,r in enumerate(allg): struct.pack_into("<10I",data,tbl+40*i2,*r)
        dirty=True
    if dirty: entries[e]=(n,bytes(data))
os.makedirs(ROOT+r"\outputs\patch17",exist_ok=True)
open(ROOT+r"\outputs\patch17\ui-win.gfs","wb").write(G.build(entries))
open(ROOT+r"\outputs\patch17\core.gfs","wb").write(G.build([(n,bytes(d)) for n,d in G.iter_files(ROOT+r"\outputs\patch2\core.gfs")]))
print("built patch17")
