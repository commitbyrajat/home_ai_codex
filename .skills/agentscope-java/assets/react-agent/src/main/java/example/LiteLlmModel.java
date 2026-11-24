package example;

import io.agentscope.extensions.model.openai.OpenAIChatModel;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

public final class LiteLlmModel {
    private static final String DEFAULT_BASE_URL = "http://127.0.0.1:4000/v1";
    private static final String DEFAULT_ENV_FILE =
            "/Users/rajatnigam/workspace/home_ai_stack/litellm-tev-stack/.env";

    private LiteLlmModel() {}

    public static OpenAIChatModel create() {
        return create(Path.of(setting("LITELLM_ENV_FILE", DEFAULT_ENV_FILE)),
                setting("LITELLM_BASE_URL", DEFAULT_BASE_URL));
    }

    static OpenAIChatModel create(Path envFile, String baseUrl) {
        return OpenAIChatModel.builder()
                .apiKey(readApiKey(envFile))
                .baseUrl(baseUrl)
                .modelName("engineering-auto")
                .stream(true)
                // The router can select different backends; native JSON-schema support is unverified.
                .nativeStructuredOutput(false)
                .nativeStructuredOutputWithTools(false)
                .build();
    }

    private static String setting(String name, String fallback) {
        String value = System.getenv(name);
        return value == null || value.isBlank() ? fallback : value;
    }

    private static String readApiKey(Path envFile) {
        try {
            for (String raw : Files.readAllLines(envFile)) {
                String line = raw.strip();
                if (line.startsWith("export ")) {
                    line = line.substring(7).stripLeading();
                }
                int separator = line.indexOf('=');
                if (separator < 0 || !line.substring(0, separator).strip().equals("LITELLM_MASTER_KEY")) {
                    continue;
                }
                String value = line.substring(separator + 1).strip();
                if (value.startsWith("\"") || value.startsWith("'")) {
                    int end = value.indexOf(value.charAt(0), 1);
                    if (end < 0 || !(value.substring(end + 1).isBlank()
                            || value.substring(end + 1).stripLeading().startsWith("#"))) {
                        throw new IllegalStateException("Invalid quoted LITELLM_MASTER_KEY in stack .env");
                    }
                    value = value.substring(1, end);
                } else {
                    value = value.split("\\s+#", 2)[0].strip();
                }
                if (!value.isBlank()) {
                    return value;
                }
                break;
            }
        } catch (IOException e) {
            throw new IllegalStateException("Cannot read LiteLLM stack .env; check LITELLM_ENV_FILE", e);
        }
        throw new IllegalStateException("LITELLM_MASTER_KEY is missing or empty in LiteLLM stack .env");
    }
}
