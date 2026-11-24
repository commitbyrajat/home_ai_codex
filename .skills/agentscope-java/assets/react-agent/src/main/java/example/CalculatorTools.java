package example;

import io.agentscope.core.tool.Tool;
import io.agentscope.core.tool.ToolParam;

public final class CalculatorTools {
    @Tool(name = "add", description = "Add two signed 32-bit integers; fail on overflow.",
            readOnly = true, concurrencySafe = true)
    public int add(
            @ToolParam(name = "left", description = "First integer") int left,
            @ToolParam(name = "right", description = "Second integer") int right) {
        return Math.addExact(left, right);
    }
}
