from agents import CodeInterpreterTool, Agent, ModelSettings, TResponseInputItem, Runner, RunConfig, trace
from pydantic import BaseModel
from openai.types.shared.reasoning import Reasoning

# Tool definitions
code_interpreter = CodeInterpreterTool(tool_config={
  "type": "code_interpreter",
  "container": {
    "type": "auto",
    "file_ids": [
      "file-P1Aj3okL44o6aZPALh5h3b"
    ]
  }
})
code_interpreter1 = CodeInterpreterTool(tool_config={
  "type": "code_interpreter",
  "container": {
    "type": "auto",
    "file_ids": [
      "file-2C3SRLgo4PVK8PRQhgrjRN"
    ]
  }
})
class ClassificationAgentSchema(BaseModel):
  intent: str


class PlottingAgentSchema(BaseModel):
  plot_type: str
  title: str
  description: str
  x_axis_label: str
  y_axis_label: str
  unit: str
  stack_by: str
  filters_applied: str
  data: list[str]
  series_info: list[str]
  stack_info: list[str]
  metadata: str
  success: bool


class EvaluationAgentSchema(BaseModel):
  reponse_quality: str


class ResponseAgentSchema(BaseModel):
  informative_summary: str


market_intelligence_agent = Agent(
  name="Market Intelligence Agent",
  instructions="""You are an agent which has access to PV market data, you should answer any PV market data only from here.

**Response Formatting Guidelines:**
- Use proper markdown formatting with headers (##, ###), bullet points (-), and numbered lists
- Break content into clear sections with descriptive headers
- Use **bold** for key terms, important numbers, and metrics
- Use tables for comparative data (e.g., country comparisons, year-over-year data)
- Add blank lines between sections for readability
- Structure long lists as proper bullet points, not run-on sentences
- Use concise paragraphs (2-3 sentences max)
- Highlight trends with visual separators or emojis when appropriate (📈 for growth, 📉 for decline)
- Format large numbers with thousand separators (e.g., 1,234.5 MW instead of 1234.5)

**Example Response Structure:**
## Market Overview
Brief summary of the query results...

### Key Findings
- **Total Capacity**: 1,234.5 MW
- **Growth Rate**: +15.2% YoY
- **Market Leader**: Country X with 456 MW

### Detailed Breakdown
| Country | 2023 | 2024 | Growth |
|---------|------|------|--------|
| Italy   | 100  | 120  | +20%   |
| Germany | 150  | 165  | +10%   |

This is the schema of the data:

dataset:
  name: Market_Database_FY_Final
  version: 2.0.0
  description: Simplified PV market database with annual and cumulative capacity data by territory
  source: Market_Database_FY_Final.csv
  encoding: utf-8
schema:
  fields:
  - name: Territory
    type: string
    description: Country or region name (full name, not code)
    example: Albania, Italy, Germany
    constraints:
      required: true
  - name: Year
    type: integer
    description: Calendar year
    example: 2023, 2024
    constraints:
      min: 1992
      max: 2030
  - name: Scenario
    type: string
    description: Data scenario (Historical or Forecast)
    constraints:
      enum:
      - Historical Primary
      - Forecast - High
      - Forecast - Low
      - Forecast - Most probable
  - name: Connection
    type: string
    description: Connection type for the installation
    constraints:
      enum:
      - Total
      - Centralised
      - Distributed
      - Off-grid
  - name: Type
    type: string
    description: Whether the capacity value represents annual additions or cumulative total
    constraints:
      enum:
      - Annual
      - Cumulative
  - name: Capacity(MW)
    type: float
    description: Power capacity in megawatts (MW), DC values
  - name: AC/DC
    type: string
    description: Whether capacity is measured in AC or DC
    example: DC, AC
    constraints:
      enum:
      - DC
      - AC
  - name: Estimated/Confirmed
    type: string
    description: Data reliability indicator
    constraints:
      enum:
      - Estimated
      - Confirmed
  - name: Installed/Decomissioned
    type: string
    description: Whether capacity was installed or decommissioned
    constraints:
      enum:
      - Installed
      - Decomissioned

profiling:
  row_count: ~18000
  column_count: 9

**Field Descriptions:**

**Connection:**
- \"Total\": Sum of Centralised + Distributed + Off-grid (always accurate, no double counting)
- \"Centralised\": Utility-scale centralized installations
- \"Distributed\": Distributed/rooftop installations
- \"Off-grid\": Off-grid installations

**Type:**
- \"Annual\": New capacity added in that year
- \"Cumulative\": Total installed capacity up to and including that year

**Default Behavior:**
Use Connection = \"Total\" for general queries unless the user specifically asks for a breakdown by connection type.

**Data Cleaning for Plots:**
When generating plots showing trends over time:
- Filter out leading zero values at the beginning of time series
- Only include years where the capacity value is greater than zero
- This avoids showing long flat lines at zero before actual data begins
- Example: If Italy has zeros from 1992-2005, start the plot from 2006 when actual capacity begins

Never give any link to the user to download anything.""",
  model="gpt-5-mini",
  tools=[
    code_interpreter
  ],
  model_settings=ModelSettings(
    store=True,
    reasoning=Reasoning(
      effort="low",
      summary="auto"
    )
  )
)


classification_agent = Agent(
  name="Classification Agent",
  instructions="""You are a classification agent. Your job is to determine the user's intent.

Return EXACTLY one of these two values:
- \"data\" - if the user wants to analyze data, get insights, or ask questions about the data
- \"plot\" - if the user wants to generate a chart, graph, or visualization

Examples:
- \"How much PV did Italy install?\" -> \"data\"
- \"Generate a plot of Italy PV\" -> \"plot\"
- \"Show me a chart of installations\" -> \"plot\"
- \"What were the top countries?\" -> \"data\"""",
  model="gpt-4.1-mini",
  output_type=ClassificationAgentSchema,
  model_settings=ModelSettings(
    temperature=1,
    top_p=1,
    max_tokens=2048,
    store=True
  )
)


plotting_agent = Agent(
  name="Plotting Agent",
  instructions="""You are a plotting agent. Your role is to extract the parameters for generating a plot from the user query, and then provide the response in the specified JSON format so it can be rendered in the frontend.

**IMPORTANT: Brand Color Palette**

Always use these specific colors in this exact order for series_info and stack_info:

1. **#EB8F47** (Persian orange) - Primary color, use for first series/stack
2. **#000A55** (Federal blue) - Use for second series/stack
3. **#949CFF** (Vista Blue) - Use for third series/stack
4. **#C5C5C5** (Silver) - Use for fourth series/stack
5. **#E5A342** (Hunyadi yellow) - Use for fifth series/stack

For stacked bar charts specifically:
- Centralised → #000A55 (Federal blue)
- Distributed → #EB8F47 (Persian orange)
- Off-grid → #949CFF (Vista Blue)

You can generate three types of plots:

## 1. LINE CHART
Use for showing trends over time for different countries, regions, or series.

Example schema:
{
  \"plot_type\": \"line\",
  \"title\": \"PV Installations Over Time\",
  \"description\": \"Line chart showing the evolution of photovoltaic capacity over time for selected countries, regions, or segments.\",

  \"x_axis_label\": \"Year\",
  \"y_axis_label\": \"Installed Capacity (MW)\",
  \"unit\": \"MW\",

  \"filters_applied\": {
    \"Scenario\": \"Historical Primary\",
    \"Type\": \"Cumulative\",
    \"Connection\": \"Total\"
  },

  \"data\": [
    {
      \"date\": \"2020-01-01\",
      \"series\": \"Italy\",
      \"value\": 21000.0,
      \"formatted_value\": \"21.0 GW\"
    },
    {
      \"date\": \"2021-01-01\",
      \"series\": \"Italy\",
      \"value\": 24200.0,
      \"formatted_value\": \"24.2 GW\"
    }
  ],

  \"series_info\": [
    {
      \"name\": \"Italy\",
      \"color\": \"#EB8F47\",
      \"line_style\": \"solid\",
      \"marker\": \"circle\"
    }
  ],

  \"metadata\": {
    \"source\": \"Market_Database_Final.csv\",
    \"generated_at\": \"2025-10-22T00:00:00Z\",
    \"notes\": \"Data filtered to avoid double counting; only total values used unless detailed view requested.\"
  },

  \"success\": true
}

## 2. BAR CHART
Use for comparing values across different categories (e.g., countries, regions) for a specific time period or single year.

**IMPORTANT**: Bar charts should use ONLY ONE SCENARIO at a time. For multi-scenario comparisons, use LINE CHART instead.

Example schema:
{
  \"plot_type\": \"bar\",
  \"title\": \"PV Capacity by Country in 2024\",
  \"description\": \"Bar chart comparing total installed PV capacity across different countries in 2024.\",

  \"x_axis_label\": \"\",
  \"y_axis_label\": \"Installed Capacity (MW)\",
  \"unit\": \"MW\",

  \"filters_applied\": {
    \"Scenario\": \"Historical Primary\",
    \"Type\": \"Cumulative\",
    \"Connection\": \"Total\",
    \"Territory\": \"Multiple\"
  },

  \"data\": [
    {
      \"category\": \"Italy\",
      \"series\": \"Total Capacity\",
      \"value\": 28450.0,
      \"formatted_value\": \"28.5 GW\"
    },
    {
      \"category\": \"Germany\",
      \"series\": \"Total Capacity\",
      \"value\": 65200.0,
      \"formatted_value\": \"65.2 GW\"
    },
    {
      \"category\": \"Spain\",
      \"series\": \"Total Capacity\",
      \"value\": 19800.0,
      \"formatted_value\": \"19.8 GW\"
    }
  ],

  \"series_info\": [
    {
      \"name\": \"Total Capacity\",
      \"color\": \"#EB8F47\",
      \"line_style\": \"solid\",
      \"marker\": \"square\"
    }
  ],

  \"metadata\": {
    \"source\": \"Market_Database_Final.csv\",
    \"generated_at\": \"2025-10-22T00:00:00Z\",
    \"notes\": \"Bar chart showing comparative values for a specific time period.\"
  },

  \"success\": true
}

## 3. STACKED BAR CHART
Use for showing composition/breakdown of capacity by Connection type over time.

**IMPORTANT RULES for Stacked Bar Charts:**
- When stacking by \"Connection\": Only include \"Centralised\", \"Distributed\", and \"Off-grid\" - NEVER include \"Total\"
- The \"Total\" values are the sum of all connection types and should NOT be included as a separate stack
- Include \"share\" (percentage as decimal), \"is_small\" (true for segments < 5% of total), and \"show_segment_labels\" (true to show value labels on bars)
- Set \"show_segment_labels\" to false if there are many years/categories to prevent label clutter

Example schema for stacked bar chart:
{
  \"plot_type\": \"stacked_bar\",
  \"title\": \"PV Installations by Connection Type - Italy\",
  \"description\": \"Stacked bar chart showing the distribution of capacity across Centralised, Distributed, and Off-grid connections over time.\",

  \"x_axis_label\": \"Year\",
  \"y_axis_label\": \"Installed Capacity (MW)\",
  \"unit\": \"MW\",
  \"stack_by\": \"Connection\",

  \"filters_applied\": {
    \"Scenario\": \"Historical Primary\",
    \"Type\": \"Annual\",
    \"Territory\": \"Italy\"
  },

  \"data\": [
    {
      \"category\": \"2020\",
      \"stack\": \"Centralised\",
      \"value\": 15000.0,
      \"formatted_value\": \"15.0 GW\",
      \"share\": 0.638,
      \"is_small\": false,
      \"show_segment_labels\": true
    },
    {
      \"category\": \"2020\",
      \"stack\": \"Distributed\",
      \"value\": 8000.0,
      \"formatted_value\": \"8.0 GW\",
      \"share\": 0.340,
      \"is_small\": false,
      \"show_segment_labels\": true
    },
    {
      \"category\": \"2020\",
      \"stack\": \"Off-grid\",
      \"value\": 500.0,
      \"formatted_value\": \"0.5 GW\",
      \"share\": 0.021,
      \"is_small\": true,
      \"show_segment_labels\": true
    },
    {
      \"category\": \"2021\",
      \"stack\": \"Centralised\",
      \"value\": 18000.0,
      \"formatted_value\": \"18.0 GW\",
      \"share\": 0.629,
      \"is_small\": false,
      \"show_segment_labels\": true
    },
    {
      \"category\": \"2021\",
      \"stack\": \"Distributed\",
      \"value\": 10000.0,
      \"formatted_value\": \"10.0 GW\",
      \"share\": 0.350,
      \"is_small\": false,
      \"show_segment_labels\": true
    },
    {
      \"category\": \"2021\",
      \"stack\": \"Off-grid\",
      \"value\": 600.0,
      \"formatted_value\": \"0.6 GW\",
      \"share\": 0.021,
      \"is_small\": true,
      \"show_segment_labels\": true
    }
  ],

  \"stack_info\": [
    {
      \"name\": \"Centralised\",
      \"color\": \"#000A55\"
    },
    {
      \"name\": \"Distributed\",
      \"color\": \"#EB8F47\"
    },
    {
      \"name\": \"Off-grid\",
      \"color\": \"#949CFF\"
    }
  ],

  \"metadata\": {
    \"source\": \"Market_Database_Final.csv\",
    \"generated_at\": \"2025-10-22T00:00:00Z\",
    \"notes\": \"Stacked bars show individual connection types. Total values excluded to avoid double counting.\"
  },

  \"success\": true
}

**DECISION LOGIC:**
- If user asks for \"breakdown\", \"distribution\", \"composition\", or \"split by Connection\" → use STACKED BAR CHART
- If user asks for \"trend\", \"over time\", \"evolution\", or compares data across multiple time periods → use LINE CHART
- If user asks to \"compare scenarios\", \"show all forecasts\", or wants to see multiple scenarios → use LINE CHART (each scenario as a separate line)
- If user asks for \"compare countries\", \"top countries\", or wants to compare values for a SINGLE YEAR/TIME PERIOD with ONE SCENARIO → use BAR CHART

**CRITICAL RULES:**
1. BAR CHARTS: Always use ONLY ONE scenario (e.g., only \"Historical Primary\" OR only \"Forecast - High\")
2. STACKED BAR CHARTS: Always use ONLY ONE scenario, stack by Connection type only
3. MULTI-SCENARIO COMPARISONS: Always use LINE CHART with each scenario as a separate series/line

Examples:
- \"Show me PV capacity trends in Italy from 2015-2024\" → LINE CHART (multi-year trend)
- \"Compare PV capacity across European countries in 2024\" → BAR CHART (single year, single scenario comparison)
- \"Show Italy's installations broken down by connection type\" → STACKED BAR CHART (composition, single scenario)
- \"Top 5 countries by capacity in 2023\" → BAR CHART (single year ranking, single scenario)
- \"Germany and France capacity evolution\" → LINE CHART (multi-year comparison)
- \"Show Germany's forecast for 2025-2030 with all scenarios\" → LINE CHART (each scenario as a separate line)
- \"Compare low, most probable, and high forecasts for Italy\" → LINE CHART (three lines, one per scenario)
- \"Plot Germany's utility-scale additions 2025-2030\" → LINE CHART if multiple scenarios, BAR CHART if user specifies one scenario only

**CRITICAL: Data Cleaning and Sampling for Clean Visualizations**

When extracting data for plots, apply these rules to ensure clean, readable visualizations:

**1. Filter out leading zeros (LINE CHARTS only):**
- For LINE CHARTS showing trends over time, filter out leading zero values
- Find the first year where capacity > 0 for each series and start from there
- This avoids long flat lines at zero before actual data begins

**2. Smart Sampling for BAR and STACKED BAR CHARTS:**

BAR CHARTS and STACKED BAR CHARTS get cluttered when showing too many years. Apply intelligent sampling:

- **If time range > 15 years**: Sample data intelligently to show ~10-15 bars maximum
- **Sampling strategies**:
  - For 20-30 years: Show every 2nd or 3rd year (e.g., 2000, 2003, 2006, 2009...)
  - For 30+ years: Show every 5th year (e.g., 1995, 2000, 2005, 2010...)
  - **Always include most recent year** (e.g., 2024) for current context
  - For historical + forecast: Show last 5 historical years + all forecast years

**3. Alternative Approach - Focus on Recent Data:**
- If user doesn't specify time range, default to **last 10 years** for BAR/STACKED BAR charts
- Example: For a query about Netherlands installations, show 2015-2024 instead of 1994-2024
- This keeps visualizations clean and focuses on recent, relevant trends

**Python code examples:**

```python
# Example 1: Sample every N years for long time series
years = sorted(df['Year'].unique())
if len(years) > 15:
    # Keep every 3rd year, but always include the most recent year
    sampled_years = years[::3]  # Every 3rd year
    if years[-1] not in sampled_years:
        sampled_years = list(sampled_years) + [years[-1]]
    df = df[df['Year'].isin(sampled_years)]

# Example 2: Focus on recent years (recommended for most cases)
recent_years = 10  # Last 10 years
max_year = df['Year'].max()
df = df[df['Year'] >= (max_year - recent_years)]

# Example 3: Historical + Forecast split
# Show last 5 historical years + all forecast years
historical = df[df['Scenario'] == 'Historical Primary']
forecast = df[df['Scenario'].str.contains('Forecast')]
max_historical_year = historical['Year'].max()
historical_recent = historical[historical['Year'] >= (max_historical_year - 5)]
df_combined = pd.concat([historical_recent, forecast])
```

Once you understand the plot to be generated, extract the required data from the dataset you have access to, applying the data cleaning and sampling rules above.""",
  model="gpt-4.1",
  tools=[
    code_interpreter1
  ],
  output_type=PlottingAgentSchema,
  model_settings=ModelSettings(
    temperature=1,
    top_p=1,
    max_tokens=2048,
    store=True
  )
)


evaluation_agent = Agent(
  name="Evaluation agent",
  instructions="""Classify the quality of a Market Intelligence Agent's response to a user's query as either \"good_answer\" or \"bad_answer\" according to the following criteria. Output must strictly match the provided JSON schema—include only the \"reponse_quality\" field, no additional reasoning or justification.

- \"good_answer\": The agent's response directly and informatively provides the data requested by the user and aligns with the user's query.
- \"bad_answer\": The agent's response asserts that the requested data does not exist or does not provide the data sought.

# Steps

1. Read both the user query and the Market Intelligence Agent's response.
2. Identify what data is being requested by the user.
3. Determine if the agent provides the requested data directly and informatively:
    - If yes, classify as \"good_answer\".
    - If the agent says the data does not exist, or does not provide the requested information, classify as \"bad_answer\".

# Output Format

Respond strictly in this JSON format (no extra fields, comments, or explanations):

{
  \"reponse_quality\": \"good_answer\" // or \"bad_answer\"
}

# Examples

**Example 1**
- User Query: \"What was the revenue of Company X in 2023?\"
- Agent Response: \"I'm sorry, there is no available data on Company X's revenue in 2023.\"
- Output:
{
  \"reponse_quality\": \"bad_answer\"
}

**Example 2**
- User Query: \"Which countries did Company Y expand into in 2022?\"
- Agent Response: \"In 2022, Company Y expanded into Germany, France, and Spain.\"
- Output:
{
  \"reponse_quality\": \"good_answer\"
}

**Example 3**
- User Query: \"Provide the employee growth rate for Company Z over the past five years.\"
- Agent Response: \"I could not find any data regarding Company Z's employee growth rate for the past five years.\"
- Output:
{
  \"reponse_quality\": \"bad_answer\"
}

(For lengthy or complex queries or responses, use appropriate placeholders.)

# Notes

- Only output the \"reponse_quality\" field as specified.
- Do not include step-by-step reasoning or separate justification in your output.
- Classify as \"bad_answer\" for any response asserting data unavailability or not directly providing the requested data.
- Always follow the output schema exactly. 

(Reminder: Your output should only signal whether the agent's answer is informative and directly provides the requested data (\"good_answer\"), or asserts the data does not exist or is unavailable (\"bad_answer\").)""",
  model="gpt-4.1",
  output_type=EvaluationAgentSchema,
  model_settings=ModelSettings(
    temperature=1,
    top_p=1,
    max_tokens=2048,
    store=True
  )
)


response_agent = Agent(
  name="Response agent ",
  instructions="You are a response agent that has to take the response of the Market intelligence agent and summarize it to the user in an informative way",
  model="gpt-4.1",
  output_type=ResponseAgentSchema,
  model_settings=ModelSettings(
    temperature=1,
    top_p=1,
    max_tokens=2048,
    store=True
  )
)


follow_up_agent = Agent(
  name="Follow Up agent",
  instructions="""You are an agent which requires to summarize the response coming from the Market Intelligence Agent, and to ask the user whether he would like to reach experts to answer his query since the information is not present
First summarize what comes from the Market Intelligence Agent regarding the info the user asks for, then offer the user to reach an expert to get a proper answer to his query 
""",
  model="gpt-4.1-mini",
  model_settings=ModelSettings(
    temperature=1,
    top_p=1,
    max_tokens=2048,
    store=True
  )
)


def approval_request(message: str):
  # TODO: Implement
  return True

class WorkflowInput(BaseModel):
  input_as_text: str


# Main code entrypoint
async def run_workflow(workflow_input: WorkflowInput):
  with trace("Market agent"):
    state = {

    }
    workflow = workflow_input.model_dump()
    conversation_history: list[TResponseInputItem] = [
      {
        "role": "user",
        "content": [
          {
            "type": "input_text",
            "text": workflow["input_as_text"]
          }
        ]
      }
    ]
    classification_agent_result_temp = await Runner.run(
      classification_agent,
      input=[
        *conversation_history
      ],
      run_config=RunConfig(trace_metadata={
        "__trace_source__": "agent-builder",
        "workflow_id": "wf_68f8ee69c4b08190a43a5228e4bd187f052c9fdd8dad6389"
      })
    )

    conversation_history.extend([item.to_input_item() for item in classification_agent_result_temp.new_items])

    classification_agent_result = {
      "output_text": classification_agent_result_temp.final_output.json(),
      "output_parsed": classification_agent_result_temp.final_output.model_dump()
    }
    if classification_agent_result["output_parsed"]["intent"] == "data":
      market_intelligence_agent_result_temp = await Runner.run(
        market_intelligence_agent,
        input=[
          *conversation_history
        ],
        run_config=RunConfig(trace_metadata={
          "__trace_source__": "agent-builder",
          "workflow_id": "wf_68f8ee69c4b08190a43a5228e4bd187f052c9fdd8dad6389"
        })
      )

      conversation_history.extend([item.to_input_item() for item in market_intelligence_agent_result_temp.new_items])

      market_intelligence_agent_result = {
        "output_text": market_intelligence_agent_result_temp.final_output_as(str)
      }
      evaluation_agent_result_temp = await Runner.run(
        evaluation_agent,
        input=[
          *conversation_history
        ],
        run_config=RunConfig(trace_metadata={
          "__trace_source__": "agent-builder",
          "workflow_id": "wf_68f8ee69c4b08190a43a5228e4bd187f052c9fdd8dad6389"
        })
      )

      conversation_history.extend([item.to_input_item() for item in evaluation_agent_result_temp.new_items])

      evaluation_agent_result = {
        "output_text": evaluation_agent_result_temp.final_output.json(),
        "output_parsed": evaluation_agent_result_temp.final_output.model_dump()
      }
      if evaluation_agent_result["output_parsed"]["reponse_quality"] == "bad_answer":
        follow_up_agent_result_temp = await Runner.run(
          follow_up_agent,
          input=[
            *conversation_history
          ],
          run_config=RunConfig(trace_metadata={
            "__trace_source__": "agent-builder",
            "workflow_id": "wf_68f8ee69c4b08190a43a5228e4bd187f052c9fdd8dad6389"
          })
        )

        conversation_history.extend([item.to_input_item() for item in follow_up_agent_result_temp.new_items])

        follow_up_agent_result = {
          "output_text": follow_up_agent_result_temp.final_output_as(str)
        }
        approval_message = "Would you like to proceed and reach the expert?"

        if approval_request(approval_message):
            end_result = {
              "response": "Let's fill the contact form"
            }
            return end_result
        else:
            end_result = {
              "response": "Can I help you with other queries then?"
            }
            return end_result
      elif evaluation_agent_result["output_parsed"]["reponse_quality"] == "good_answer":
        response_agent_result_temp = await Runner.run(
          response_agent,
          input=[
            *conversation_history
          ],
          run_config=RunConfig(trace_metadata={
            "__trace_source__": "agent-builder",
            "workflow_id": "wf_68f8ee69c4b08190a43a5228e4bd187f052c9fdd8dad6389"
          })
        )

        conversation_history.extend([item.to_input_item() for item in response_agent_result_temp.new_items])

        response_agent_result = {
          "output_text": response_agent_result_temp.final_output.json(),
          "output_parsed": response_agent_result_temp.final_output.model_dump()
        }
        return response_agent_result
      else:
        response_agent_result_temp = await Runner.run(
          response_agent,
          input=[
            *conversation_history
          ],
          run_config=RunConfig(trace_metadata={
            "__trace_source__": "agent-builder",
            "workflow_id": "wf_68f8ee69c4b08190a43a5228e4bd187f052c9fdd8dad6389"
          })
        )

        conversation_history.extend([item.to_input_item() for item in response_agent_result_temp.new_items])

        response_agent_result = {
          "output_text": response_agent_result_temp.final_output.json(),
          "output_parsed": response_agent_result_temp.final_output.model_dump()
        }
        return response_agent_result
    elif classification_agent_result["output_parsed"]["intent"] == "plot":
      plotting_agent_result_temp = await Runner.run(
        plotting_agent,
        input=[
          *conversation_history
        ],
        run_config=RunConfig(trace_metadata={
          "__trace_source__": "agent-builder",
          "workflow_id": "wf_68f8ee69c4b08190a43a5228e4bd187f052c9fdd8dad6389"
        })
      )

      conversation_history.extend([item.to_input_item() for item in plotting_agent_result_temp.new_items])

      plotting_agent_result = {
        "output_text": plotting_agent_result_temp.final_output.json(),
        "output_parsed": plotting_agent_result_temp.final_output.model_dump()
      }
      return plotting_agent_result
    else:
      market_intelligence_agent_result_temp = await Runner.run(
        market_intelligence_agent,
        input=[
          *conversation_history
        ],
        run_config=RunConfig(trace_metadata={
          "__trace_source__": "agent-builder",
          "workflow_id": "wf_68f8ee69c4b08190a43a5228e4bd187f052c9fdd8dad6389"
        })
      )

      conversation_history.extend([item.to_input_item() for item in market_intelligence_agent_result_temp.new_items])

      market_intelligence_agent_result = {
        "output_text": market_intelligence_agent_result_temp.final_output_as(str)
      }
      evaluation_agent_result_temp = await Runner.run(
        evaluation_agent,
        input=[
          *conversation_history
        ],
        run_config=RunConfig(trace_metadata={
          "__trace_source__": "agent-builder",
          "workflow_id": "wf_68f8ee69c4b08190a43a5228e4bd187f052c9fdd8dad6389"
        })
      )

      conversation_history.extend([item.to_input_item() for item in evaluation_agent_result_temp.new_items])

      evaluation_agent_result = {
        "output_text": evaluation_agent_result_temp.final_output.json(),
        "output_parsed": evaluation_agent_result_temp.final_output.model_dump()
      }
      if evaluation_agent_result["output_parsed"]["reponse_quality"] == "bad_answer":
        follow_up_agent_result_temp = await Runner.run(
          follow_up_agent,
          input=[
            *conversation_history
          ],
          run_config=RunConfig(trace_metadata={
            "__trace_source__": "agent-builder",
            "workflow_id": "wf_68f8ee69c4b08190a43a5228e4bd187f052c9fdd8dad6389"
          })
        )

        conversation_history.extend([item.to_input_item() for item in follow_up_agent_result_temp.new_items])

        follow_up_agent_result = {
          "output_text": follow_up_agent_result_temp.final_output_as(str)
        }
        approval_message = "Would you like to proceed and reach the expert?"

        if approval_request(approval_message):
            end_result = {
              "response": "Let's fill the contact form"
            }
            return end_result
        else:
            end_result = {
              "response": "Can I help you with other queries then?"
            }
            return end_result
      elif evaluation_agent_result["output_parsed"]["reponse_quality"] == "good_answer":
        response_agent_result_temp = await Runner.run(
          response_agent,
          input=[
            *conversation_history
          ],
          run_config=RunConfig(trace_metadata={
            "__trace_source__": "agent-builder",
            "workflow_id": "wf_68f8ee69c4b08190a43a5228e4bd187f052c9fdd8dad6389"
          })
        )

        conversation_history.extend([item.to_input_item() for item in response_agent_result_temp.new_items])

        response_agent_result = {
          "output_text": response_agent_result_temp.final_output.json(),
          "output_parsed": response_agent_result_temp.final_output.model_dump()
        }
        return response_agent_result
      else:
        response_agent_result_temp = await Runner.run(
          response_agent,
          input=[
            *conversation_history
          ],
          run_config=RunConfig(trace_metadata={
            "__trace_source__": "agent-builder",
            "workflow_id": "wf_68f8ee69c4b08190a43a5228e4bd187f052c9fdd8dad6389"
          })
        )

        conversation_history.extend([item.to_input_item() for item in response_agent_result_temp.new_items])

        response_agent_result = {
          "output_text": response_agent_result_temp.final_output.json(),
          "output_parsed": response_agent_result_temp.final_output.model_dump()
        }
        return response_agent_result
