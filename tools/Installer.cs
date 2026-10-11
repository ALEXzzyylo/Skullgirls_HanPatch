// Skullgirls 汉化补丁 (based on the 2013 LMAO/ALI213 translation)
// 单文件安装程序：自动定位游戏目录 / 安装 / 卸载
using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Text;
using System.Windows.Forms;
using Microsoft.Win32;

static class Gfs
{
    public static void Dbg(string s)
    {
        try
        {
            File.AppendAllText(Path.Combine(Application.StartupPath, "sg_debug.txt"),
                               DateTime.Now.ToString("HH:mm:ss") + "  " + s + "\r\n", Encoding.UTF8);
        }
        catch { }
    }

    public class Entry
    {
        public string Name;
        public long Size;
        public long Offset;          // 在源文件中的偏移（-1 表示来自补丁数据）
        public byte[] Data;          // 补丁数据（Offset<0 时使用）
    }

    public static List<Entry> ReadIndex(string path, out uint dataOff, out byte[] magic, out byte[] version)
    {
        using (FileStream fs = File.OpenRead(path))
        {
            BinaryReader br = new BinaryReader(fs);
            dataOff = ReadU32BE(br);
            magic = ReadPStr(br);
            version = ReadPStr(br);
            ulong count = ReadU64BE(br);
            List<Entry> list = new List<Entry>();
            for (ulong i = 0; i < count; i++)
            {
                Entry e = new Entry();
                e.Name = Encoding.GetEncoding("ISO-8859-1").GetString(ReadPStr(br));
                e.Size = (long)ReadU64BE(br);
                ReadU32BE(br);                       // flags
                list.Add(e);
            }
            long off = dataOff;
            foreach (Entry e in list)
            {
                e.Offset = off;
                off += e.Size;
            }
            return list;
        }
    }

    static uint ReadU32BE(BinaryReader br)
    {
        byte[] b = br.ReadBytes(4);
        if (b.Length < 4) throw new Exception("GFS 文件损坏");
        return (uint)((b[0] << 24) | (b[1] << 16) | (b[2] << 8) | b[3]);
    }

    static ulong ReadU64BE(BinaryReader br)
    {
        ulong v = 0;
        for (int i = 0; i < 8; i++) v = (v << 8) | br.ReadByte();
        return v;
    }

    static byte[] ReadPStr(BinaryReader br)
    {
        ulong n = ReadU64BE(br);
        return br.ReadBytes((int)n);
    }

    static void WriteU32BE(Stream s, uint v)
    {
        s.WriteByte((byte)(v >> 24)); s.WriteByte((byte)(v >> 16));
        s.WriteByte((byte)(v >> 8)); s.WriteByte((byte)v);
    }

    static void WriteU64BE(Stream s, ulong v)
    {
        for (int i = 7; i >= 0; i--) s.WriteByte((byte)(v >> (8 * i)));
    }

    static void WritePStr(Stream s, byte[] b)
    {
        WriteU64BE(s, (ulong)b.Length);
        s.Write(b, 0, b.Length);
    }

    public static bool IsGfs(string path)
    {
        try
        {
            byte[] head = new byte[32];
            using (FileStream fs = File.OpenRead(path))
            {
                int got = fs.Read(head, 0, 32);
                Dbg("IsGfs " + path + " read=" + got + " head=" +
                    BitConverter.ToString(head, 0, Math.Max(0, Math.Min(32, got))));
                if (got < 32) return false;
                byte[] l = new byte[8];
                Array.Copy(head, 4, l, 0, 8);
                ulong n = 0;
                for (int i = 0; i < 8; i++) n = (n << 8) | l[i];
                Dbg("   magicLen=" + n);
                if (n != 20) return false;
                byte[] m = new byte[20];
                Array.Copy(head, 12, m, 0, 20);
                string s = Encoding.ASCII.GetString(m);
                Dbg("   magic=" + s);
                return s == "Reverge Package File";
            }
        }
        catch (Exception ex) { Dbg("IsGfs EX " + path + " : " + ex.Message); return false; }
    }

    /// <summary>把 repl 替换进 src，new 追加到末尾，输出到 dst。</summary>
    public static void Rewrite(string src, string dst,
                              Dictionary<string, byte[]> repl,
                              List<KeyValuePair<string, byte[]>> add)
    {
        uint dataOff; byte[] magic, version;
        List<Entry> list = ReadIndex(src, out dataOff, out magic, out version);

        List<Entry> outList = new List<Entry>();
        HashSet<string> present = new HashSet<string>();
        foreach (Entry e in list)
        {
            present.Add(e.Name);
            byte[] nd;
            if (repl.TryGetValue(e.Name, out nd))
            {
                Entry n = new Entry();
                n.Name = e.Name; n.Data = nd; n.Size = nd.Length; n.Offset = -1;
                outList.Add(n);
            }
            else outList.Add(e);
        }
        if (add != null)
            foreach (KeyValuePair<string, byte[]> kv in add)
            {
                if (present.Contains(kv.Key)) continue;
                Entry n = new Entry();
                n.Name = kv.Key; n.Data = kv.Value; n.Size = kv.Value.Length; n.Offset = -1;
                outList.Add(n);
            }

        // 先算出表长度，得到新的 dataOffset
        byte[][] nameBytes = new byte[outList.Count][];
        long tableLen = 0;
        for (int i = 0; i < outList.Count; i++)
        {
            nameBytes[i] = Encoding.GetEncoding("ISO-8859-1").GetBytes(outList[i].Name);
            tableLen += 8 + nameBytes[i].Length + 8 + 4;
        }
        long headLen = 4 + (8 + magic.Length) + (8 + version.Length) + 8;
        uint newDataOff = (uint)(headLen + tableLen);

        using (FileStream srcFs = File.OpenRead(src))
        using (FileStream dstFs = File.Create(dst))
        {
            WriteU32BE(dstFs, newDataOff);
            WritePStr(dstFs, magic);
            WritePStr(dstFs, version);
            WriteU64BE(dstFs, (ulong)outList.Count);
            for (int i = 0; i < outList.Count; i++)
            {
                WritePStr(dstFs, nameBytes[i]);
                WriteU64BE(dstFs, (ulong)outList[i].Size);
                WriteU32BE(dstFs, 1);
            }
            byte[] buf = new byte[1 << 20];
            foreach (Entry e in outList)
            {
                if (e.Offset >= 0)
                {
                    srcFs.Seek(e.Offset, SeekOrigin.Begin);
                    long left = e.Size;
                    while (left > 0)
                    {
                        int n = srcFs.Read(buf, 0, (int)Math.Min(buf.Length, left));
                        if (n <= 0) throw new Exception("读取源文件失败");
                        dstFs.Write(buf, 0, n);
                        left -= n;
                    }
                }
                else dstFs.Write(e.Data, 0, e.Data.Length);
            }
        }
    }
}

static class Patch
{
    public class Item
    {
        public byte Kind;            // 0 = 普通文件, 1 = gfs 内条目
        public string Dest;
        public string Key;
        public byte[] Data;
    }

    public static List<Item> LoadPayload(string exePath)
    {
        using (FileStream fs = File.OpenRead(exePath))
        {
            if (fs.Length < 32) throw new Exception("这不是补丁程序");
            fs.Seek(-32, SeekOrigin.End);
            BinaryReader br = new BinaryReader(fs);
            ulong off = br.ReadUInt64();
            ulong size = br.ReadUInt64();
            byte[] magic = br.ReadBytes(16);
            if (Encoding.ASCII.GetString(magic, 0, 8) != "SGPATCH1")
                throw new Exception("补丁数据未找到（文件可能被改动过）");
            fs.Seek((long)off, SeekOrigin.Begin);
            uint count = br.ReadUInt32();
            List<Item> list = new List<Item>();
            for (uint i = 0; i < count; i++)
            {
                Item it = new Item();
                it.Kind = br.ReadByte();
                int dl = br.ReadUInt16();
                int kl = br.ReadUInt16();
                byte comp = br.ReadByte();
                uint rawSize = br.ReadUInt32();
                uint dataSize = br.ReadUInt32();
                it.Dest = Encoding.UTF8.GetString(br.ReadBytes(dl));
                it.Key = Encoding.UTF8.GetString(br.ReadBytes(kl));
                byte[] data = br.ReadBytes((int)dataSize);
                if (comp == 1)
                {
                    using (MemoryStream ms = new MemoryStream(data))
                    using (DeflateStream ds = new DeflateStream(ms, CompressionMode.Decompress))
                    using (MemoryStream os = new MemoryStream())
                    {
                        byte[] tmp = new byte[1 << 20];
                        int n;
                        while ((n = ds.Read(tmp, 0, tmp.Length)) > 0) os.Write(tmp, 0, n);
                        data = os.ToArray();
                    }
                }
                if (rawSize != 0 && data.Length != rawSize) throw new Exception("补丁数据校验失败: " + it.Dest);
                it.Data = data;
                list.Add(it);
            }
            return list;
        }
    }

    public static string FindGameDir(string exeDir)
    {
        List<string> cand = new List<string>();
        cand.Add(exeDir);
        try
        {
            string steam = null;
            using (RegistryKey k = Registry.CurrentUser.OpenSubKey(@"Software\Valve\Steam"))
                if (k != null) steam = k.GetValue("SteamPath") as string;
            if (steam == null)
                using (RegistryKey k = Registry.LocalMachine.OpenSubKey(@"SOFTWARE\WOW6432Node\Valve\Steam"))
                    if (k != null) steam = k.GetValue("InstallPath") as string;
            if (steam != null)
            {
                List<string> libs = new List<string>();
                libs.Add(steam);
                string vdf = Path.Combine(steam, @"steamapps\libraryfolders.vdf");
                if (File.Exists(vdf))
                {
                    foreach (string line in File.ReadAllLines(vdf))
                    {
                        int i = line.IndexOf("\"path\"");
                        if (i >= 0)
                        {
                            int a = line.IndexOf('"', i + 6);
                            int b = line.IndexOf('"', a + 1);
                            if (a > 0 && b > a) libs.Add(line.Substring(a + 1, b - a - 1).Replace("\\\\", "\\"));
                        }
                    }
                }
                foreach (string l in libs)
                    cand.Add(Path.Combine(l, @"steamapps\common\Skullgirls"));
            }
        }
        catch { }
        foreach (string c in cand)
        {
            try
            {
                if (File.Exists(Path.Combine(c, "SkullGirls.exe")) &&
                    File.Exists(Path.Combine(c, @"data01\ui.gfs")))
                    return c;
            }
            catch { }
        }
        return null;
    }

    public static string BackupDir(string gameDir)
    {
        return Path.Combine(gameDir, "_sg_chs_backup_v2");
    }

    /// <summary>把即将被修改的文件原样备份一份（已存在则不覆盖）。</summary>
    public static void Backup(string gameDir, List<string> relFiles, Action<string> log)
    {
        string bk = BackupDir(gameDir);
        Directory.CreateDirectory(bk);
        foreach (string rel in relFiles)
        {
            string s = Path.Combine(gameDir, rel);
            if (!File.Exists(s)) continue;
            string d = Path.Combine(bk, rel.Replace('\\', '_'));
            if (File.Exists(d)) continue;
            log("备份 " + rel + " ...");
            File.Copy(s, d, false);
        }
    }

    static byte[] HexToBytes(string s)
    {
        s = s.Replace(" ", "");
        byte[] b = new byte[s.Length / 2];
        for (int i = 0; i < b.Length; i++)
            b[i] = Convert.ToByte(s.Substring(i * 2, 2), 16);
        return b;
    }

    static string BytesToHex(byte[] b, int n)
    {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n && i < b.Length; i++) sb.Append(b[i].ToString("X2"));
        return sb.ToString();
    }

    /// <summary>原地修改文件里的若干字节（用于绕过 exe 校验）。key = "偏移|期望字节HEX"</summary>
    static void PatchBytes(string path, string key, byte[] newBytes, Action<string> log)
    {
        string[] parts = key.Split('|');
        long off = Convert.ToInt64(parts[0]);
        byte[] expect = parts.Length > 1 && parts[1].Length > 0 ? HexToBytes(parts[1]) : null;
        byte[] data = File.ReadAllBytes(path);
        if (off + newBytes.Length > data.Length) throw new Exception("文件比预期小: " + path);
          bool same = true;
          for (int i = 0; i < newBytes.Length; i++) if (data[off + i] != newBytes[i]) { same = false; break; }
          if (same) { log("  " + Path.GetFileName(path) + " 已经是打过补丁的状态"); return; }
        if (expect != null)
        {
            for (int i = 0; i < expect.Length; i++)
                if (data[off + i] != expect[i])
                    throw new Exception("文件内容与预期不符（可能版本变了）: " + Path.GetFileName(path));
        }
        Array.Copy(newBytes, 0, data, off, newBytes.Length);
        File.WriteAllBytes(path, data);
        log("  已修改 " + Path.GetFileName(path) + " @" + off + " -> " + BytesToHex(newBytes, newBytes.Length));
    }

    public static void Install(string gameDir, List<Item> items, Action<string> log)
    {
        List<string> touched = new List<string>();
        foreach (Item it in items)
        {
            if (it.Dest == null || it.Dest.Length == 0) continue;
            string rel = it.Kind == 0 ? it.Dest : Path.Combine("data01", it.Dest);
            if (it.Kind == 2) rel = it.Dest;
            if (!touched.Contains(rel)) touched.Add(rel);
        }
        Backup(gameDir, touched, log);
        Dictionary<string, Dictionary<string, byte[]>> repl =
            new Dictionary<string, Dictionary<string, byte[]>>();
        Dictionary<string, List<KeyValuePair<string, byte[]>>> add =
            new Dictionary<string, List<KeyValuePair<string, byte[]>>>();
        List<Item> plain = new List<Item>();
        List<Item> binpatch = new List<Item>();
        foreach (Item it in items)
        {
            if (it.Kind == 2) { binpatch.Add(it); continue; }
            if (it.Kind == 0) { plain.Add(it); continue; }
            if (!repl.ContainsKey(it.Dest))
            {
                repl[it.Dest] = new Dictionary<string, byte[]>();
                add[it.Dest] = new List<KeyValuePair<string, byte[]>>();
            }
            if (it.Key != null && it.Key.Length > 0 && IsAdded(it.Dest, gameDir, it.Key))
                add[it.Dest].Add(new KeyValuePair<string, byte[]>(it.Key, it.Data));
            else
                repl[it.Dest][it.Key] = it.Data;
        }
        foreach (KeyValuePair<string, Dictionary<string, byte[]>> kv in repl)
        {
            string src = Path.Combine(gameDir, "data01", kv.Key);
            if (!File.Exists(src)) { log("跳过（没找到）: " + kv.Key); continue; }
            if (!Gfs.IsGfs(src)) { log("跳过（不是合法 GFS）: " + kv.Key); continue; }
            string tmp = src + ".sg_tmp";
            log("写入 " + kv.Key + " ...");
            Gfs.Rewrite(src, tmp, kv.Value, add[kv.Key]);
            File.Delete(src);
            File.Move(tmp, src);
        }
        foreach (Item it in plain)
        {
            string dst = Path.Combine(gameDir, it.Dest);
            if (File.Exists(dst))
            {
                log("写入 " + it.Dest + " ...");
                File.WriteAllBytes(dst, it.Data);
            }
        }
        foreach (Item it in binpatch)
        {
            string dst = Path.Combine(gameDir, it.Dest);
            if (!File.Exists(dst)) { log("跳过（没找到）: " + it.Dest); continue; }
            log("修补 " + it.Dest + " ...");
            PatchBytes(dst, it.Key, it.Data, log);
        }
    }

    static Dictionary<string, HashSet<string>> _names = new Dictionary<string, HashSet<string>>();

    static bool IsAdded(string gfs, string gameDir, string key)
    {
        string src = Path.Combine(gameDir, "data01", gfs);
        if (!_names.ContainsKey(src))
        {
            HashSet<string> set = new HashSet<string>();
            try
            {
                uint d; byte[] m, v;
                foreach (Gfs.Entry e in Gfs.ReadIndex(src, out d, out m, out v)) set.Add(e.Name);
            }
            catch { }
            _names[src] = set;
        }
        return !_names[src].Contains(key);
    }

    public static void Uninstall(string gameDir, Action<string> log)
    {
        string bk = BackupDir(gameDir);
        if (!Directory.Exists(bk)) throw new Exception("没有找到备份，无法卸载（可能没装过）");
        string[][] map = new string[][] {
            new string[] { "SkullGirls.exe", "SkullGirls.exe" },
            new string[] { "LOCALE.txt",    "LOCALE.txt" },
            new string[] { "core.gfs",      @"data01\core.gfs" },
            new string[] { "ui.gfs",        @"data01\ui.gfs" },
            new string[] { "ui-win.gfs",    @"data01\ui-win.gfs" },
            new string[] { "dev.gfs",       @"data01\dev.gfs" },
        };
        foreach (string[] m in map)
        {
            string s = Path.Combine(bk, m[0]);
            if (!File.Exists(s)) s = Path.Combine(bk, m[1].Replace('\\', '_'));
            if (!File.Exists(s)) continue;
            string dst = Path.Combine(gameDir, m[1]);
            if (!File.Exists(dst)) continue;
            log("还原 " + m[1] + " ...");
            File.Copy(s, dst, true);
        }
    }
}

public class MainForm : Form
{
    TextBox box;
    Label status;
    string gameDir;
    List<Patch.Item> items;

    public MainForm()
    {
        Text = "骷髅女孩 (Skullgirls) 汉化补丁";
        ClientSize = new Size(560, 392);
        FormBorderStyle = FormBorderStyle.FixedSingle;
        MaximizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;

        Label title = new Label();
        title.Text = "骷髅女孩 (Skullgirls) 汉化补丁";
        title.Font = new Font("Microsoft YaHei UI", 12F, FontStyle.Bold);
        title.SetBounds(16, 12, 520, 26);
        Controls.Add(title);

        Label sub = new Label();
        sub.Text = "基于 2013 年游侠 LMAO 汉化组的译文与字库重制 · 适配当前 Steam 版本";
        sub.SetBounds(16, 42, 530, 18);
        Controls.Add(sub);

        Label path = new Label();
        path.Name = "pathLabel";
        path.SetBounds(16, 66, 530, 18);
        path.ForeColor = Color.DimGray;
        Controls.Add(path);

        Button bInstall = new Button();
        bInstall.Text = "安装汉化(&I)";
        bInstall.SetBounds(16, 92, 170, 34);
        bInstall.Click += delegate { Run(true); };
        Controls.Add(bInstall);

        Button bUninstall = new Button();
        bUninstall.Text = "卸载汉化(&U)";
        bUninstall.SetBounds(196, 92, 170, 34);
        bUninstall.Click += delegate { Run(false); };
        Controls.Add(bUninstall);

        Button bExit = new Button();
        bExit.Text = "退出程序(&X)";
        bExit.SetBounds(376, 92, 170, 34);
        bExit.Click += delegate { Close(); };
        Controls.Add(bExit);

        Button bPath = new Button();
        bPath.Text = "选择游戏目录(&P)…";
        bPath.SetBounds(16, 132, 170, 30);
        bPath.Click += delegate
        {
            FolderBrowserDialog d = new FolderBrowserDialog();
            d.Description = "请选择 Skullgirls 游戏目录（里面能看到 SkullGirls.exe 和 data01 文件夹）";
            if (gameDir != null) d.SelectedPath = gameDir;
            if (d.ShowDialog() != DialogResult.OK) return;
            gameDir = d.SelectedPath;
            Control[] c = Controls.Find("pathLabel", true);
            if (c.Length > 0) c[0].Text = "游戏目录：" + gameDir;
            Log("已选择游戏目录：" + gameDir);
        };
        Controls.Add(bPath);

        Button bOpen = new Button();
        bOpen.Text = "打开游戏目录(&O)";
        bOpen.SetBounds(196, 132, 170, 30);
        bOpen.Click += delegate
        {
            try { if (gameDir != null) System.Diagnostics.Process.Start(gameDir); }
            catch { }
        };
        Controls.Add(bOpen);

        box = new TextBox();
        box.Multiline = true;
        box.ScrollBars = ScrollBars.Vertical;
        box.ReadOnly = true;
        box.SetBounds(16, 172, 530, 204);
        box.BackColor = Color.White;
        Controls.Add(box);

        status = new Label();
        status.Name = "statusLabel";
        status.SetBounds(16, 66, 530, 18);
        Controls.Add(status);

        Load += delegate
        {
            gameDir = Patch.FindGameDir(Application.StartupPath);
            Control[] c = Controls.Find("pathLabel", true);
            if (gameDir != null)
            {
                c[0].Text = "游戏目录：" + gameDir;
                Log("已找到游戏目录。");
            }
            else
            {
                c[0].Text = "没有自动找到游戏目录，点「安装汉化」后手动选择。";
                Log("没找到游戏目录（可点安装后手动选择 Skullgirls 文件夹）。");
            }
            try { items = Patch.LoadPayload(Application.ExecutablePath); Log("补丁数据载入完成。"); }
            catch (Exception ex) { Log("补丁数据载入失败: " + ex.Message); }
        };
    }

    void Log(string s)
    {
        box.AppendText(s + "\r\n");
        Application.DoEvents();
    }

    void Run(bool install)
    {
        if (items == null) { MessageBox.Show("补丁数据未载入。", "错误"); return; }
        if (gameDir == null)
        {
            FolderBrowserDialog d = new FolderBrowserDialog();
            d.Description = "请选择 Skullgirls 游戏目录（里面能看到 SkullGirls.exe 和 data01 文件夹）";
            if (d.ShowDialog() != DialogResult.OK) return;
            gameDir = d.SelectedPath;
        }
        try
        {
            if (install)
            {
                Log("=== 开始安装 ===");
                Patch.Install(gameDir, items, Log);
                Log("=== 完成！进游戏即可（语言若不是英文，去 选项→语言 切成 English）===");
                MessageBox.Show("汉化安装完成！\n\n如果游戏里还是日文/英文，请到 选项 → 语言 里切换成 English。",
                                "完成", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            else
            {
                Log("=== 开始卸载 ===");
                Patch.Uninstall(gameDir, Log);
                Log("=== 已还原为原版 ===");
                MessageBox.Show("已还原为原版。", "完成", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
        }
        catch (Exception ex)
        {
            Log("出错: " + ex.Message);
            MessageBox.Show("出错：" + ex.Message, "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}

static class Program
{
    static void SilentLog(string s)
    {
        string p = Path.Combine(Application.StartupPath, "skullgirls_patch_log.txt");
        File.AppendAllText(p, s + "\r\n", Encoding.UTF8);
    }

    [STAThread]
    static void Main(string[] args)
    {
        // 静默模式： Skullgirls_CHS_Patch.exe /install [游戏目录]  或  /uninstall [游戏目录]
        if (args.Length > 0 && (args[0].Equals("/install", StringComparison.OrdinalIgnoreCase) ||
                                args[0].Equals("/uninstall", StringComparison.OrdinalIgnoreCase)))
        {
            bool install = args[0].Equals("/install", StringComparison.OrdinalIgnoreCase);
            string logPath = Path.Combine(Application.StartupPath, "skullgirls_patch_log.txt");
            try { File.Delete(logPath); } catch { }
            try
            {
                string dir = args.Length > 1 ? args[1] : Patch.FindGameDir(Application.StartupPath);
                if (dir == null) { SilentLog("找不到游戏目录"); return; }
                List<Patch.Item> items = Patch.LoadPayload(Application.ExecutablePath);
                SilentLog("game dir: " + dir);
                if (install) Patch.Install(dir, items, SilentLog);
                else Patch.Uninstall(dir, SilentLog);
                SilentLog("OK");
            }
            catch (Exception ex) { SilentLog("ERROR: " + ex.Message); }
            return;
        }

        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new MainForm());
    }
}
