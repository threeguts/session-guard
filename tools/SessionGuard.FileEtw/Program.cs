using System.Globalization;
using System.Reflection;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Diagnostics.Tracing;
using Microsoft.Diagnostics.Tracing.Parsers.Kernel;
using Microsoft.Diagnostics.Tracing.Session;

internal sealed class Options
{
    public string SessionName { get; set; } = "SessionGuardFileEtw";
    public double TtlSeconds { get; set; } = 120;
    public List<string> BrowserRoots { get; } = [];
    public List<string> BrowserRootTails { get; } = [];
    public List<Regex> SensitivePathMatchers { get; } = [];
}

internal sealed class InterestingFile
{
    public InterestingFile(string path, DateTime nowUtc)
    {
        Path = path;
        FirstSeenUtc = nowUtc;
        LastSeenUtc = nowUtc;
    }

    public string Path { get; }
    public DateTime FirstSeenUtc { get; }
    public DateTime LastSeenUtc { get; set; }
}

internal static class Program
{
    private const string ProviderName = "Microsoft-Windows-Kernel-File";
    private static readonly Dictionary<string, InterestingFile> InterestingFiles = new(StringComparer.OrdinalIgnoreCase);
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = false,
    };

    private static Options ActiveOptions = new();

    private static int Main(string[] args)
    {
        ActiveOptions = ParseOptions(args);
        if (ActiveOptions.BrowserRoots.Count == 0)
        {
            Console.Error.WriteLine("At least one --browser-root argument is required.");
            return 2;
        }

        if (!(TraceEventSession.IsElevated() ?? false))
        {
            Console.Error.WriteLine("TraceEvent file helper must run from an elevated terminal.");
            return 5;
        }

        using var session = new TraceEventSession(ActiveOptions.SessionName);
        var stopped = 0;

        void RequestStop()
        {
            if (Interlocked.Exchange(ref stopped, 1) == 0)
            {
                session.Stop();
            }
        }

        Console.CancelKeyPress += (_, eventArgs) =>
        {
            eventArgs.Cancel = true;
            RequestStop();
        };

        StartStdinStopThread(RequestStop);
        Subscribe(session.Source.Kernel);

        var keywords =
            KernelTraceEventParser.Keywords.FileIOInit |
            KernelTraceEventParser.Keywords.FileIO;

        session.EnableKernelProvider(keywords);
        Console.Error.WriteLine(
            $"TraceEvent file helper started: session={ActiveOptions.SessionName}, roots={ActiveOptions.BrowserRoots.Count}");
        session.Source.Process();
        Console.Error.WriteLine("TraceEvent file helper stopped.");
        return 0;
    }

    private static void Subscribe(KernelTraceEventParser kernel)
    {
        kernel.FileIOCreate += data => HandlePathEvent("create", 12, data, emit: true);
        kernel.FileIOFileCreate += data => HandlePathEvent("create", 10, data, emit: false);
        kernel.FileIORead += data => HandleReadWriteEvent("read", 15, data);
        kernel.FileIOWrite += data => HandleReadWriteEvent("write", 16, data);
    }

    private static void HandlePathEvent(string eventName, int eventId, TraceEvent data, bool emit)
    {
        var path = GetPath(data);
        if (!IsSensitiveBrowserPath(path))
        {
            return;
        }

        var nowUtc = DateTime.UtcNow;
        PruneInterestingFiles(nowUtc);
        var identities = GetFileIdentities(data, data.ProcessID);

        foreach (var identity in identities)
        {
            InterestingFiles[identity] = new InterestingFile(path!, nowUtc);
        }

        if (emit)
        {
            EmitFileEvent(eventName, eventId, data, path!, identities.FirstOrDefault());
        }
    }

    private static void HandleReadWriteEvent(string eventName, int eventId, TraceEvent data)
    {
        var nowUtc = DateTime.UtcNow;
        PruneInterestingFiles(nowUtc);
        var identities = GetFileIdentities(data, data.ProcessID);
        var path = GetPath(data);
        var matchedIdentity = identities.FirstOrDefault(identity =>
        {
            if (!InterestingFiles.TryGetValue(identity, out var fileInfo))
            {
                return false;
            }

            fileInfo.LastSeenUtc = nowUtc;
            path ??= fileInfo.Path;
            return true;
        });

        if (matchedIdentity is null)
        {
            if (!IsSensitiveBrowserPath(path))
            {
                return;
            }

            matchedIdentity = identities.FirstOrDefault();
            if (matchedIdentity is not null && path is not null)
            {
                InterestingFiles[matchedIdentity] = new InterestingFile(path, nowUtc);
            }
        }

        if (path is null)
        {
            return;
        }

        EmitFileEvent(eventName, eventId, data, path, matchedIdentity);
    }

    private static void EmitFileEvent(
        string eventName,
        int eventId,
        TraceEvent data,
        string path,
        string? fileObject)
    {
        var row = new Dictionary<string, object?>
        {
            ["provider"] = ProviderName,
            ["event"] = eventName,
            ["event_id"] = eventId,
            ["time"] = data.TimeStamp.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
            ["pid"] = data.ProcessID,
            ["path"] = path,
            ["file_object"] = fileObject,
        };

        Console.Out.WriteLine(JsonSerializer.Serialize(row, JsonOptions));
        Console.Out.Flush();
    }

    private static void StartStdinStopThread(Action requestStop)
    {
        var thread = new Thread(() =>
        {
            try
            {
                while (Console.In.ReadLine() is not null)
                {
                    requestStop();
                    break;
                }

                requestStop();
            }
            catch (IOException)
            {
                requestStop();
            }
            catch (ObjectDisposedException)
            {
                requestStop();
            }
        })
        {
            IsBackground = true,
            Name = "SessionGuardFileEtwStdinStop",
        };
        thread.Start();
    }

    private static Options ParseOptions(string[] args)
    {
        var options = new Options();
        for (var index = 0; index < args.Length; index++)
        {
            var argument = args[index];
            if (argument == "--browser-root" && TryReadValue(args, ref index, out var browserRoot))
            {
                AddBrowserRoot(options, browserRoot);
            }
            else if (argument == "--sensitive-path" && TryReadValue(args, ref index, out var sensitivePath))
            {
                AddSensitivePath(options, sensitivePath);
            }
            else if (argument == "--session-name" && TryReadValue(args, ref index, out var sessionName))
            {
                options.SessionName = sessionName;
            }
            else if (argument == "--ttl-seconds" && TryReadValue(args, ref index, out var ttlSeconds))
            {
                if (double.TryParse(ttlSeconds, NumberStyles.Float, CultureInfo.InvariantCulture, out var parsedTtl)
                    && parsedTtl > 0)
                {
                    options.TtlSeconds = parsedTtl;
                }
            }
        }

        return options;
    }

    private static bool TryReadValue(string[] args, ref int index, out string value)
    {
        if (index + 1 >= args.Length)
        {
            value = string.Empty;
            return false;
        }

        index++;
        value = args[index];
        return true;
    }

    private static void AddBrowserRoot(Options options, string browserRoot)
    {
        var normalizedRoot = NormalizePath(Environment.ExpandEnvironmentVariables(browserRoot));
        if (string.IsNullOrEmpty(normalizedRoot))
        {
            return;
        }

        options.BrowserRoots.Add(normalizedRoot);
        var rootTail = GetRootTail(normalizedRoot);
        if (!string.IsNullOrEmpty(rootTail))
        {
            options.BrowserRootTails.Add(rootTail);
        }
    }

    private static void AddSensitivePath(Options options, string sensitivePath)
    {
        var normalizedPath = NormalizePath(Environment.ExpandEnvironmentVariables(sensitivePath)).TrimStart('\\');
        if (string.IsNullOrEmpty(normalizedPath))
        {
            return;
        }

        options.SensitivePathMatchers.Add(WildcardToRegex(@"*\" + normalizedPath));
        options.SensitivePathMatchers.Add(WildcardToRegex(@"*\" + normalizedPath + @"\*"));
    }

    private static bool IsSensitiveBrowserPath(string? path)
    {
        if (!IsInsideBrowserRoot(path))
        {
            return false;
        }

        if (ActiveOptions.SensitivePathMatchers.Count == 0)
        {
            return true;
        }

        var normalizedPath = NormalizePath(path);
        return ActiveOptions.SensitivePathMatchers.Any(matcher => matcher.IsMatch(normalizedPath));
    }

    private static bool IsInsideBrowserRoot(string? path)
    {
        var normalizedPath = NormalizePath(path);
        if (string.IsNullOrEmpty(normalizedPath))
        {
            return false;
        }

        foreach (var browserRoot in ActiveOptions.BrowserRoots)
        {
            if (normalizedPath == browserRoot || normalizedPath.StartsWith(browserRoot + @"\", StringComparison.Ordinal))
            {
                return true;
            }
        }

        foreach (var rootTail in ActiveOptions.BrowserRootTails)
        {
            if (normalizedPath.EndsWith(rootTail, StringComparison.Ordinal)
                || normalizedPath.Contains(@"\" + rootTail + @"\", StringComparison.Ordinal))
            {
                return true;
            }
        }

        return false;
    }

    private static string GetRootTail(string normalizedRoot)
    {
        var colonIndex = normalizedRoot.IndexOf(':');
        if (colonIndex >= 0 && colonIndex + 1 < normalizedRoot.Length)
        {
            return normalizedRoot[(colonIndex + 1)..].TrimStart('\\');
        }

        return normalizedRoot.TrimStart('\\');
    }

    private static string NormalizePath(string? path)
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            return string.Empty;
        }

        return path.Replace('/', '\\').TrimEnd('\\').ToLowerInvariant();
    }

    private static Regex WildcardToRegex(string pattern)
    {
        var regexPattern = "^" + Regex.Escape(pattern)
            .Replace(@"\*", ".*", StringComparison.Ordinal)
            .Replace(@"\?", ".", StringComparison.Ordinal) + "$";
        return new Regex(regexPattern, RegexOptions.IgnoreCase | RegexOptions.CultureInvariant | RegexOptions.Compiled);
    }

    private static string? GetPath(TraceEvent data)
    {
        foreach (var field in new[] { "OpenPath", "FileName", "FilePath", "Path", "Name" })
        {
            var value = GetValue(data, field);
            if (value is string path && !string.IsNullOrWhiteSpace(path))
            {
                return path;
            }
        }

        return null;
    }

    private static List<string> GetFileIdentities(TraceEvent data, int pid)
    {
        var identities = new List<string>();
        foreach (var field in new[] { "FileObject", "FileKey", "FileObjectPointer" })
        {
            var value = NormalizeFileIdentity(GetValue(data, field));
            if (value is not null)
            {
                identities.Add($"{field.ToLowerInvariant()}:{value}");
            }
        }

        foreach (var field in new[] { "FileHandle" })
        {
            var value = NormalizeFileIdentity(GetValue(data, field));
            if (value is not null)
            {
                identities.Add($"pid:{pid}:{field.ToLowerInvariant()}:{value}");
            }
        }

        return identities;
    }

    private static string? NormalizeFileIdentity(object? value)
    {
        if (value is null)
        {
            return null;
        }

        if (value is string text)
        {
            text = text.Trim();
            if (string.IsNullOrEmpty(text))
            {
                return null;
            }

            return TryNormalizeIntegerText(text, out var normalizedText)
                ? normalizedText
                : text.ToLowerInvariant();
        }

        try
        {
            if (value is IntPtr pointer)
            {
                return "0x" + pointer.ToInt64().ToString("x", CultureInfo.InvariantCulture);
            }

            if (value is UIntPtr unsignedPointer)
            {
                return "0x" + unsignedPointer.ToUInt64().ToString("x", CultureInfo.InvariantCulture);
            }

            var unsignedValue = Convert.ToUInt64(value, CultureInfo.InvariantCulture);
            return "0x" + unsignedValue.ToString("x", CultureInfo.InvariantCulture);
        }
        catch (Exception error) when (
            error is not AccessViolationException &&
            error is not OutOfMemoryException &&
            error is not StackOverflowException)
        {
            return value.ToString()?.ToLowerInvariant();
        }
    }

    private static bool TryNormalizeIntegerText(string text, out string normalizedText)
    {
        if (text.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
        {
            if (ulong.TryParse(text[2..], NumberStyles.HexNumber, CultureInfo.InvariantCulture, out var hexValue))
            {
                normalizedText = "0x" + hexValue.ToString("x", CultureInfo.InvariantCulture);
                return true;
            }
        }
        else if (ulong.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out var decimalValue))
        {
            normalizedText = "0x" + decimalValue.ToString("x", CultureInfo.InvariantCulture);
            return true;
        }

        normalizedText = string.Empty;
        return false;
    }

    private static object? GetValue(TraceEvent data, string name)
    {
        try
        {
            var value = data.PayloadByName(name);
            if (value is not null)
            {
                return value;
            }
        }
        catch (Exception error) when (
            error is not AccessViolationException &&
            error is not OutOfMemoryException &&
            error is not StackOverflowException)
        {
        }

        var property = data.GetType().GetProperty(name, BindingFlags.Instance | BindingFlags.Public);
        if (property is null)
        {
            return null;
        }

        try
        {
            return property.GetValue(data);
        }
        catch (TargetInvocationException)
        {
            return null;
        }
    }

    private static void PruneInterestingFiles(DateTime nowUtc)
    {
        var ttl = TimeSpan.FromSeconds(ActiveOptions.TtlSeconds);
        foreach (var (fileIdentity, fileInfo) in InterestingFiles.ToArray())
        {
            if (nowUtc - fileInfo.LastSeenUtc > ttl)
            {
                InterestingFiles.Remove(fileIdentity);
            }
        }
    }
}
