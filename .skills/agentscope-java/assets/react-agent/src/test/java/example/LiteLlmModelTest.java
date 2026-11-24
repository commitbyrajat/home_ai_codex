package example;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import com.sun.net.httpserver.HttpServer;
import io.agentscope.core.message.UserMessage;
import io.agentscope.core.util.JsonUtils;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class LiteLlmModelTest {
    @TempDir Path directory;

    @Test
    void sendsAuthenticatedEngineeringAutoRequestToConfiguredEndpoint() throws Exception {
        Path env = directory.resolve(".env");
        Files.writeString(env, "UNRELATED=value\nexport LITELLM_MASTER_KEY='synthetic-test-key' # fixture\n");
        AtomicReference<String> requestPath = new AtomicReference<>();
        AtomicReference<String> authorization = new AtomicReference<>();
        AtomicReference<String> requestBody = new AtomicReference<>();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            requestPath.set(exchange.getRequestURI().getPath());
            authorization.set(exchange.getRequestHeaders().getFirst("Authorization"));
            requestBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            byte[] response = ("data: {\"id\":\"test\",\"object\":\"chat.completion.chunk\","
                    + "\"model\":\"engineering-auto\",\"choices\":[{\"index\":0,"
                    + "\"delta\":{\"role\":\"assistant\",\"content\":\"ok\"},\"finish_reason\":null}]}\n\n"
                    + "data: [DONE]\n\n").getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type", "text/event-stream");
            exchange.sendResponseHeaders(200, response.length);
            try (var output = exchange.getResponseBody()) {
                output.write(response);
            }
        });
        server.start();
        try {
            var model = LiteLlmModel.create(env, "http://127.0.0.1:" + server.getAddress().getPort() + "/v1");
            var replies = model.stream(List.of(new UserMessage("Say ok")), List.of(), null)
                    .collectList().block(Duration.ofSeconds(10));
            assertTrue(replies != null && !replies.isEmpty());
            assertEquals("/v1/chat/completions", requestPath.get());
            assertEquals("Bearer synthetic-test-key", authorization.get());
            var body = JsonUtils.getJsonCodec().fromJson(requestBody.get(), JsonNode.class);
            assertEquals("engineering-auto", body.get("model").asText());
            assertTrue(body.get("stream").asBoolean());
        } finally {
            server.stop(0);
        }
    }

    @Test
    void refusesMissingKeyWithoutFallingBack() throws Exception {
        Path env = directory.resolve(".env");
        Files.writeString(env, "OTHER_KEY=unrelated\nLITELLM_MASTER_KEY=\n");
        IllegalStateException failure = assertThrows(IllegalStateException.class,
                () -> LiteLlmModel.create(env, "http://127.0.0.1:4000/v1"));
        assertTrue(failure.getMessage().contains("LITELLM_MASTER_KEY"));
        assertThrows(IllegalStateException.class,
                () -> LiteLlmModel.create(directory.resolve("missing.env"), "http://127.0.0.1:4000/v1"));
    }
}
