using System.Net.Http.Headers;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

static class Program
{
    static readonly System.Text.Json.JsonSerializerOptions Pretty = new() { WriteIndented = true };

    static JsonObject ReadObject(string path)
    {
        if (new FileInfo(path).Length > 65536) throw new ArgumentException("JSON file exceeds 64 KiB");
        return JsonNode.Parse(File.ReadAllText(path, Encoding.UTF8)) as JsonObject
            ?? throw new ArgumentException("Expected a JSON object");
    }

    static string Text(JsonNode? node) => node?.GetValue<string>() ?? throw new ArgumentException("Missing field");

    static async Task<int> Main(string[] arguments)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        try
        {
            bool execute = arguments.Contains("--execute"), dllMode = arguments.Contains("--dll");
            var args = arguments.Where(a => a != "--execute" && a != "--dll").ToArray();
            if (args.Length < 1 || args.Length > 3) throw new ArgumentException("Usage: demo PRODUCT [COMMAND [VALUE]] [--execute] [--dll]");
            string product = args[0], command = args.Length > 1 ? args[1] : "query", value = args.Length > 2 ? args[2] : "";
            if (product != "tdx" && product != "ths") throw new ArgumentException("PRODUCT must be tdx or ths");
            var profile = (JsonObject)ReadObject("config/api-contract.json")[product]!;
            JsonObject spec;
            if (command == "query")
            {
                string category = value == "" ? "funds" : value;
                string path = Text(profile["queries"]?[category]);
                spec = new JsonObject { ["method"] = "GET", ["path"] = path, ["input"] = "none", ["live"] = false };
            }
            else spec = (JsonObject)(profile["commands"]?[command]?.DeepClone() ?? throw new ArgumentException("Unsupported command"));
            string method = Text(spec["method"]), endpoint = Text(spec["path"]), input = Text(spec["input"]);
            JsonObject? body = null;
            if (input == "file") body = ReadObject(value);
            else if (input.StartsWith("id-"))
            {
                if (!Regex.IsMatch(value, "^[A-Za-z0-9_-]{1,128}$")) throw new ArgumentException("Pass an existing action/preview ID");
                if (input == "id-path") endpoint += value;
                else body = new JsonObject { ["preview_id"] = value };
            }
            else if (value != "" && command != "query") throw new ArgumentException("This command takes no VALUE");
            if (spec["live"]!.GetValue<bool>() && !execute)
            {
                Console.WriteLine(new JsonObject { ["dry_run"] = true, ["method"] = method, ["path"] = endpoint,
                    ["body"] = body, ["note"] = "Nothing sent. --execute submits ONE REAL action." }.ToJsonString(Pretty));
                return 0;
            }
            string url = (Environment.GetEnvironmentVariable(Text(profile["url_env"])) ?? Text(profile["base_url"])).TrimEnd('/');
            var uri = new Uri(url);
            if (!Regex.IsMatch(url, "^http://127\\.0\\.0\\.1:[0-9]{1,5}$") || uri.Port <= 0 ||
                uri.UserInfo != "" || uri.Query != "" || uri.Fragment != "" || uri.AbsolutePath != "/")
                throw new ArgumentException("URL must be http://127.0.0.1:<nondefault port>");
            string token = (Environment.GetEnvironmentVariable(Text(profile["token_env"])) ?? "").Trim();
            if (endpoint != "/health" && !Regex.IsMatch(token, "^[A-Za-z0-9_-]{32,256}$"))
                throw new ArgumentException("Set " + Text(profile["token_env"]));
            int status; string raw;
            if (dllMode) (status, raw) = DllConsumer.Call(product, url, token, method, endpoint, body?.ToJsonString());
            else
            {
                using var handler = new HttpClientHandler { AllowAutoRedirect = false, UseProxy = false };
                using var client = new HttpClient(handler) { Timeout = TimeSpan.FromSeconds(90), MaxResponseContentBufferSize = 16 * 1024 * 1024 };
                using var request = new HttpRequestMessage(new HttpMethod(method), url + endpoint);
                if (token != "") request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
                if (body != null) request.Content = new StringContent(body.ToJsonString(), Encoding.UTF8, "application/json");
                using var response = await client.SendAsync(request);
                status = (int)response.StatusCode;
                raw = await response.Content.ReadAsStringAsync();
            }
            var result = JsonNode.Parse(raw) as JsonObject ?? throw new ArgumentException("Response is not a JSON object");
            Console.WriteLine("HTTP " + status);
            Console.WriteLine(result.ToJsonString(Pretty));
            return status == 200 && result["ok"]?.GetValue<bool>() != false ? 0 : 1;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine(error.Message + "\nNo automatic retry. Reconcile any submitted action in the official client.");
            return 1;
        }
    }
}

static class DllConsumer
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int Initialize(byte[] url, byte[] token);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int ApiCall(byte[] method, byte[] path, byte[]? json, [Out] byte[] output, uint capacity, out uint required);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int Cached([Out] byte[] output, uint capacity, out uint required);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate uint HttpStatus();
    static byte[] Utf8(string text) => Encoding.UTF8.GetBytes(text + "\0");

    public static (int, string) Call(string product, string url, string token, string method, string path, string? json)
    {
        if (!OperatingSystem.IsWindows()) throw new PlatformNotSupportedException("DLL mode requires Windows");
        string home = Environment.GetEnvironmentVariable("TRADEAPI_" + product.ToUpperInvariant() + "_HOME")
            ?? throw new ArgumentException("Set the product HOME environment variable");
        string arch = Environment.Is64BitProcess ? "x64" : "x86";
        nint library = NativeLibrary.Load(Path.GetFullPath(Path.Combine(home, "build", arch, "tradeapi_" + product + ".dll")));
        try
        {
            var init = Marshal.GetDelegateForFunctionPointer<Initialize>(NativeLibrary.GetExport(library, "TradeApi_Initialize"));
            var call = Marshal.GetDelegateForFunctionPointer<ApiCall>(NativeLibrary.GetExport(library, "TradeApi_Call"));
            var cached = Marshal.GetDelegateForFunctionPointer<Cached>(NativeLibrary.GetExport(library, "TradeApi_GetLastResponse"));
            var status = Marshal.GetDelegateForFunctionPointer<HttpStatus>(NativeLibrary.GetExport(library, "TradeApi_GetLastHttpStatus"));
            if (init(Utf8(url), Utf8(token)) != 0) throw new ArgumentException("DLL initialization failed");
            byte[] output = new byte[65536];
            int code = call(Utf8(method), Utf8(path), json == null ? null : Utf8(json), output, (uint)output.Length, out uint required);
            if (code == 3)
            {
                if (required == 0 || required > 16 * 1024 * 1024 + 1) throw new ArgumentException("Invalid DLL size");
                output = new byte[required];
                code = cached(output, (uint)output.Length, out required); // Same thread; no new request.
            }
            if (code != 0 && code != 4) throw new ArgumentException("DLL code=" + code + "; do not resubmit");
            int nul = Array.IndexOf(output, (byte)0);
            if (nul < 0) throw new ArgumentException("DLL output has no terminator");
            return ((int)status(), Encoding.UTF8.GetString(output, 0, nul));
        }
        finally { NativeLibrary.Free(library); }
    }
}
