import { fileSearchTool, Agent, AgentInputItem, Runner } from "@openai/agents";


// Tool definitions
const fileSearch = fileSearchTool([
  "vs_68e5846b1a708191a5b17970b3ac9994"
])
const digitalizationAnalyst = new Agent({
  name: "Digitalization analyst ",
  instructions: "You are an expert in digitalization and AI integration in the different solutions and solutions of the different the stages of the PV value chain, you have access to an AI report in the PV industry, you must ask users query about the topic by accessing the data from this report",
  model: "gpt-4.1",
  tools: [
    fileSearch
  ],
  modelSettings: {
    reasoning: {
      effort: "low",
      summary: "auto"
    },
    store: true
  }
});

type WorkflowInput = { input_as_text: string };


// Main code entrypoint
export const runWorkflow = async (workflow: WorkflowInput) => {
  const conversationHistory: AgentInputItem[] = [
    {
      role: "user",
      content: [
        {
          type: "input_text",
          text: workflow.input_as_text
        }
      ]
    }
  ];
  const runner = new Runner({
    traceMetadata: {
      __trace_source__: "agent-builder",
      workflow_id: "wf_68e7dad14470819088ac6c5882196f920445e169e9469949"
    }
  });
  const digitalizationAnalystResultTemp = await runner.run(
    digitalizationAnalyst,
    [
      ...conversationHistory
    ]
  );
  conversationHistory.push(...digitalizationAnalystResultTemp.newItems.map((item) => item.rawItem));

  if (!digitalizationAnalystResultTemp.finalOutput) {
      throw new Error("Agent result is undefined");
  }

  const digitalizationAnalystResult = {
    output_text: digitalizationAnalystResultTemp.finalOutput ?? ""
  };
  return digitalizationAnalystResult;
}
