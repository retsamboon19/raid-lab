using System.Collections;
using System.Globalization;
using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using EpinelPS;
using Google.Protobuf;
using Google.Protobuf.Reflection;

static class PacketDecoder
{
    const int MaxBytes = 16 * 1024 * 1024;
    static readonly JsonSerializerOptions Json = new() { WriteIndented = true, PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
    static string Sha(byte[] bytes) => Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
    static string FileSha(string path) => Sha(File.ReadAllBytes(path));
    static void Require(bool valid, string why) { if (!valid) throw new InvalidDataException(why); }
    internal sealed record Expected(int WaveId, int BattleDuration, int CharacterCount, int MonsterCount, int[] CharacterTids,
        int? NativeByteLength = null, string? NativeSha256 = null);

    // Visit only known message fields. This is structural validation, with no combat calculations.
    static int CheckStructure(IMessage message, int depth = 0, int count = 0)
    {
        Require(depth <= 64 && ++count <= 100000, "Known-schema structure exceeds bounds");
        foreach (var field in message.Descriptor.Fields.InFieldNumberOrder())
        {
            var value = field.Accessor.GetValue(message);
            if (field.IsMap)
            {
                var map = (IDictionary)value;
                Require(map.Count <= 100000, "Map field exceeds bounds");
                foreach (DictionaryEntry entry in map)
                    if (entry.Value is IMessage nested) count = CheckStructure(nested, depth + 1, count);
            }
            else if (field.IsRepeated)
            {
                var list = (IList)value;
                Require(list.Count <= 100000, "Repeated field exceeds bounds");
                foreach (var item in list)
                    if (item is IMessage nested) count = CheckStructure(nested, depth + 1, count);
            }
            else if (value is IMessage nested) count = CheckStructure(nested, depth + 1, count);
        }
        return count;
    }
    static void CheckLongJson(IMessage message, JsonElement json)
    {
        foreach (var field in message.Descriptor.Fields.InFieldNumberOrder())
        {
            var value = field.Accessor.GetValue(message);
            if (!json.TryGetProperty(field.JsonName, out var item)) continue;
            if (field.IsMap)
            {
                foreach (DictionaryEntry entry in (IDictionary)value)
                {
                    var element = item.GetProperty(Convert.ToString(entry.Key, CultureInfo.InvariantCulture)!);
                    if (entry.Value is IMessage nested) CheckLongJson(nested, element);
                    else if (entry.Value is long or ulong) Require(element.ValueKind == JsonValueKind.String &&
                        element.GetString() == Convert.ToString(entry.Value, CultureInfo.InvariantCulture), "64-bit map integer changed");
                }
            }
            else if (field.IsRepeated)
            {
                var list = (IList)value; int index = 0;
                foreach (var element in item.EnumerateArray())
                {
                    var original = list[index++];
                    if (original is IMessage nested) CheckLongJson(nested, element);
                    else if (original is long or ulong) Require(element.ValueKind == JsonValueKind.String &&
                        element.GetString() == Convert.ToString(original, CultureInfo.InvariantCulture), "64-bit repeated integer changed");
                }
            }
            else if (value is IMessage nested) CheckLongJson(nested, item);
            else if (value is long or ulong) Require(item.ValueKind == JsonValueKind.String &&
                item.GetString() == Convert.ToString(value, CultureInfo.InvariantCulture), "64-bit integer changed or lost string representation");
        }
    }
    internal static object Decode(byte[] raw, Expected expected, string inputPath)
    {
        Require(raw.Length is > 0 and <= MaxBytes, "Wire input must be 1..16 MiB");
        Require(expected.CharacterCount == 5 && expected.MonsterCount is > 0 and <= 100000, "Invalid expected native DTO counts");
        Require(expected.CharacterTids.Length == 5 && expected.CharacterTids.Distinct().Count() == 5, "Five distinct expected typed identities required");
        if (expected.NativeByteLength is int length) Require(length == raw.Length, "Native export byte length mismatch");
        if (expected.NativeSha256 is string digest) Require(digest == Sha(raw), "Native export digest mismatch");
        var message = NetAntiCheatBattleData.Parser.ParseFrom(raw);
        Require(message.WaveId == expected.WaveId && message.BattleDuration == expected.BattleDuration, "Typed wave/duration mismatch");
        Require(message.Characters.Count == expected.CharacterCount && message.Monsters.Count == expected.MonsterCount, "Typed character/monster count mismatch");
        Require(message.Characters.Select(c => c.Tid).Order().SequenceEqual(expected.CharacterTids.Order()), "Typed character identities mismatch");
        int knownMessages = CheckStructure(message);
        string knownJson = new JsonFormatter(new JsonFormatter.Settings(true)).Format(message);
        using var document = JsonDocument.Parse(knownJson, new JsonDocumentOptions { MaxDepth = 128 });
        CheckLongJson(message, document.RootElement);
        byte[] roundTrip = message.ToByteArray();
        return new
        {
            schemaVersion = 1, status = "passed", scope = "Independent managed decode of unchanged original native protobuf wire bytes; no combat calculations",
            originalWire = new { path = Path.GetFullPath(inputPath), byteLength = raw.Length, sha256 = Sha(raw), bytesRewritten = false },
            nativeExportBinding = new { byteLengthProvided = expected.NativeByteLength.HasValue, sha256Provided = expected.NativeSha256 != null,
                expected.NativeByteLength, expected.NativeSha256 },
            expected, typedReadback = new { message.WaveId, message.BattleDuration, characterCount = message.Characters.Count,
                monsterCount = message.Monsters.Count, characterTids = message.Characters.Select(c => c.Tid).ToArray(), knownMessages },
            decoder = new { assemblyPath = Assembly.GetExecutingAssembly().Location, assemblySha256 = FileSha(Assembly.GetExecutingAssembly().Location),
                generatedTypesAssemblySha256 = FileSha(typeof(NetAntiCheatBattleData).Assembly.Location),
                protobufAssemblySha256 = FileSha(typeof(IMessage).Assembly.Location) },
            knownSchemaDecode = new { provenance = "Independent managed generated-schema JSON; not native ToString output", allInt64AndUInt64AreStrings = true,
                includesDefaultKnownFields = true, message = document.RootElement.Clone() },
            unknownFields = new { omittedFromKnownSchemaJson = true, originalOpaqueBytesRetainedInRawArtifact = true,
                managedRoundTripByteLength = roundTrip.Length, managedRoundTripSha256 = Sha(roundTrip),
                managedRoundTripByteIdentical = raw.AsSpan().SequenceEqual(roundTrip), byteIdenticalRoundTripRequired = false },
            combatCalculationsPerformed = false, submittedScoreCalculated = false
        };
    }
    static void WriteFresh(string input, string output, Expected expected)
    {
        Require(Path.GetFullPath(input) != Path.GetFullPath(output), "Input and output paths must differ");
        if (File.Exists(output)) throw new IOException("Preserve existing decoder output");
        var length = new FileInfo(input).Length;
        Require(length is > 0 and <= MaxBytes, "Wire input must be 1..16 MiB");
        var raw = File.ReadAllBytes(input);
        string report = JsonSerializer.Serialize(Decode(raw, expected, input), Json) + "\n";
        using var stream = new FileStream(output, FileMode.CreateNew, FileAccess.Write, FileShare.None);
        using var writer = new StreamWriter(stream);
        writer.Write(report);
    }
    static void SelfTest()
    {
        // Every payload here is synthetic managed test data, never native battle evidence.
        string directory = Path.Combine(Path.GetTempPath(), "nikke-packet-decoder-test-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(directory); int assertions = 0;
        void Check(bool good, string label) { assertions++; Require(good, label); }
        void Reject(Action action, string label) { bool failed = false; try { action(); } catch (Exception e) when (e is InvalidDataException or InvalidProtocolBufferException or IOException) { failed = true; } Check(failed, label); }
        try
        {
            var message = new NetAntiCheatBattleData { WaveId = 6801001, BattleDuration = 90000 };
            for (int i = 0; i < 5; i++) message.Characters.Add(new NetAntiCheatCharacter { Tid = 100 + i, Csn = 9007199254740993L + i, Slot = i });
            message.Monsters.Add(new NetAntiCheatMonster());
            byte[] raw = message.ToByteArray();
            var expected = new Expected(6801001, 90000, 5, 1, [100, 101, 102, 103, 104], raw.Length, Sha(raw));
            using var report = JsonDocument.Parse(JsonSerializer.Serialize(Decode(raw, expected, "synthetic.pb"), Json));
            Check(report.RootElement.GetProperty("knownSchemaDecode").GetProperty("message").GetProperty("characters")[0].GetProperty("csn").GetString() == "9007199254740993", "Int64 above 2^53 preserved");
            using var unsigned = JsonDocument.Parse(JsonFormatter.Default.Format(new Google.Protobuf.WellKnownTypes.UInt64Value { Value = ulong.MaxValue }));
            Check(unsigned.RootElement.GetString() == "18446744073709551615", "UInt64 formatter preserves maximum as string");
            Reject(() => Decode(raw[..^1], expected with { NativeByteLength = null, NativeSha256 = null }, "synthetic-truncated.pb"), "Truncated payload rejected");
            Reject(() => Decode([0xff, 0xff], expected with { NativeByteLength = null, NativeSha256 = null }, "synthetic-malformed.pb"), "Malformed payload rejected");
            Reject(() => Decode(raw, expected with { WaveId = 9 }, "synthetic.pb"), "Wrong wave rejected");
            Reject(() => Decode(raw, expected with { BattleDuration = 1 }, "synthetic.pb"), "Wrong duration rejected");
            Reject(() => Decode(raw, expected with { MonsterCount = 2 }, "synthetic.pb"), "Native monster count mismatch rejected");
            Reject(() => Decode(raw, expected with { CharacterCount = 4 }, "synthetic.pb"), "Native character count mismatch rejected");
            Reject(() => Decode(raw, expected with { CharacterTids = [1, 2, 3, 4, 5] }, "synthetic.pb"), "Typed identity mismatch rejected");
            Reject(() => Decode(raw, expected with { NativeByteLength = 1 }, "synthetic.pb"), "Native byte length mismatch rejected");
            Reject(() => Decode(raw, expected with { NativeSha256 = new string('0', 64) }, "synthetic.pb"), "Native digest mismatch rejected");
            // Unknown varint field number 2047, value 123. Preserve original bytes independently of JSON.
            using var wire = new MemoryStream(); wire.Write(raw);
            using (var coded = new CodedOutputStream(wire, true)) { coded.WriteTag(2047, WireFormat.WireType.Varint); coded.WriteUInt64(123); coded.Flush(); }
            byte[] unknownRaw = wire.ToArray(); var parsed = NetAntiCheatBattleData.Parser.ParseFrom(unknownRaw);
            Check(parsed.ToByteArray().AsSpan().SequenceEqual(unknownRaw), "Synthetic unknown field preserved by managed parser separately");
            Decode(unknownRaw, expected with { NativeByteLength = null, NativeSha256 = null }, "synthetic-unknown.pb"); assertions++;
            string input = Path.Combine(directory, "synthetic.pb"), output = Path.Combine(directory, "decode.json");
            File.WriteAllBytes(input, raw); WriteFresh(input, output, expected);
            string first = FileSha(output); Reject(() => WriteFresh(input, output, expected), "Fresh output no-overwrite enforced");
            Check(first == FileSha(output) && Sha(raw) == FileSha(input), "Input and preexisting output unchanged");
            Console.WriteLine(JsonSerializer.Serialize(new { status = "passed", provenance = "Synthetic managed decoder controls only; no native battle run", assertions }));
        }
        finally
        {
            string resolved = Path.GetFullPath(directory), temp = Path.GetFullPath(Path.GetTempPath()).TrimEnd(Path.DirectorySeparatorChar);
            Require(Path.GetDirectoryName(resolved) == temp && Path.GetFileName(resolved).StartsWith("nikke-packet-decoder-test-", StringComparison.Ordinal) &&
                Guid.TryParseExact(Path.GetFileName(resolved)["nikke-packet-decoder-test-".Length..], "N", out _) &&
                (File.GetAttributes(resolved) & FileAttributes.ReparsePoint) == 0, "Refuse cleanup outside exact new temporary GUID child");
            Directory.Delete(resolved, true);
        }
    }
    static void ReferenceControl(string input, string output)
    {
        Require(Path.GetFullPath(input) != Path.GetFullPath(output) && !File.Exists(output), "Reference control requires fresh separate output");
        Require(new FileInfo(input).Length is > 0 and <= MaxBytes, "Reference request exceeds bounds");
        byte[] requestRaw = File.ReadAllBytes(input);
        var request = ReqSetShootingRangeScoreV2.Parser.ParseFrom(requestRaw);
        var battle = request.AntiCheatBattleData ?? throw new InvalidDataException("Reference request lacks AntiCheat DTO");
        byte[] managedExtraction = battle.ToByteArray();
        var report = new { status = "passed", provenance = "Managed reserialization of one existing original reference request nested DTO, decoder control only; not a new native packet artifact",
            nativePacketArtifact = false, originalRequest = new { path = Path.GetFullPath(input), sha256 = Sha(requestRaw), byteLength = requestRaw.Length },
            independentDecode = Decode(managedExtraction, new Expected(6801001, 90000, 5, battle.Monsters.Count, [301701, 141207, 110109, 319111, 422205]), "managed-extraction-control-only.pb") };
        Require(FileSha(input) == Sha(requestRaw), "Original reference request changed");
        string json = JsonSerializer.Serialize(report, Json) + "\n";
        using var stream = new FileStream(output, FileMode.CreateNew, FileAccess.Write, FileShare.None);
        using var writer = new StreamWriter(stream); writer.Write(json);
    }
    public static int Main(string[] args)
    {
        try
        {
            if (args.SequenceEqual(["--self-test"])) { SelfTest(); return 0; }
            if (args.Length == 4 && args[0] == "--reference-control" && args[2] == "--output")
            { ReferenceControl(args[1], args[3]); return 0; }
            Require(args.Length % 2 == 0, "Expected named argument/value pairs");
            var options = new Dictionary<string, string>();
            for (int i = 0; i < args.Length; i += 2) Require(options.TryAdd(args[i], args[i + 1]), "Duplicate argument");
            string[] allowed = ["--input", "--output", "--wave", "--duration", "--characters", "--monsters", "--tids", "--native-byte-length", "--native-sha256"];
            Require(options.Keys.All(allowed.Contains), "Unknown argument");
            string Get(string key) => options.TryGetValue(key, out var value) ? value : throw new InvalidDataException("Missing " + key);
            int Number(string key) => int.Parse(Get(key), CultureInfo.InvariantCulture);
            WriteFresh(Get("--input"), Get("--output"), new Expected(Number("--wave"), Number("--duration"), Number("--characters"), Number("--monsters"),
                Get("--tids").Split(',').Select(v => int.Parse(v, CultureInfo.InvariantCulture)).ToArray(),
                options.TryGetValue("--native-byte-length", out var length) ? int.Parse(length, CultureInfo.InvariantCulture) : null,
                options.GetValueOrDefault("--native-sha256")));
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error.GetType().Name + ": " + error.Message); return 2; }
    }
}
