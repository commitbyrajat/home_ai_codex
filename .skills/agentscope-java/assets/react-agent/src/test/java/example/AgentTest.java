package example;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.agentscope.core.ReActAgent;
import io.agentscope.core.agent.RuntimeContext;
import io.agentscope.core.message.Msg;
import io.agentscope.core.message.MsgRole;
import io.agentscope.core.message.TextBlock;
import io.agentscope.core.message.ToolResultBlock;
import io.agentscope.core.message.ToolUseBlock;
import io.agentscope.core.message.UserMessage;
import io.agentscope.core.model.ChatResponse;
import io.agentscope.core.model.GenerateOptions;
import io.agentscope.core.model.Model;
import io.agentscope.core.model.ToolSchema;
import io.agentscope.core.state.InMemoryAgentStateStore;
import io.agentscope.core.tool.Toolkit;
import io.agentscope.core.util.JsonUtils;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Flux;

class AgentTest {
    @Test
    void executesRegisteredToolAndFeedsItsResultBackToModel() {
        AtomicInteger modelCalls = new AtomicInteger();
        Model model = scripted(messages -> {
            if (modelCalls.getAndIncrement() == 0) {
                Map<String, Object> arguments = Map.of("left", 19, "right", 23);
                return ChatResponse.builder().content(List.of(ToolUseBlock.builder()
                        .id("addition-1").name("add")
                        .input(arguments)
                        .content(JsonUtils.getJsonCodec().toJson(arguments)).build())).build();
            }
            ToolResultBlock result = messages.stream().flatMap(m -> m.getContent().stream())
                    .filter(ToolResultBlock.class::isInstance).map(ToolResultBlock.class::cast)
                    .filter(r -> "addition-1".equals(r.getId())).findFirst().orElseThrow();
            assertEquals("add", result.getName());
            assertTrue(result.getOutput().stream().filter(TextBlock.class::isInstance)
                    .map(TextBlock.class::cast).anyMatch(t -> t.getText().contains("42")),
                    () -> "Unexpected tool output: " + result.getOutput().stream()
                            .filter(TextBlock.class::isInstance).map(TextBlock.class::cast)
                            .map(TextBlock::getText).collect(Collectors.joining("|")));
            return text("The sum is 42.");
        });
        Toolkit tools = new Toolkit();
        tools.registerTool(new CalculatorTools());
        try (ReActAgent agent = ReActAgent.builder().name("calculator-test")
                .sysPrompt("Use arithmetic tools.").model(model).toolkit(tools).maxIters(4).build()) {
            Msg reply = agent.call(List.of(new UserMessage("Add 19 and 23")), context("alice"))
                    .block(Duration.ofSeconds(10));
            assertNotNull(reply);
            assertTrue(reply.getTextContent().contains("42"));
            assertEquals(2, modelCalls.get());
        }
    }

    @Test
    void preservesFollowUpHistoryAndIsolatesUsersWithTheSameSessionId() {
        Model model = scripted(messages -> text(messages.stream()
                .filter(m -> m.getRole() == MsgRole.USER).map(Msg::getTextContent)
                .collect(Collectors.joining("|"))));
        try (ReActAgent agent = ReActAgent.builder().name("session-test")
                .sysPrompt("Echo user context.").model(model)
                .stateStore(new InMemoryAgentStateStore()).maxIters(2).build()) {
            assertEquals("alice-private", ask(agent, "alice", "alice-private"));
            assertEquals("bob-private", ask(agent, "bob", "bob-private"));
            assertEquals("alice-private|follow-up", ask(agent, "alice", "follow-up"));
        }
    }

    private static String ask(ReActAgent agent, String user, String input) {
        Msg result = agent.call(List.of(new UserMessage(input)), context(user)).block(Duration.ofSeconds(10));
        assertNotNull(result);
        return result.getTextContent();
    }

    private static RuntimeContext context(String user) {
        return RuntimeContext.builder().userId(user).sessionId("same-session").build();
    }

    private static ChatResponse text(String value) {
        return ChatResponse.builder().content(List.of(TextBlock.builder().text(value).build())).build();
    }

    private static Model scripted(Function<List<Msg>, ChatResponse> response) {
        return new Model() {
            @Override
            public Flux<ChatResponse> stream(List<Msg> messages, List<ToolSchema> tools,
                    GenerateOptions options) {
                return Flux.defer(() -> Flux.just(response.apply(messages)));
            }

            @Override
            public String getModelName() {
                return "offline-scripted-model";
            }
        };
    }
}
