package example;

import io.agentscope.core.ReActAgent;
import io.agentscope.core.agent.RuntimeContext;
import io.agentscope.core.event.TextBlockDeltaEvent;
import io.agentscope.core.event.ToolCallStartEvent;
import io.agentscope.core.message.Msg;
import io.agentscope.core.message.UserMessage;
import io.agentscope.core.state.InMemoryAgentStateStore;
import io.agentscope.core.tool.Toolkit;
import java.time.Duration;
import java.util.List;
import java.util.Objects;

public final class AgentApp {
    public static void main(String[] args) {
        boolean streaming = args.length > 0 && "--stream".equals(args[0]);
        String prompt = "Use the add tool to calculate 19 + 23, then tell me the result.";
        Toolkit tools = new Toolkit();
        tools.registerTool(new CalculatorTools());
        RuntimeContext context = RuntimeContext.builder()
                .userId("local-user").sessionId("calculator-session").build();
        try (ReActAgent agent = ReActAgent.builder()
                .name("calculator-assistant")
                .sysPrompt("Use the available tools for arithmetic. Give a concise final answer.")
                .model(LiteLlmModel.create())
                .toolkit(tools)
                .stateStore(new InMemoryAgentStateStore())
                .maxIters(8)
                .build()) {
            if (streaming) {
                agent.streamEvents(new UserMessage(prompt), context)
                        .doOnNext(event -> {
                            if (event instanceof TextBlockDeltaEvent delta) {
                                System.out.print(delta.getDelta());
                            } else if (event instanceof ToolCallStartEvent tool) {
                                System.err.println("[tool] " + tool.getToolCallName());
                            }
                        })
                        .blockLast(Duration.ofMinutes(2));
                System.out.println();
            } else {
                Msg reply = Objects.requireNonNull(agent.call(List.of(new UserMessage(prompt)), context)
                        .block(Duration.ofMinutes(2)), "Agent returned no reply");
                System.out.println(reply.getTextContent());
                System.out.println("Termination: " + reply.getGenerateReason());
            }
        }
    }
}
