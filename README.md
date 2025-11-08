# 🧾 LLM Evaluation Playground

A Streamlit web app for generating educational intervention and curriculum prompts, evaluating model-generated outputs using LLM-as-a-Judge evaluation, and validating responses with Pydantic.

**🌐 Live Demo:** [https://llm-judge-tilli.streamlit.app/](https://llm-judge-tilli.streamlit.app/)

## 🎯 Features

- **Intervention Prompt Generation** – Generate targeted intervention plans based on EMT (Emotion Matching Task) scores
- **Curriculum Prompt Generation** – Create personalized curriculum-based intervention plans
- **LLM-as-a-Judge Evaluation** – Uses Google Gemini API to evaluate answer quality with detailed scoring
- **Multi-Metric Scoring** – Evaluates answers across 5 dimensions: Total, Relevance, Clarity, Consistency, and Creativity (1-10 scale)
- **Separate Generator & Judge Models** – Configure different models and temperatures for generation vs. evaluation
- **Pydantic Validation** – Validates structural completeness of answers
- **CSV Logging** – Automatically logs all evaluations to CSV with comprehensive metrics
- **Evaluation History** – View past evaluations with summary statistics
- **Batch Evaluation** – Process multiple evaluations from a CSV file
- **Multiple Models** – Support for Gemini 2.5 models (Pro, Flash, Flash-Lite)

## 🚀 Setup

### 1. Clone or navigate to the project directory

```bash
cd llm-judge
```

### 2. Create a virtual environment

**Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up your API key

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Then edit `.env` and add your Google API key:

```
GOOGLE_API_KEY=your_actual_api_key_here
```

**To get a Google API key:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy and paste it into your `.env` file

### 5. Run the app

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## 📖 Usage

### Individual Evaluation

1. **Enter your API key** in the sidebar (or set it in `.env` file)

2. **Configure models**:
   - Select a **Judge Model** for evaluation (with temperature control)
   - Select a **Generator Model** for answer generation (with temperature control)
   - **Note:** If you check the "Use Structured Output (Gemini)" checkbox, a warning will appear reminding you to keep it unticked and use Pydantic validation instead

3. **Select prompt type**:
   - **EMT (Emotion Matching Task)**: Generate intervention plans based on class performance scores
   - **Curriculum**: Generate curriculum-based interventions based on grade level and skill areas

4. **Enter JSON input data**:
   - **For EMT**: Provide scores and metadata (see example format below)
   - **For Curriculum**: Provide grade level, skill areas, and score

5. **View evaluation prompts** (optional): Use the expandable sections at the top to view the evaluation prompts used for individual and batch modes

6. **Click "Generate & Evaluate"** to:
   - Generate the intervention/curriculum prompt
   - Generate the answer using the selected generator model
   - Evaluate the answer using the LLM judge

7. **View results**:
   - Generated prompt (Step 2)
   - Generated answer (Step 3)
   - **Evaluation metrics**:
     - Total Rating (1-10) - Average of Relevance and Clarity
     - Relevance Score (1-10)
     - Clarity Score (1-10)
     - Note: Consistency and Creativity scores are only available for batch evaluations
   - Pydantic validation status
   - Detailed LLM judge feedback
   - Expandable section to view the exact judge prompt used

8. **Check history** by toggling "Show Evaluation History" to view all past evaluations with summary statistics

## 🔗 SEAL API Integration

This tool can integrate with the SEAL API to fetch real intervention plans instead of generating them locally.

**📖 For detailed integration documentation, see [SEAL_INTEGRATION.md](SEAL_INTEGRATION.md)**

### Setup

1. **Start SEAL API** (in a separate terminal):
   ```bash
   cd /path/to/seal
   uvicorn app.main:app --reload
   ```

2. **In the Prompt-Eval-Tool UI**:
   - Check "Use SEAL API for generation" in the sidebar
   - Enter SEAL API URL (default: `http://localhost:8000`)
   - The health check will run automatically and cache the result
   - Click "🔄 Refresh" to manually re-check the health status

### Health Check Caching

The health check result is cached in Streamlit session state to improve performance and reliability:
- **First check**: Health check runs when you first check the checkbox
- **Subsequent runs**: Uses cached result (no re-checking on button clicks)
- **Manual refresh**: Click "🔄 Refresh" button to force a new health check
- **URL changes**: Automatically clears cache and re-checks when URL changes

### Benefits

- ✅ Fetch real SEAL outputs for evaluation
- ✅ Compare SEAL vs local generation
- ✅ Test SEAL API endpoints
- ✅ End-to-end workflow testing
- ✅ Automatic fallback to local generation if API is unavailable

### Troubleshooting

- **"SEAL API is not accessible"**: 
  - Verify SEAL is running: `curl http://localhost:8000/health`
  - Check the URL matches your SEAL instance
  - Click "🔄 Refresh" to re-check the health status
- **Health check passes but generation fails**: 
  - Check SEAL logs for errors
  - Verify the input data format matches SEAL's expected schema
  - The tool will automatically fall back to local generation

## SEAL Prompt Evaluation: Single vs Batch Modes

This project evaluates the two prompts from the SEAL repository across two modes:

- Single run: Qualitative scoring (LLM-as-a-Judge)
- Batch run (5 input-output pairs): Per-item qualitative scoring + batch-level metrics

### Single Run (Prompt A)

- Relevance (1–10): How relevant is the response to the given input and context?
- Clarity (1–10): How clear and understandable is the generated output?

### Batch Run (5 datasets)

- For each of the 5 input/output pairs: Relevance (1–10), Clarity (1–10)
- For the entire batch: Consistency (1–10), Creativity (1–10)

Use the following template to evaluate batch-level metrics (Consistency and Creativity):

```jsx
Following are the inputs and answer combinations for prompt 1

{input1} : {answer1}
{input2} : {answer2}
{input3} : {answer3}
{input4} : {answer4}
{input5} : {answer5}

Please evaluate and score these results for consistency and creativity

Consistency means..., how to score
Creativity means ..., how to score
```

### Completeness (Binary) – Structured Output + Pydantic

- Completeness: Does the output address all aspects of the prompt? All fields are present and within expected ranges.
- Primary enforcement: Gemini Structured Output (schema-constrained JSON)
- Fallback enforcement: Pydantic validation

**⚠️ Important Note:** Structured Output does not work well with this application. **Please keep the "Use Structured Output (Gemini)" checkbox unticked** and stick to Pydantic validation instead. Pydantic provides reliable validation and is the recommended approach for this tool.

If you check the structured output checkbox in the UI, a warning message will appear reminding you to keep it unticked.

### Batch Evaluation

1. **Prepare CSV file** with the following columns:
   - `type`: Either "emt" or "curriculum"
   - `input`: JSON string containing the input data

2. See `sample-input-dataset.csv` for example format

3. **Upload CSV** in the "Batch Evaluation" tab

4. **Click "Run Batch Evaluation"** to process all rows

5. **Download results** as CSV with all evaluation metrics

### Example Input Formats

**EMT Input:**
```json
{
  "scores": {
    "EMT1": [35.0, 40.0, 38.0, 42.0, 39.0],
    "EMT2": [75.0, 78.0, 80.0, 77.0, 79.0],
    "EMT3": [70.0, 72.0, 68.0, 71.0, 69.0],
    "EMT4": [65.0, 67.0, 70.0, 68.0, 66.0]
  },
  "metadata": {
    "class_id": "QUICK_TEST_1A",
    "deficient_area": "EMT1",
    "num_students": 25
  }
}
```

**Curriculum Input:**
```json
{
  "grade_level": "1",
  "skill_areas": ["emotional_awareness"],
  "score": 25.0
}
```

## 🤖 Gemini 2.5 Models

The app supports three Gemini 2.5 models, each optimized for different use cases:

### **Gemini 2.5 Pro** (`gemini-2.5-pro`)
- **Best for**: Complex tasks requiring detailed analysis
- **Strengths**: 
  - Handles large datasets
  - Long context windows (over 1 million tokens)
  - Provides comprehensive, detailed responses
- **Use cases**: Long-form content, research summaries, advanced coding help

### **Gemini 2.5 Flash** (`gemini-2.5-flash`) ⚡ *Recommended*
- **Best for**: Balanced performance and quality
- **Strengths**: 
  - Optimized for speed and cost-efficiency
  - Low latency responses
  - Good quality-to-speed ratio
- **Use cases**: Real-time applications, chat, summarization, interactive experiences

### **Gemini 2.5 Flash-Lite** (`gemini-2.5-flash-lite`)
- **Best for**: High-volume, high-speed tasks
- **Strengths**: 
  - Fastest model in the 2.5 series
  - Most cost-effective option
  - High throughput
- **Use cases**: Classification, sentiment analysis, high-scale operations

## 📊 CSV Output

All evaluations are automatically saved to `evaluations.csv` with the following columns:

- `timestamp` – When the evaluation was performed
- `batch_id` – Identifier for batch runs (same for all rows in a batch, `None` for individual evaluations)
- `row_type` – `item` for per-item rows, `batch_summary` for batch-level metrics
- `model` – Which generator model was used
- `temperature` – Temperature setting for the generator model
- `question` – The input context/question (prompt type and input data)
- `answer` – The model-generated answer
- `judge_feedback` – Detailed feedback from the LLM judge
- `judge_prompt` – The prompt sent to the LLM judge
- `total_rating(1-10)` – Overall rating from 1-10
- `validation_status` – Pydantic validation result (Valid ✅ or Invalid ❌)
- `relevance_score` – Relevance score from 1-10
- `clarity_score` – Clarity score from 1-10
- `consistency_score` – Consistency score from 1-10 (batch_summary rows only)
- `creativity_score` – Creativity score from 1-10 (batch_summary rows only)

## 🏗️ Project Structure

```
llm-judge/
├── app.py                  # Main Streamlit application
├── judge.py                # LLM-as-a-Judge evaluation logic
├── models.py               # Pydantic models for validation
├── logger.py               # CSV logging functionality
├── seal_client.py          # SEAL API client for fetching interventions
├── check_deprecated.py     # Deprecation checker utility
├── prompts/                # ⚠️ DEPRECATED - Use tilli_prompts package instead
│   ├── DEPRECATED.md      # Migration guide
│   ├── intervention.py    # (Old - not used)
│   └── curriculum.py      # (Old - not used)
├── schemas/                # ⚠️ DEPRECATED - Use tilli_prompts.schemas instead
│   ├── DEPRECATED.md      # Migration guide
│   ├── base.py            # (Old - not used)
│   └── curriculum.py      # (Old - not used)
├── tests/                  # Test suite
├── requirements.txt        # Python dependencies
├── evaluations.csv        # Evaluation log (generated)
├── sample-input-dataset.csv # Example CSV for batch evaluation
├── .env.example           # Example environment file
├── .gitignore             # Git ignore rules
├── README.md              # This file
└── PRD.md                 # Product requirements document
```

**⚠️ Important**: The `prompts/` and `schemas/` directories are deprecated. This project now uses the shared `tilli-prompts` package. See `SHARED_PACKAGE_INTEGRATION.md` for details.

## 🧪 Code Coverage

The project maintains **51% overall code coverage** with comprehensive test coverage for core business logic:

### Coverage Breakdown

| Module | Coverage | Status |
|--------|----------|--------|
| **Total** | **51%** | ✅ |
| `models.py` | 100% | ✅ Excellent |
| `prompts/curriculum.py` | 100% | ✅ Excellent |
| `prompts/intervention.py` | 100% | ✅ Excellent |
| `schemas/curriculum.py` | 100% | ✅ Excellent |
| `prompts/__init__.py` | 100% | ✅ Excellent |
| `logger.py` | 96% | ✅ Excellent |
| `schemas/base.py` | 85% | ✅ Good |
| `judge.py` | 71% | ✅ Good |
| `app.py` | 0% | ⚠️ UI Code (Streamlit) |

### Running Tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests with coverage
pytest

# View detailed coverage report
pytest --cov=. --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=. --cov-report=html
# Then open htmlcov/index.html in your browser
```

### Test Coverage Notes

- **Core business logic** (prompts, models, logger, judge) is well-tested with 71-100% coverage
- **UI code** (`app.py`) is not tested, which is standard for Streamlit applications
- The test suite focuses on testable business logic rather than UI interactions

## 🛠️ Customization

### Modify the Judge Prompt

Edit the evaluation prompts in `judge.py` to customize evaluation criteria and scoring dimensions:
- `EVALUATION_PROMPT_INDIVIDUAL` - Used for individual evaluations (Relevance & Clarity)
- `EVALUATION_PROMPT_BATCH_GUIDE` - Used for batch-level evaluations (Consistency & Creativity)
- `EVALUATION_PROMPT` - Available but not currently used in the application flow

### Change Validation Schema

Update the `ModelAnswer` class in `models.py` to match your expected answer structure.

### Customize Intervention Prompts

Modify `InterventionPrompt` class in `prompts/intervention.py` to:
- Update EMT strategies
- Change the base prompt template
- Adjust safety guidelines

### Customize Curriculum Prompts

Modify `CurriculumPrompt` class in `prompts/curriculum.py` to:
- Update available interventions
- Change curriculum data
- Adjust prompt templates

### Add New Models

Add more Gemini models to the `model_options` dictionary in `app.py` (sidebar section).

### Modify Evaluation Metrics

Update the evaluation prompts in `judge.py` (`EVALUATION_PROMPT_INDIVIDUAL` or `EVALUATION_PROMPT_BATCH_GUIDE`) and the score extraction functions to add or modify evaluation dimensions.

## 📝 License

MIT License - feel free to use and modify as needed.

## 🤝 Contributing

Feel free to submit issues and enhancement requests!
