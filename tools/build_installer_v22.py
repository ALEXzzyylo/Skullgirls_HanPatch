import os,sys,struct,zlib,subprocess
ROOT=r"C:\Users\A.Aitherine\Documents\Codex\2026-10-10\s"
sys.path.insert(0,ROOT+r"\outputs")
import skullgirls_gfs as G
PATCH=ROOT+r"\outputs\patch17\ui-win.gfs"
print("patch17 ui-win.gfs = %.1f MB"%(os.path.getsize(PATCH)/1048576.0))
VAN=r"E:\SteamLibrary\steamapps\common\Skullgirls\_sg_chs_backup_v2\data01_ui-win.gfs"
OUT=ROOT+r"\outputs\installer"; END=0xE0F0E0F0
EXE_OFF=0x45C07D-0x401000+0x400
EXE_OLD=bytes([0x8A,0x85,0x6F,0xFE,0xFF,0xFF]); EXE_NEW=bytes([0xB0,0x01,0x90,0x90,0x90,0x90])
items=[]
for n,d in G.iter_files(ROOT+r"\outputs\patch2\core.gfs"):
    if n in ("core/localization/en_loc.json","core/localization/jp_loc.json"):
        items.append((1,"core.gfs",n,bytes(d)))
van={n:bytes(b) for n,b in G.iter_files(VAN)}
new={n:bytes(b) for n,b in G.iter_files(PATCH)}
added=[n for n in new if n not in van]; changed=[n for n in new if n in van and new[n]!=van[n]]
for n in sorted(added): items.append((1,"ui-win.gfs",n,new[n]))
for n in sorted(changed): items.append((1,"ui-win.gfs",n,new[n]))
items.append((2,"SkullGirls.exe","%d|%s"%(EXE_OFF,EXE_OLD.hex().upper()),EXE_NEW))
body=bytearray(struct.pack("<I",len(items))); raw=comp=0
for kind,dest,key,data in items:
    db=dest.encode(); kb=key.encode(); payload=data; c=0
    if len(data)>512:
        co=zlib.compressobj(9,zlib.DEFLATED,-15); z=co.compress(data)+co.flush()
        if len(z)<len(data)*0.97: payload,c=z,1
    raw+=len(data); comp+=len(payload)
    body+=struct.pack("<BHHBII",kind,len(db),len(kb),c,len(data),len(payload)); body+=db+kb+payload
body+=struct.pack("<I",END)
PAY=os.path.join(OUT,"payload_v17.bin"); open(PAY,"wb").write(body)
print("payload raw %.1f MB -> %.1f MB ; changed %d"%(raw/1048576.0,comp/1048576.0,len(changed)))
CSC=r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
EXE=os.path.join(OUT,"Skullgirls_CHS_Patch_v22.exe")
r=subprocess.run([CSC,"/nologo","/target:winexe","/platform:anycpu","/out:"+EXE,"/win32manifest:"+os.path.join(OUT,"app.manifest"),"/reference:System.Windows.Forms.dll","/reference:System.Drawing.dll",os.path.join(OUT,"Installer.cs")],capture_output=True,text=True)
if r.returncode!=0: print(r.stdout,r.stderr); sys.exit(1)
pb=open(PAY,"rb").read()
with open(EXE,"r+b") as f:
    f.seek(0,os.SEEK_END); off=f.tell(); f.write(pb); f.write(struct.pack("<QQ",off,len(pb))); f.write(b"SGPATCH1"+b"\x00"*8)
print("installer %.1f MB"%(os.path.getsize(EXE)/1048576.0))






