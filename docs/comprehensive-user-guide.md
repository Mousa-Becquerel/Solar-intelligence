# DH Agents - Comprehensive User Guide

## 🌟 Welcome to DH Agents

Your AI-powered platform for comprehensive photovoltaic (PV) market analysis, component pricing, and industry news. Access real-time data, generate interactive visualizations, and stay updated with the latest industry developments.

---

## 🔐 **Getting Started**

*Please contact your system administrator for login credentials.*

---

## 🎯 **Available Agents**

### **1. Market Analysis Agent** 📊
**Purpose**: Comprehensive PV market data analysis and insights

**Capabilities**:
- Historical solar capacity installations
- Market forecast data (2025-2030)
- Country-specific market analysis
- Trend analysis and comparisons
- Interactive data visualization

**Data Collections**:
- `market_search_data`: Historical and forecast solar capacity installations with market segments (Distributed, Centralized) and scenarios (Historical, Most Probable, High, Low)
- **Available Countries**: Germany, France, Italy, Spain, Netherlands, Poland, Belgium, Austria, Sweden, and other European countries
- **Available Years**: 2015-2024 (historical data) + 2025-2030 (forecasts)
- **Available Segments**: Distributed (rooftop) and Centralized (utility-scale)
- **Available Scenarios**: Historical, Most Probable, High, Low

### **2. Module Prices Agent** 💰
**Purpose**: Solar component pricing analysis and market trends

**Capabilities**:
- Real-time component price data
- Interactive price tables and charts
- Regional price comparisons
- Trend analysis and forecasting
- Statistical analysis (boxplots, distributions)

**Available Components**:
- Module (solar modules)
- Cell (solar cells)
- Wafer (solar wafers)
- Polysilicon
- EVA (Ethylene Vinyl Acetate)
- PV glass
- Silver
- Copper
- Aluminium

**Regions Covered**:
- China
- EU (European Union)
- US (United States)
- India
- Overseas
- Australia

**Data Collections**:
- `component_prices`: Solar module pricing data with specific technology types and regional variations
- **Available Countries**: Australia, China, EU, India, Overseas, US
- **Available Years**: 2019 through 2023 (historical data available)
- **Available Module Types**: CdTe, n-type TOPCon, p-type mono-Si PERC G12, p-type multi-Si PERC, and more
- **Time Coverage**: Monthly and yearly price data with historical trends

### **3. News Agent** 📰
**Purpose**: Latest PV industry news and developments

**Capabilities**:
- Real-time news search
- Industry developments tracking
- Market trend analysis
- Company announcements
- Technology updates
- Policy and regulatory news

**News Categories**:
- Solar technology developments
- Industry trends and market updates
- Company announcements and business news
- Policy and regulatory changes
- Investment and financing news
- Project developments and installations
- Renewable energy developments

---

## 🚀 **Query Examples by Agent**

## 📊 **Market Analysis Agent Queries**

**Available Data:**
- **Historical Data**: 2015-2024 (actual installations)
- **Forecast Data**: 2025-2030 (projections with multiple scenarios)
- **Geographic Coverage**: Major European solar markets
- **Market Segments**: Centralized (utility-scale) and Distributed (rooftop) solar
- **Scenarios**: Most Probable, High, and Low forecasts for future years

### **Basic Market Analysis (Data Only - No Charts)**
```
"What was Germany's total solar capacity installed in 2023?"
"Show me Italy's PV market performance for 2024"
"How much distributed solar did France add in 2022?"
"What was Spain's centralized solar growth in 2023?"
"Display Netherlands solar installations for 2024"
"Show me Poland's PV market data for 2024"
"What was Belgium's solar capacity in 2023?"
"Display Austria's distributed solar installations for 2024"
"What was Sweden's PV capacity in 2023?"
```

### **Multi-Year Trends (Data Only - No Charts)**
```
"Show Germany's solar installation trend from 2020 to 2024"
"How did Italy's PV market grow over the last 5 years?"
"Display France's solar capacity evolution from 2019 to 2024"
"What's Spain's annual solar growth pattern since 2020?"
"Chart Poland's PV development over the past 4 years"
"Show Netherlands' solar market growth from 2020 to 2024"
"Display Belgium's PV capacity trend over the last 5 years"
```

### **Trend Line Charts (Charts Generated)**
```
"Plot Germany's solar market growth from 2020 to 2024"
"Create a line chart showing Italy's solar trend over 5 years"
"Graph France's annual PV installations with trend line"
"Show Spain's solar capacity growth trajectory over time"
"Chart Germany's solar development from 2015 to 2024"
"Plot Netherlands' PV market growth from 2020 to 2024"
"Show Belgium's solar capacity trend line over time"
"Create a trend analysis of Austria's solar market"
```

### **Comparative Bar Charts (Charts Generated)**
```
"Create a bar chart of Germany's annual PV installations"
"Show Italy's solar capacity by year as bars for 2020-2024"
"Bar graph showing France's solar growth by year"
"Display Spain's annual PV additions as bars"
"Chart Germany's distributed vs centralized solar as bars"
"Show Poland's annual solar installations as grouped bars"
```

### **Market Share Pie Charts (Charts Generated)**
```
"Show Germany's distributed vs centralized solar split as pie chart"
"Create a pie chart of Italy's solar segment distribution"
"Display France's distributed vs centralized solar as pie chart"
"Show Spain's solar market segments as pie chart"
"Chart Netherlands' distributed vs centralized solar split"
"Show Austria's solar segment breakdown for 2024"
```

### **Advanced Visualizations (Charts Generated)**
```
"Create a stacked chart showing Germany's solar segments by year"
"Show Italy's solar development with scenario forecasts"
"Generate a before and after chart for France's market changes"
"Display Germany's growth rate by solar segment"
"Create a multi-year view of Spain's solar performance"
"Show all scenarios for Germany's solar projections to 2030"
"Compare capacity trends between Germany and Italy"
```

### **Market Intelligence Questions (Data Only - No Charts)**
```
"What is Germany's total solar capacity as of 2024?"
"What was Italy's PV growth rate in 2023?"
"Show me France's current solar market size"
"What is Spain's distributed solar capacity?"
"Display Netherlands' centralized solar development"
"What is Poland's distributed solar capacity?"
"What is Sweden's total PV capacity?"
```

### **Market Share Analysis (Data Only - No Charts)**
```
"What's Germany's distributed vs centralized solar share?"
"How big is Italy's distributed solar segment?"
"What portion of France's capacity is centralized?"
"Show Spain's solar segment breakdown"
"Display Netherlands' distributed solar market share"
"Show Austria's solar segment distribution"
```

### **Future Market Projections (Charts Generated)**
```
"What's Germany's projected solar capacity in 2030?"
"Show Italy's solar market projections through 2028"
"What does France's future solar outlook look like?"
"Display Spain's growth scenarios for the next 5 years"
"Compare optimistic vs conservative forecasts for Germany"
"Show Netherlands' solar capacity projections to 2030"
"What is Poland's projected PV growth through 2028?"
```

### **Multi-Scenario Analysis (Charts Generated)**
```
"Show all scenarios for Germany's solar projections to 2030"
"Display multiple scenarios for Italy's solar growth"
"Compare different forecast scenarios for France"
"Show all the scenarios for Spain's solar development"
"Display forecasting scenarios for Netherlands' solar market"
"Show three scenarios for Poland's PV growth"
```

### **Solar Market Segments (Data Only - No Charts)**
```
"What's Germany's distributed vs centralized solar split in 2024?"
"Show Italy's distributed solar trend over time"
"How is France's solar segment mix changing over time?"
"Display Spain's centralized solar development"
"Show Netherlands' distributed solar penetration trend"
"Show Austria's solar segment evolution"
```

### **Country Comparisons (Charts Generated)**
```
"Compare Germany and Italy's solar capacity trends"
"Show France vs Spain's solar market development"
"Compare Netherlands and Belgium's PV growth"
"Display Germany vs Austria's solar market performance"
"Show Italy vs Poland's solar development"
```

## 💰 **Module Prices Agent Queries**

**📊 Chart Generation Rules:**
- **Data Queries**: When you ask for data, prices, or information, you get tabular data only
- **Chart Queries**: When you explicitly ask for charts, plots, graphs, or visualizations, you get charts
- **Keywords for Charts**: Use words like "plot", "chart", "graph", "visualize", "generate", "create", "show me a chart"

**Available Data:**
- **Countries**: Australia, China, EU, India, Overseas, US
- **Years**: 2019 through 2023 (historical data available)
- **Module Types**: CdTe, n-type TOPCon, p-type mono-Si PERC G12, p-type multi-Si PERC, and more

### **Average Price Queries (Data Only - No Charts)**
```
"What's the average module price in China for 2023?"
"What was the average module price in the EU in 2022?"
"Show me the average module price in India for 2023"
"What are the average module prices in US for 2021?"
"Average module price in Australia for 2023"
"Module price in Overseas for 2020"
```

### **Module Type Queries**
```
"Which types of modules are available?"
"What module types do you have data for?"
"Show me all available module types"
"List the different module technologies"
"What are the module technology options?"
```

### **Specific Module Type Price Queries**
```
"What is the average price of p-type mono-Si PERC G12?"
"Show me the price of CdTe modules"
"What's the price for n-type TOPCon modules?"
"Average price of p-type multi-Si PERC modules"
"Price of p-type mono-Si PERC G12 in China"
"CdTe module price in EU for 2023"
"n-type TOPCon price in US for 2024"
```

### **Price Change Analysis (Charts Generated)**
```
"Show me the monthly price change for CdTe in Overseas"
"What is the year-over-year price change for p-type mono-Si PERC G12 in China?"
"Monthly price trends for p-type mono-Si PERC M10 in EU"
"Price change over time for n-type TOPCon in US"
"Show price evolution for CdTe from 2020 to 2023"
"Year-over-year price change for p-type multi-Si PERC in India"
"Monthly price variation for p-type mono-Si PERC G12 in Australia"
```

### **Regional Price Comparison (Charts Generated)**
```
"Compare module prices between China and EU"
"Show price differences between US and India"
"Regional price comparison for p-type mono-Si PERC G12"
"Price comparison across all regions for CdTe"
"Compare n-type TOPCon prices in different countries"
"Regional price analysis for p-type multi-Si PERC"
```

### **Time Series Analysis (Charts Generated)**
```
"Show me the price trend for p-type mono-Si PERC G12 from 2020 to 2024"
"Price evolution of CdTe modules over time"
"Historical price data for n-type TOPCon in China"
"Price timeline for p-type multi-Si PERC in EU"
"Show price changes month by month for CdTe in Overseas"
"Yearly price progression for p-type mono-Si PERC G12 in US"
```

## 📰 **News Agent Queries**

### **General News Queries**
```
"What are the latest developments in solar technology?"
"Show me recent news about solar panel manufacturing"
"What's happening with solar energy policy in Europe?"
"Find news about major solar companies"
"Show me the latest solar industry trends"
"Tell me about recent solar energy developments"
"Show me Germany's solar market innovation trends"
"German solar market digitalization trends"
```

### **Technology News**
```
"What are the latest innovations in solar panel technology?"
"Show me news about new solar cell technologies"
"Find articles about solar energy storage"
"What's new in solar panel efficiency improvements?"
"Show me developments in solar manufacturing processes"
"Tell me about recent solar technology breakthroughs"
"German solar market technology adoption"
"Show me Germany's floating solar projects"
```

### **Market and Business News**
```
"What are the latest solar market trends?"
"Show me news about solar company mergers and acquisitions"
"Find articles about solar energy investments"
"What's happening with solar energy financing?"
"Show me news about major solar projects"
"Tell me about solar industry business developments"
"German solar market investment trends"
"Show Germany PV export/import data"
```

### **Policy and Regulatory News**
```
"What are the latest solar energy policies in Europe?"
"Show me news about solar subsidies and incentives"
"Find articles about renewable energy regulations"
"What's happening with solar energy targets?"
"Show me news about carbon reduction policies"
"Tell me about recent solar energy policy changes"
```

### **Industry Developments**
```
"What's new in the solar industry?"
"Show me recent solar energy developments"
"Find news about solar power growth"
"What are the latest trends in renewable energy?"
"Tell me about solar energy market updates"
```

### **Company and Project News**
```
"Show me news about major solar companies"
"Find articles about solar energy projects"
"What's happening with solar energy investments?"
"Tell me about recent solar company announcements"
"Show me news about solar energy financing"
```

---

## 💡 **Advanced Query Techniques**

### **Follow-up Questions**
All agents support conversation memory, allowing you to ask follow-up questions:

```
User: "What is the solar capacity in Germany?"
Agent: [Provides Germany's solar capacity data]

User: "How does this compare to France?"
Agent: [Compares Germany vs France using previous context]

User: "What's the forecast for both countries?"
Agent: [Provides forecast data for both countries]
```

### **Complex Multi-Part Queries**
```
"Compare solar capacity between Germany, France, and Italy, then show me the forecast for these countries and identify which one has the strongest growth potential"
```

### **Data Visualization Requests**
```
"Create a chart showing module price trends in China and EU"
"Show me a boxplot of solar capacity by country"
"Generate a line chart of forecasted growth"
```

---

## 🎨 **Data Visualization Features**

### **Available Chart Types**
- **Line Charts**: For trend analysis over time
- **Bar Charts**: For comparisons between categories
- **Box Plots**: For statistical distribution analysis
- **Pie Charts**: For market share analysis
- **Scatter Plots**: For correlation analysis

### **Interactive Features**
- **Zoom and Pan**: Navigate through large datasets
- **Hover Information**: Get detailed data on hover
- **Download Options**: Export charts as images
- **Filter Controls**: Focus on specific data subsets

---

## 📱 **User Interface Features**

### **Conversation Management**
- **New Chat**: Start fresh conversations
- **Conversation History**: Access previous discussions
- **Agent Switching**: Seamlessly switch between agents
- **Memory Context**: Agents remember conversation context

### **Data Export**
- **CSV Downloads**: Export table data
- **Chart Images**: Save visualizations
- **Report Generation**: Create comprehensive reports

### **Real-time Updates**
- **Live Data**: Access current market information
- **Auto-refresh**: Get the latest updates
- **Notification System**: Stay informed of important changes

---

## 🔧 **Tips for Best Results**

### **Be Specific**
- ✅ "Show module prices in China for the last 6 months"
- ❌ "Show me some prices"

### **Use Natural Language**
- ✅ "Which countries have the highest solar capacity?"
- ✅ "Compare prices between different regions"
- ✅ "What are the latest solar technology developments?"

### **Ask Follow-up Questions**
- ✅ "How does this compare to last year?"
- ✅ "What's the forecast for this trend?"
- ✅ "Show me the factors driving this change?"

### **Request Visualizations**
- ✅ "Create a chart showing the trends"
- ✅ "Show me a comparison chart"
- ✅ "Generate a boxplot of the data"

---

## 🆘 **Getting Help**

### **If You're Not Getting Expected Results**
1. **Rephrase your question** - Try different wording
2. **Be more specific** - Include time periods, regions, or components
3. **Use follow-up questions** - Build on previous responses
4. **Switch agents** - Different agents have different capabilities

### **Common Query Patterns**
- **For Market Data**: "What is the [metric] in [country/region] for [time period]?"
- **For Price Data**: "Show [component] prices in [region] for [time period]"
- **For News**: "Find news about [topic] in [region/time period]"

### **Contact Support**
- Check the admin panel for system status
- Review conversation history for context
- Try different query formulations

---

## 🚀 **Quick Start Examples**

### **Market Analysis Quick Start**
1. Ask: "What is the solar capacity in Germany?"
2. Follow up: "How does this compare to France?"
3. Ask: "What's the forecast for both countries?"

### **Module Prices Quick Start**
1. Ask: "Show module prices in China"
2. Follow up: "Create a chart of the trends"
3. Ask: "Compare with EU prices"

### **News Quick Start**
1. Ask: "What are the latest solar technology developments?"
2. Follow up: "Show me news about major companies"
3. Ask: "What are the market trends?"

---

**Happy analyzing! 🌟**

*This guide covers all three agents available in DH Agents. Each agent specializes in different aspects of the solar industry, providing comprehensive insights for your analysis needs.* 