package com.tradeapi.examples;

import com.google.gson.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

public final class Demo {
    private static final Gson PRETTY = new GsonBuilder().setPrettyPrinting().create();
    private static JsonObject readObject(String file) throws IOException {
        Path path = Path.of(file);
        if (Files.size(path) > 65536) throw new IllegalArgumentException("JSON file exceeds 64 KiB");
        String text = Files.readString(path, StandardCharsets.UTF_8).replaceFirst("^\uFEFF", "");
        return JsonParser.parseString(text).getAsJsonObject();
    }
    private static String text(JsonObject object, String key) { return object.get(key).getAsString(); }
    private static int run(String[] arguments) throws Exception {
        List<String> args = new ArrayList<>(Arrays.asList(arguments));
        boolean execute = args.removeIf(a -> a.equals("--execute"));
        if (args.size() < 1 || args.size() > 3) throw new IllegalArgumentException("Usage: demo PRODUCT [COMMAND [VALUE]] [--execute]");
        String product = args.get(0), command = args.size() > 1 ? args.get(1) : "query", value = args.size() > 2 ? args.get(2) : "";
        if (!product.equals("tdx") && !product.equals("ths")) throw new IllegalArgumentException("PRODUCT must be tdx or ths");
        JsonObject profile = readObject("config/api-contract.json").getAsJsonObject(product), spec;
        if (command.equals("query")) {
            JsonObject queries = profile.getAsJsonObject("queries");
            String category = value.isEmpty() ? "funds" : value;
            if (!queries.has(category)) throw new IllegalArgumentException("Unsupported query");
            spec = new JsonObject(); spec.addProperty("method", "GET"); spec.addProperty("path", text(queries, category));
            spec.addProperty("input", "none"); spec.addProperty("live", false);
        } else {
            JsonObject commands = profile.getAsJsonObject("commands");
            if (!commands.has(command)) throw new IllegalArgumentException("Unsupported command");
            spec = commands.getAsJsonObject(command).deepCopy();
        }
        String input = text(spec, "input"), endpoint = text(spec, "path");
        JsonObject body = null;
        if (input.equals("file")) body = readObject(value);
        else if (input.startsWith("id-")) {
            if (!value.matches("[A-Za-z0-9_-]{1,128}")) throw new IllegalArgumentException("Pass an existing action/preview ID");
            if (input.equals("id-path")) endpoint += value;
            else { body = new JsonObject(); body.addProperty("preview_id", value); }
        } else if (!value.isEmpty() && !command.equals("query")) throw new IllegalArgumentException("This command takes no VALUE");
        if (spec.get("live").getAsBoolean() && !execute) {
            JsonObject dry = new JsonObject(); dry.addProperty("dry_run", true); dry.addProperty("method", text(spec,"method"));
            dry.addProperty("path", endpoint); dry.add("body", body); dry.addProperty("note", "Nothing sent. --execute submits ONE REAL action.");
            System.out.println(PRETTY.toJson(dry)); return 0;
        }
        String base = System.getenv(text(profile,"url_env")); if (base == null || base.isEmpty()) base = text(profile,"base_url");
        base = base.replaceAll("/+$", "");
        URI uri = URI.create(base);
        if (!"http".equals(uri.getScheme()) || !"127.0.0.1".equals(uri.getHost()) || uri.getPort() < 1 || uri.getPort() > 65535 ||
            uri.getUserInfo() != null || uri.getQuery() != null || uri.getFragment() != null || (uri.getPath() != null && !uri.getPath().isEmpty()))
            throw new IllegalArgumentException("URL must be http://127.0.0.1:<port>");
        String token = Optional.ofNullable(System.getenv(text(profile,"token_env"))).orElse("").trim();
        if (!endpoint.equals("/health") && !token.matches("[A-Za-z0-9_-]{32,256}")) throw new IllegalArgumentException("Set " + text(profile,"token_env"));
        HttpURLConnection conn = (HttpURLConnection) URI.create(base + endpoint).toURL().openConnection(Proxy.NO_PROXY);
        try {
            conn.setInstanceFollowRedirects(false); conn.setConnectTimeout(90000); conn.setReadTimeout(90000);
            conn.setRequestMethod(text(spec,"method")); conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("Connection", "close");
            if (!token.isEmpty()) conn.setRequestProperty("Authorization", "Bearer " + token);
            if (body != null) {
                byte[] data = body.toString().getBytes(StandardCharsets.UTF_8);
                conn.setDoOutput(true); conn.setFixedLengthStreamingMode(data.length);
                try (OutputStream output = conn.getOutputStream()) { output.write(data); }
            }
            int status = conn.getResponseCode();
            InputStream source = status >= 400 ? conn.getErrorStream() : conn.getInputStream();
            if (source == null) throw new IOException("Empty error response; do not resubmit");
            byte[] data;
            try (InputStream stream = source) { data = stream.readNBytes(16*1024*1024+1); }
            if (data.length > 16*1024*1024) throw new IOException("Response exceeds 16 MiB");
            JsonObject result = JsonParser.parseString(new String(data, StandardCharsets.UTF_8)).getAsJsonObject();
            System.out.println("HTTP " + status); System.out.println(PRETTY.toJson(result));
            return status == 200 && !(result.has("ok") && result.get("ok").isJsonPrimitive() && result.get("ok").getAsString().equals("false")) ? 0 : 1;
        } finally { conn.disconnect(); }
    }
    public static void main(String[] args) {
        // JDK URLConnection must not transparently replay a POST after an I/O failure.
        System.setProperty("sun.net.http.retryPost", "false");
        System.setOut(new PrintStream(System.out, true, StandardCharsets.UTF_8));
        System.setErr(new PrintStream(System.err, true, StandardCharsets.UTF_8));
        try { System.exit(run(args)); }
        catch (Exception error) { System.err.println(error.getMessage() + "\nNo automatic retry. Reconcile any action in the official client."); System.exit(1); }
    }
}
