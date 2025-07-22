# Pydantic-AI Weaviate Agent Application

This is a focused application that uses a **Pydantic-AI based Weaviate agent** for PV market analysis through vector database queries with **conversation memory**.

## 🚀 Features

### Pydantic-AI Weaviate Agent
- **Agent Type**: `pydantic_weaviate`
- **Technology Stack**: Pydantic-AI + Weaviate Vector Database
- **Capabilities**: 
  - Semantic search through Weaviate vector database
  - Natural language queries for PV market data
  - **Access to both historical and forecast data**
  - **Intelligent query reformulation** - translates user questions into specific Weaviate queries
  - Intelligent data retrieval and analysis
  - **Conversation memory across multiple queries**
  - Fallback mode when Weaviate is unavailable

## 🧠 Conversation Memory

### How It Works
The agent maintains conversation context using Pydantic-AI's built-in `message_history` feature:

- **Per-Conversation Memory**: Each conversation maintains its own message history
- **Context Awareness**: The agent can reference previous questions and build on conversation context
- **Automatic Cleanup**: Memory is cleared when conversations are deleted
- **Memory Monitoring**: Admin can monitor memory usage and active conversations

### Memory Features
- ✅ **Context Retention**: Agent remembers previous questions in the same conversation
- ✅ **Follow-up Queries**: Can answer questions like "How does this compare to France?"
- ✅ **Memory Management**: Automatic cleanup and memory monitoring
- ✅ **Conversation Isolation**: Each conversation has independent memory

## 📊 Available Data Collections

The agent has access to two Weaviate collections:

1. **Market_historical_data**: Historical solar capacity installations and market data
2. **Market_most_probable_forecast**: Forecast data from 2025 to 2030 in the most probable scenario

## 📊 Available Agent

**Pydantic-AI Weaviate Agent** (`pydantic_weaviate`) ⭐
- Pydantic-AI + Weaviate Vector Database
- Semantic search capabilities
- Vector-based data retrieval
- **Conversation memory support**
- **Historical and forecast data access**

## 🛠️ Setup and Installation

### Prerequisites
- Python 3.8+
- Weaviate Cloud instance (optional, for full functionality)
- OpenAI API key

### Environment Variables
Create a `.env` file with the following variables:

```env
# Required
OPENAI_API_KEY=your_openai_api_key
FLASK_SECRET_KEY=your_flask_secret_key

# Optional (for Weaviate functionality)
WEAVIATE_URL=your_weaviate_cluster_url
WEAVIATE_API_KEY=your_weaviate_api_key
```

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python reset_database.py
```

## 🚀 Running the Application

### Option 1: Startup Script (Recommended)
```bash
python start_enhanced_app.py
```

### Option 2: Direct Flask Run
```bash
python app.py
```

### Option 3: Test the Pydantic-AI Agent with Memory
```bash
python test_pydantic_weaviate_agent.py
```

## 🌐 Access the Application

- **URL**: http://localhost:5000
- **Default Login**:
  - Username: `admin`
  - Password: `BecqSight2024!`

## 🔧 Agent Usage

The application uses a single Pydantic-AI Weaviate agent for all queries with conversation memory:

**Pydantic Weaviate Agent**: For semantic search and vector-based queries with context retention

## 📝 Usage Examples

### Basic Queries
```
User: "What is the total solar capacity installed in Italy in 2022?"
Agent Reformulation: "solar capacity installations in Italy for 2022"
Weaviate Query: SQL translation to retrieve Italy's 2022 data

User: "What are the current market trends in Germany?"
Agent Reformulation: "solar capacity installations in Germany for recent years"
Weaviate Query: SQL translation to retrieve Germany's recent data

User: "Show me the solar capacity data for France"
Agent Reformulation: "solar capacity installations in France for current period"
Weaviate Query: SQL translation to retrieve France's current data
```

### Forecast Queries
```
User: "What is the forecasted solar capacity for Germany in 2027?"
Agent Reformulation: "forecasted solar capacity for Germany in 2027"
Weaviate Query: SQL translation to retrieve Germany's 2027 forecast

User: "What are the market projections for Italy in 2030?"
Agent Reformulation: "forecasted solar capacity for Italy in 2030"
Weaviate Query: SQL translation to retrieve Italy's 2030 forecast

User: "Show me the forecast data for France from 2025 to 2030"
Agent Reformulation: "forecasted solar capacity for France from 2025 to 2030"
Weaviate Query: SQL translation to retrieve France's forecast range
```

### Historical vs Forecast Comparisons
```
User: "Compare Germany's current capacity with the 2028 forecast"
Agent Reformulation: "compare current solar capacity with forecasted capacity for Germany"
Weaviate Query: SQL translation to retrieve both current and 2028 data

User: "What is the expected growth rate from 2022 to 2030?"
Agent Reformulation: "solar capacity growth trend from 2022 to 2030"
Weaviate Query: SQL translation to retrieve growth data across years

User: "How does the historical trend compare to future projections?"
Agent Reformulation: "compare historical solar capacity trends with forecast projections"
Weaviate Query: SQL translation to retrieve both historical and forecast data
```

### Complex Query Reformulation
```
User: "I want to know about solar energy in Europe, particularly how Italy and France are doing compared to Germany, and what the future looks like"
Agent Reformulation: Multiple specific queries:
- "solar capacity installations in Italy for current period"
- "solar capacity installations in France for current period" 
- "solar capacity installations in Germany for current period"
- "forecasted solar capacity for Italy, France, and Germany for future years"
Weaviate Query: Multiple SQL translations to retrieve comprehensive data
```

### Conversation with Memory
```
User: "What is the solar capacity in Germany?"
Agent Reformulation: "solar capacity installations in Germany for recent years"
Agent: "Germany installed X GW of solar capacity in 2022..."

User: "What is the forecast for Germany in 2028?"
Agent Reformulation: "forecasted solar capacity for Germany in 2028"
Agent: "According to the most probable scenario, Germany is forecasted to reach Y GW by 2028..."

User: "How does the forecast compare to current capacity?"
Agent Reformulation: "compare current solar capacity with forecasted capacity for Germany"
Agent: "Based on the previous data, Germany's capacity is expected to grow from X GW to Y GW..."

User: "What about the growth rate in these countries?"
Agent Reformulation: "solar capacity growth trend in Germany from current to 2028"
Agent: "Based on the historical and forecast data, Germany's growth rate is..."
```

## 🔍 Testing

### Test Pydantic-AI Agent with Memory
```bash
python test_pydantic_weaviate_agent.py
```

The test script demonstrates:
- Basic query functionality
- Conversation memory across multiple queries
- Memory information and monitoring
- Memory clearing functionality
- Context-aware responses

### Test Application
```bash
python start_enhanced_app.py
# The startup script will test the agent during initialization
```

## 🏗️ Architecture

### Code Structure
```
cursor_langchain_enhanced/
├── app.py                          # Main Flask application
├── pydantic_weaviate_agent.py      # Pydantic-AI Weaviate agent with memory
├── start_enhanced_app.py           # Startup script
├── test_pydantic_weaviate_agent.py # Pydantic-AI agent tests with memory
├── requirements.txt                # Dependencies
└── README_ENHANCED.md             # This file
```

### Agent Integration
- **Focused Approach**: Single Pydantic-AI agent for all queries
- **Conversation Memory**: Built-in message history per conversation
- **Clean Interface**: Simple chat interface
- **Fallback Support**: Works even without Weaviate connection
- **Memory Management**: Integrated memory monitoring and cleanup

## 🔧 Configuration

### Weaviate Setup
1. Create a Weaviate Cloud instance
2. Set up your collections:
   - `Market_historical_data`: Historical solar capacity installations and market data
   - `Market_most_probable_forecast`: Forecast data from 2025 to 2030 in the most probable scenario
3. Add your data to the vector database
4. Configure environment variables

### Agent Configuration
- Modify `pydantic_weaviate_agent.py` to adjust agent behavior
- Update system prompts for different use cases
- Configure usage limits and token budgets
- Adjust conversation memory settings

### Memory Configuration
- **Token Limits**: Increased to 4000 tokens to accommodate conversation context
- **Memory Storage**: In-memory storage per conversation ID
- **Cleanup**: Automatic cleanup when conversations are deleted

## 🐛 Troubleshooting

### Common Issues

1. **Pydantic-AI Agent Not Available**
   - Check Weaviate credentials
   - Verify OpenAI API key
   - Check network connectivity

2. **Weaviate Connection Issues**
   - Verify WEAVIATE_URL and WEAVIATE_API_KEY
   - Check Weaviate cluster status
   - Agent will run in fallback mode

3. **Memory Issues**
   - Application includes automatic memory cleanup
   - Monitor memory usage in admin panel
   - Restart application if needed

4. **Conversation Memory Issues**
   - Check admin panel for conversation memory info
   - Clear conversation memory if needed
   - Verify conversation IDs are being passed correctly

## 📈 Performance

### Memory Management
- Automatic memory monitoring
- Garbage collection integration
- High memory usage alerts
- Cleanup procedures
- Conversation memory tracking

### Agent Performance
- Pydantic-AI agent: Fast semantic search with context
- Usage limits and token budgets
- Conversation memory efficiency

## 🔒 Security

- User authentication and authorization
- Role-based access control
- Secure API key management
- Database connection security
- Conversation isolation per user

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review agent test outputs
3. Check application logs
4. Verify environment configuration
5. Monitor conversation memory usage

## 🚀 Deployment

### Production Deployment
```bash
# Use Gunicorn for production
gunicorn -c gunicorn.conf.py app:app
```

### Environment Variables for Production
- Set all required environment variables
- Use strong Flask secret key
- Configure database URL
- Set up proper logging

## 🧠 Memory Management

### Conversation Memory
- **Storage**: In-memory storage with conversation ID mapping
- **Cleanup**: Automatic cleanup when conversations are deleted
- **Monitoring**: Admin panel shows active conversations and memory usage
- **Limits**: Token limits increased to accommodate conversation context

### System Memory
- **Monitoring**: Real-time memory usage tracking
- **Cleanup**: Automatic cleanup when memory usage exceeds 450MB
- **Logging**: Detailed memory usage logging for debugging

## 🔄 Query Reformulation

### How It Works
The agent intelligently reformulates user questions before passing them to the Weaviate tool:

1. **User Question**: "What is the solar capacity in Germany?"
2. **Agent Reformulation**: "solar capacity installations in Germany for recent years"
3. **Weaviate Tool**: Translates to SQL and retrieves data
4. **Response**: Comprehensive answer with context

### Reformulation Guidelines
The agent follows specific guidelines for query reformulation:

- **Historical Data**: "solar capacity installations in [country] for [year]"
- **Forecast Data**: "forecasted solar capacity for [country] in [year]"
- **Comparisons**: "compare solar capacity between [country1] and [country2] for [year]"
- **Trends**: "solar capacity growth trend in [country] from [year1] to [year2]"
- **Always specifies**: Country, year, and data type (historical vs forecast)

---

**Note**: This application is focused on the Pydantic-AI Weaviate agent for efficient vector-based queries and semantic search with conversation memory support. 