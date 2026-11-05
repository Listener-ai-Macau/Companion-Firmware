using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Text;
using System.Windows.Forms;

public class CompanionAcceptDialog : Form
{
    private TextBox noteBox;
    private string outPath;
    private string selected;

    public CompanionAcceptDialog(Dictionary<string, string> cfg)
    {
        string title = cfg["title"];
        string progress = cfg["progress"];
        string scope = cfg["scope"];
        string message = cfg["message"];
        string expected = cfg["expected"];
        outPath = cfg["output_path"];
        selected = null;

        this.Text = string.IsNullOrEmpty(progress) ? title : (title + " " + progress);
        this.StartPosition = FormStartPosition.CenterScreen;
        // Do not steal focus from other work; taskbar + sound is enough.
        this.TopMost = false;
        this.FormBorderStyle = FormBorderStyle.FixedDialog;
        this.MaximizeBox = false;
        this.MinimizeBox = false;
        this.ClientSize = new Size(720, 420);
        this.Font = new Font("Microsoft YaHei UI", 10f);
        this.ShowInTaskbar = true;

        Label lblTitle = new Label();
        lblTitle.Font = new Font("Microsoft YaHei UI", 12f, FontStyle.Bold);
        lblTitle.SetBounds(16, 10, 688, 26);
        lblTitle.Text = string.IsNullOrEmpty(progress) ? title : (progress + "  " + title);
        this.Controls.Add(lblTitle);

        Label lblScope = new Label();
        lblScope.SetBounds(16, 42, 688, 20);
        lblScope.Text = "你现在做 - " + scope;
        this.Controls.Add(lblScope);

        TextBox msg = new TextBox();
        msg.Multiline = true;
        msg.ReadOnly = true;
        msg.ScrollBars = ScrollBars.Vertical;
        msg.SetBounds(16, 64, 688, 72);
        msg.Text = message;
        this.Controls.Add(msg);

        Label lblExp = new Label();
        lblExp.SetBounds(16, 144, 688, 20);
        lblExp.Text = "通过标准";
        this.Controls.Add(lblExp);

        TextBox exp = new TextBox();
        exp.Multiline = true;
        exp.ReadOnly = true;
        exp.ScrollBars = ScrollBars.Vertical;
        exp.SetBounds(16, 166, 688, 62);
        exp.Text = expected;
        this.Controls.Add(exp);

        Label lblNote = new Label();
        lblNote.SetBounds(16, 236, 688, 20);
        lblNote.Text = "备注（可留空；有异常、疑问或小瑕疵就写下来，我会当作需求处理）";
        this.Controls.Add(lblNote);

        noteBox = new TextBox();
        noteBox.Multiline = true;
        noteBox.ScrollBars = ScrollBars.Vertical;
        noteBox.AcceptsReturn = true;
        noteBox.SetBounds(16, 258, 688, 90);
        this.Controls.Add(noteBox);

        FlowLayoutPanel panel = new FlowLayoutPanel();
        panel.FlowDirection = FlowDirection.RightToLeft;
        panel.WrapContents = false;
        panel.SetBounds(16, 360, 688, 40);
        this.Controls.Add(panel);

        string[] names = new string[] { "通过", "失败", "跳过", "中止" };
        for (int i = 0; i < names.Length; i++)
        {
            Button b = new Button();
            b.Text = names[i];
            b.Width = 86;
            b.Height = 28;
            b.Margin = new Padding(4, 3, 4, 3);
            b.Tag = names[i];
            b.Click += new EventHandler(this.OnButtonClick);
            panel.Controls.Add(b);
        }

        this.FormClosing += new FormClosingEventHandler(this.OnFormClosing);
        this.Shown += new EventHandler(this.OnShown);
    }

    private void OnShown(object sender, EventArgs e)
    {
        // Sound cue only — do not force TopMost / steal focus from other apps.
        try
        {
            string wav = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Media", "notify.wav");
            if (File.Exists(wav))
            {
                using (var player = new System.Media.SoundPlayer(wav))
                {
                    player.Play();
                }
            }
            else
            {
                System.Media.SystemSounds.Exclamation.Play();
            }
        }
        catch
        {
            try { System.Media.SystemSounds.Exclamation.Play(); } catch { }
        }
        noteBox.Focus();
    }

    private void OnFormClosing(object sender, FormClosingEventArgs e)
    {
        if (selected == null)
        {
            Save("关闭");
        }
    }

    private void OnButtonClick(object sender, EventArgs e)
    {
        Button b = (Button)sender;
        Save(Convert.ToString(b.Tag));
        this.Close();
    }

    private void Save(string sel)
    {
        selected = sel;
        string dir = Path.GetDirectoryName(outPath);
        if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
        {
            Directory.CreateDirectory(dir);
        }
        StringBuilder sb = new StringBuilder();
        sb.Append("{\n");
        sb.Append("  \"selected\": \"").Append(Esc(sel)).Append("\",\n");
        sb.Append("  \"text\": \"").Append(Esc(noteBox.Text)).Append("\",\n");
        sb.Append("  \"at\": \"").Append(DateTime.UtcNow.ToString("o")).Append("\",\n");
        sb.Append("  \"output_path\": \"").Append(Esc(outPath)).Append("\"\n");
        sb.Append("}\n");
        File.WriteAllText(outPath, sb.ToString(), new UTF8Encoding(false));
    }

    private static string Esc(string x)
    {
        if (x == null) return "";
        return x.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "\\r").Replace("\n", "\\n");
    }

    [STAThread]
    public static void Main(string[] args)
    {
        if (args.Length < 1)
        {
            MessageBox.Show("need config json path");
            return;
        }
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        string json = File.ReadAllText(args[0], Encoding.UTF8);
        Dictionary<string, string> cfg = new Dictionary<string, string>();
        string[] keys = new string[] { "title", "progress", "scope", "message", "expected", "output_path" };
        for (int i = 0; i < keys.Length; i++)
        {
            cfg[keys[i]] = Extract(json, keys[i]);
        }
        Application.Run(new CompanionAcceptDialog(cfg));
    }

    private static string Extract(string json, string key)
    {
        string pat = "\"" + key + "\"";
        int i = json.IndexOf(pat);
        if (i < 0) return "";
        int colon = json.IndexOf(':', i);
        int q1 = json.IndexOf('"', colon + 1);
        if (q1 < 0) return "";
        StringBuilder sb = new StringBuilder();
        for (int p = q1 + 1; p < json.Length; p++)
        {
            char c = json[p];
            if (c == '\\' && p + 1 < json.Length)
            {
                p++;
                char n = json[p];
                if (n == 'n') sb.Append('\n');
                else if (n == 'r') sb.Append('\r');
                else if (n == 't') sb.Append('\t');
                else sb.Append(n);
            }
            else if (c == '"') break;
            else sb.Append(c);
        }
        return sb.ToString();
    }
}
