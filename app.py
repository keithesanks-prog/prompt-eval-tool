"""
LLM Evaluation Playground - Streamlit App
"""

import streamlit as st
import os
from dotenv import load_dotenv
from pydantic import ValidationError
import pandas as pd
import json
import time

from models import ModelAnswer
from judge import (
    configure_gemini,
    evaluate_with_gemini,
    generate_with_llm,
    EVALUATION_PROMPT_INDIVIDUAL,
    EVALUATION_PROMPT_BATCH_GUIDE,
    evaluate_batch_with_gemini,
)
from logger import log_evaluation, get_evaluation_history, log_batch_summary
from tilli_prompts import InterventionPrompt, CurriculumPrompt
from seal_client import SEALAPIClient
from tilli_prompts.schemas import InterventionRequest, CurriculumRequest

# Check for deprecated imports
try:
    from check_deprecated import check_deprecated_imports
    check_deprecated_imports()
except ImportError:
    pass  # check_deprecated.py not required


# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(page_title="LLM Evaluation Playground", page_icon="🧾", layout="wide")

# Title
st.title("🧾 LLM Evaluation Playground")
st.markdown("Evaluate model-generated outputs using LLM-as-a-Judge and Pydantic validation")

with st.expander("View the Main Evaluation Prompt (Individual Mode)"):
    st.code(EVALUATION_PROMPT_INDIVIDUAL, language="markdown")

with st.expander("View the Batch Evaluation Prompt (Consistency & Creativity)"):
    st.code(EVALUATION_PROMPT_BATCH_GUIDE, language="markdown")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    # API Key input
    api_key = st.text_input(
        "Google API Key",
        type="password",
        value=os.getenv("GOOGLE_API_KEY", ""),
        help="Enter your Google Gemini API key",
    )

    if api_key:
        try:
            configure_gemini(api_key)
            st.success("✅ API Key configured")
        except Exception as e:
            st.error(f"❌ Error configuring API: {str(e)}")
    else:
        st.warning("⚠️ Please enter your Google API Key")

    st.divider()

    # Model selection
    model_options = {
        "gemini-2.5-flash": "⚡ Flash - Balanced speed and quality (recommended)",
        "gemini-2.5-pro": "🧠 Pro - Complex tasks, detailed responses",
        "gemini-2.5-flash-lite": "🚀 Flash-Lite - Fastest, high-throughput",
    }

    model_name = st.selectbox(
        "Select Gemini Model",
        options=list(model_options.keys()),
        format_func=lambda x: model_options[x],
        help="""
        • **Pro**: Complex tasks, large datasets, 1M+ token context
        • **Flash**: Real-time apps, balanced quality/speed
        • **Flash-Lite**: High-speed, cost-effective classification
        """,
    )

    st.divider()

    # Temperature slider
    temperature = st.slider(
        "Set Judge Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.1,
        help="Controls the randomness of the judge's output. Higher is more creative.",
    )

    st.divider()

    st.header("🤖 Generator Config")

    generator_provider = st.selectbox(
        "Select Generator Provider",
        options=["gemini"],
        index=0,
        help="The LLM provider to use for generating the answer",
    )

    generator_model = st.selectbox(
        "Select Generator Model",
        options=list(model_options.keys()),
        format_func=lambda x: model_options[x],
        help="The model to use for generating the answer",
    )

    generator_temperature = st.slider(
        "Set Generator Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.1,
        help="Controls the randomness of the generator's output. Higher is more creative.",
    )

    use_structured_output = False

    # Show history toggle
    show_history = st.checkbox("Show Evaluation History", value=False)

    st.divider()

    # SEAL API Configuration
    st.header("🔗 SEAL API Integration")
    seal_api_url = st.text_input(
        "SEAL API URL",
        value=os.getenv("SEAL_API_URL", "http://localhost:8000"),
        help="Base URL of the SEAL API server",
    )
    use_seal_api = st.checkbox(
        "Use SEAL API for generation",
        value=False,
        help="Fetch intervention plans from SEAL API instead of generating locally",
    )
    
    # Initialize session state for health check caching
    if "seal_health_check" not in st.session_state:
        st.session_state.seal_health_check = {}
    if "seal_client" not in st.session_state:
        st.session_state.seal_client = None
    
    # Add refresh button for health check
    col_refresh1, col_refresh2 = st.columns([3, 1])
    with col_refresh2:
        refresh_health = st.button("🔄 Refresh", help="Refresh SEAL API health check")
    
    seal_client = None
    health_cache_key = f"health_{seal_api_url}"
    
    # Clear cache if refresh button clicked or URL changed
    if refresh_health or (health_cache_key in st.session_state.seal_health_check and 
                          st.session_state.seal_health_check[health_cache_key].get("url") != seal_api_url):
        if health_cache_key in st.session_state.seal_health_check:
            del st.session_state.seal_health_check[health_cache_key]
        st.session_state.seal_client = None
    
    if use_seal_api:
        # Check if URL changed or health check not cached
        if health_cache_key not in st.session_state.seal_health_check:
            # Perform health check and cache result
            seal_client = SEALAPIClient(base_url=seal_api_url)
            try:
                is_healthy = seal_client.health_check()
                st.session_state.seal_health_check[health_cache_key] = {
                    "healthy": is_healthy,
                    "timestamp": time.time(),
                    "url": seal_api_url
                }
                if is_healthy:
                    st.session_state.seal_client = seal_client
                else:
                    st.session_state.seal_client = None
            except Exception as e:
                st.session_state.seal_health_check[health_cache_key] = {
                    "healthy": False,
                    "timestamp": time.time(),
                    "error": str(e),
                    "url": seal_api_url
                }
                st.session_state.seal_client = None
        
        # Get cached health check result
        health_status = st.session_state.seal_health_check.get(health_cache_key, {})
        is_healthy = health_status.get("healthy", False)
        
        # Use cached client or create new one if healthy
        if is_healthy:
            if st.session_state.seal_client is None:
                st.session_state.seal_client = SEALAPIClient(base_url=seal_api_url)
            seal_client = st.session_state.seal_client
            st.success("✅ SEAL API is accessible")
        else:
            error_msg = health_status.get("error", "")
            if error_msg:
                st.warning(f"⚠️ SEAL API is not accessible: {error_msg}")
            else:
                st.warning("⚠️ SEAL API is not accessible. Check the URL and ensure SEAL is running.")
            # Don't disable use_seal_api here - let the generation code handle it
            seal_client = None
    else:
        # If checkbox is unchecked, clear the cached client
        st.session_state.seal_client = None

# Main content
individual_tab, batch_tab = st.tabs(["Individual Evaluation", "Batch Evaluation"])

with individual_tab:
    st.header("Step 1: Provide Input Data")

    col1, col2 = st.columns([1, 1])

    with col1:
        prompt_type = st.selectbox(
            "Select Prompt Type",
            options=["emt", "curriculum"],
            index=0,
            help="Select the type of intervention prompt to generate.",
        )

        # Example data to guide the user
        example_emt = {
            "scores": {
                "EMT1": [35.0, 40.0, 38.0, 42.0, 39.0],
                "EMT2": [75.0, 78.0, 80.0, 77.0, 79.0],
                "EMT3": [70.0, 72.0, 68.0, 71.0, 69.0],
                "EMT4": [65.0, 67.0, 70.0, 68.0, 66.0],
            },
            "metadata": {"class_id": "QUICK_TEST_1A", "deficient_area": "EMT1", "num_students": 25},
        }
        example_curriculum = {
            "grade_level": "1",
            "skill_areas": ["emotional_awareness"],
            "score": 25.0,
        }

        # Set default input based on prompt type
        if prompt_type == "emt":
            default_input = json.dumps(example_emt, indent=2)
        else:
            default_input = json.dumps(example_curriculum, indent=2)

        input_data_str = st.text_area(
            "Input Data (JSON format)",
            value=default_input,
            height=250,
            help="Paste the JSON input data for the selected prompt type.",
        )

        generate_button = st.button(
            "🚀 Generate & Evaluate", type="primary", use_container_width=True
        )

    with col2:
        st.header("Step 2: View Generated Prompt")
        generated_prompt_placeholder = st.empty()
        generated_prompt_placeholder.info(
            "The generated prompt will appear here after clicking the button."
        )

    st.divider()

    st.header("Step 3: Review Results")

    col3, col4 = st.columns([1, 1])

    with col3:
        st.subheader("🤖 Generated Answer")
        answer_placeholder = st.empty()
        answer_placeholder.info("The generated answer will appear here.")

    with col4:
        st.subheader("📊 Evaluation")
        results_placeholder = st.empty()
        results_placeholder.info("Evaluation results will appear here.")

    if generate_button:
        if not api_key:
            st.error("❌ Please enter your Google API Key in the sidebar")
        else:
            try:
                # Step 1: Parse input and generate prompt
                input_data = json.loads(input_data_str)
                prompt = ""

                if prompt_type == "emt":
                    # Calculate averages for EMT scores
                    scores = input_data.get("scores", {})
                    emt_averages = {k: sum(v) / len(v) for k, v in scores.items() if v}

                    prompt_data = {
                        "class_id": input_data.get("metadata", {}).get("class_id"),
                        "num_students": input_data.get("metadata", {}).get("num_students"),
                        "deficient_area": input_data.get("metadata", {}).get("deficient_area"),
                        "emt1_avg": emt_averages.get("EMT1", 0),
                        "emt2_avg": emt_averages.get("EMT2", 0),
                        "emt3_avg": emt_averages.get("EMT3", 0),
                        "emt4_avg": emt_averages.get("EMT4", 0),
                    }
                    prompt = InterventionPrompt.get_prompt(generator_provider, prompt_data)

                elif prompt_type == "curriculum":
                    prompt = CurriculumPrompt.get_prompt(generator_provider, input_data)

                with generated_prompt_placeholder.container():
                    with st.expander("📝 View Generated Prompt", expanded=True):
                        st.code(prompt, language="markdown")

                # Step 2: Generate answer - either from SEAL API or local LLM
                # Use cached client from session state if available
                active_seal_client = seal_client or st.session_state.get("seal_client")
                if use_seal_api and active_seal_client:
                    with st.spinner("Fetching from SEAL API..."):
                        try:
                            if prompt_type == "emt":
                                # Convert input to InterventionRequest
                                intervention_request = InterventionRequest(**input_data)
                                seal_response = active_seal_client.generate_intervention(intervention_request)
                                # Convert response to JSON string for evaluation
                                answer = json.dumps(seal_response, indent=2)
                            elif prompt_type == "curriculum":
                                # Convert input to CurriculumRequest
                                curriculum_request = CurriculumRequest(**input_data)
                                seal_response = active_seal_client.generate_curriculum(curriculum_request)
                                # Convert response to JSON string for evaluation
                                answer = json.dumps(seal_response, indent=2)
                            st.success("✅ Successfully fetched from SEAL API")
                        except Exception as e:
                            st.error(f"❌ Failed to fetch from SEAL API: {str(e)}")
                            st.info("Falling back to local generation...")
                            # Fallback to local generation
                            response_schema = None
                            answer = generate_with_llm(
                                prompt,
                                generator_provider,
                                generator_model,
                                generator_temperature,
                                response_schema=response_schema,
                            )
                else:
                    # Local generation
                    with st.spinner("Generating answer..."):
                        response_schema = None
                        answer = generate_with_llm(
                            prompt,
                            generator_provider,
                            generator_model,
                            generator_temperature,
                            response_schema=response_schema,
                        )

                with answer_placeholder.container():
                    st.markdown(answer)
                    # Completeness validation always via Pydantic
                    try:
                        ModelAnswer(content=answer)
                        validation_status = "Valid ✅"
                        st.success("Completeness: " + validation_status)
                    except ValidationError as e:
                        validation_status = f"Invalid ❌\n{str(e)}"
                        st.error("Completeness: " + validation_status)

                # Step 3: Evaluate the generated answer
                with st.spinner("Evaluating answer..."):
                    # For evaluation, the 'question' is the input data that generated the answer
                    question_for_judge = f"Prompt Type: {prompt_type}\nInput Data:\n{json.dumps(input_data, indent=2)}"

                    feedback, scores, judge_prompt = evaluate_with_gemini(
                        question_for_judge, answer, model_name, temperature, mode="individual"
                    )

                # Step 4: Display results and log
                with results_placeholder.container():
                    st.subheader("🤖 LLM Judge Feedback")
                    st.markdown(feedback)
                    st.divider()
                    cols = st.columns(2)
                    cols[0].metric(
                        "Relevance", f"{scores['relevance']}/10" if scores["relevance"] else "N/A"
                    )
                    cols[1].metric(
                        "Clarity", f"{scores['clarity']}/10" if scores["clarity"] else "N/A"
                    )

                    with st.expander("Show Judge Prompt"):
                        st.code(judge_prompt, language="markdown")

                # Log the evaluation
                log_evaluation(
                    model=generator_model,
                    temperature=generator_temperature,
                    question=question_for_judge,
                    answer=answer,
                    judge_feedback=feedback,
                    judge_prompt=judge_prompt,
                    total_rating=scores["total"],
                    validation_status=validation_status,
                    relevance_score=scores["relevance"],
                    clarity_score=scores["clarity"],
                    consistency_score=scores["consistency"],
                    creativity_score=scores["creativity"],
                    batch_id=None,
                    row_type="item",
                )
                st.success("✅ Results saved to evaluations.csv")

            except json.JSONDecodeError:
                st.error("❌ Invalid JSON format in Input Data.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")


with batch_tab:
    st.header("📤 Batch Evaluation from CSV")

    uploaded_file = st.file_uploader(
        "Upload a CSV file with 'type' and 'input' columns (see sample-input-dataset.csv)",
        type="csv",
    )

    batch_evaluate_button = st.button(
        "🚀 Run Batch Evaluation", type="primary", use_container_width=True
    )

    if batch_evaluate_button and uploaded_file:  # noqa: C901
        if not api_key:
            st.error("❌ Please enter your Google API Key in the sidebar")
        else:
            try:
                input_df = pd.read_csv(uploaded_file)
                if "type" not in input_df.columns or "input" not in input_df.columns:
                    st.error("❌ CSV must contain 'type' and 'input' columns.")
                else:
                    results = []
                    progress_bar = st.progress(0)
                    total_rows = len(input_df)

                    batch_id = str(int(time.time()))
                    batch_pairs = []
                    for index, row in input_df.iterrows():
                        with st.spinner(f"Processing row {index + 1}/{total_rows}..."):
                            try:
                                # Step 1: Generate prompt
                                input_data = json.loads(row["input"])
                                prompt = ""
                                prompt_type = row["type"]

                                if prompt_type == "emt":
                                    scores = input_data.get("scores", {})
                                    emt_averages = {
                                        k: sum(v) / len(v) for k, v in scores.items() if v
                                    }
                                    prompt_data = {
                                        "class_id": input_data.get("metadata", {}).get("class_id"),
                                        "num_students": input_data.get("metadata", {}).get(
                                            "num_students"
                                        ),
                                        "deficient_area": input_data.get("metadata", {}).get(
                                            "deficient_area"
                                        ),
                                        "emt1_avg": emt_averages.get("EMT1", 0),
                                        "emt2_avg": emt_averages.get("EMT2", 0),
                                        "emt3_avg": emt_averages.get("EMT3", 0),
                                        "emt4_avg": emt_averages.get("EMT4", 0),
                                    }
                                    prompt = InterventionPrompt.get_prompt(
                                        generator_provider, prompt_data
                                    )
                                elif prompt_type == "curriculum":
                                    prompt = CurriculumPrompt.get_prompt(
                                        generator_provider, input_data
                                    )

                                # Step 2: Generate answer (Structured Output disabled)
                                response_schema = None
                                answer = generate_with_llm(
                                    prompt,
                                    generator_provider,
                                    generator_model,
                                    generator_temperature,
                                    response_schema=response_schema,
                                )
                                time.sleep(1)  # To avoid hitting API rate limits

                                # Step 3: Per-item judging (Relevance & Clarity only)
                                question_for_judge = (
                                    f"Prompt Type: {prompt_type}\nInput Data:\n{row['input']}"
                                )
                                feedback, scores, judge_prompt = evaluate_with_gemini(
                                    question_for_judge,
                                    answer,
                                    model_name,
                                    temperature,
                                    mode="individual",
                                )

                                # Step 4: Completeness validation always via Pydantic
                                try:
                                    ModelAnswer(content=answer)
                                    validation_status = "Valid"
                                except ValidationError as e:
                                    validation_status = f"Invalid: {e}"

                                result_row = {
                                    "type": prompt_type,
                                    "input": row["input"],
                                    "generated_answer": answer,
                                    "judge_feedback": feedback,
                                    "total_score": scores.get("total"),
                                    "relevance_score": scores.get("relevance"),
                                    "clarity_score": scores.get("clarity"),
                                    "validation_status": validation_status,
                                    "generator_model": generator_model,
                                    "judge_model": model_name,
                                }
                                results.append(result_row)
                                # Log per-item row with batch_id
                                log_evaluation(
                                    model=generator_model,
                                    temperature=generator_temperature,
                                    question=question_for_judge,
                                    answer=answer,
                                    judge_feedback=feedback,
                                    judge_prompt=judge_prompt,
                                    total_rating=scores.get("total"),
                                    validation_status=validation_status,
                                    relevance_score=scores.get("relevance"),
                                    clarity_score=scores.get("clarity"),
                                    consistency_score=None,
                                    creativity_score=None,
                                    batch_id=batch_id,
                                    row_type="item",
                                )

                                batch_pairs.append((row["input"], answer))
                            except Exception as row_error:
                                results.append(
                                    {
                                        "type": row.get("type", "unknown"),
                                        "input": row.get("input", "error"),
                                        "generated_answer": f"ERROR: {row_error}",
                                        "judge_feedback": "N/A",
                                        "total_score": None,
                                        "relevance_score": None,
                                        "clarity_score": None,
                                        "consistency_score": None,
                                        "creativity_score": None,
                                        "validation_status": "Error",
                                        "generator_model": generator_model,
                                        "judge_model": model_name,
                                    }
                                )

                        progress_bar.progress((index + 1) / total_rows)

                    results_df = pd.DataFrame(results)
                    # Batch-level evaluation: Consistency & Creativity
                    try:
                        batch_feedback, batch_scores, batch_prompt = evaluate_batch_with_gemini(
                            batch_pairs, model_name, temperature
                        )
                        st.subheader("🧪 Batch Metrics")
                        cols = st.columns(2)
                        cols[0].metric("Consistency (1-10)", batch_scores.get("consistency", "N/A"))
                        cols[1].metric("Creativity (1-10)", batch_scores.get("creativity", "N/A"))

                        with st.expander("Show Batch Feedback"):
                            st.markdown(batch_feedback)

                        with st.expander("Show Batch Judge Prompt"):
                            st.code(batch_prompt, language="markdown")
                        # Log batch summary row
                        log_batch_summary(
                            model=generator_model,
                            temperature=generator_temperature,
                            judge_feedback=batch_feedback,
                            judge_prompt=batch_prompt,
                            consistency_score=batch_scores.get("consistency"),
                            creativity_score=batch_scores.get("creativity"),
                            batch_id=batch_id,
                        )
                    except Exception as e:
                        st.warning(f"Batch-level evaluation failed: {e}")
                    st.success("✅ Batch evaluation complete!")
                    st.dataframe(results_df)

                    csv_results = results_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Results CSV",
                        data=csv_results,
                        file_name="batch_evaluation_results.csv",
                        mime="text/csv",
                    )

            except Exception as e:
                st.error(f"An error occurred during batch processing: {e}")

# Show evaluation history if toggled
if show_history:
    st.divider()
    st.header("📚 Evaluation History")

    history_df = get_evaluation_history()

    if not history_df.empty:
        # Display summary metrics
        if (
            "relevance_score" in history_df.columns
            and not history_df["relevance_score"].dropna().empty
        ):
            cols = st.columns(5)
        else:
            cols = st.columns(3)

        with cols[0]:
            st.metric("Total Evaluations", len(history_df))

        with cols[1]:
            st.metric(
                "Avg Rating (1-10)", f"{history_df['total_rating(1-10)'].dropna().mean():.2f}"
            )
            st.metric(
                "Valid Responses",
                f"{history_df['validation_status'].apply(lambda x: 'Valid' in str(x)).sum()} / {len(history_df)}",
            )

        with cols[2]:
            st.metric("Avg Relevance", f"{history_df['relevance_score'].dropna().mean():.2f}")
            st.metric("Avg Clarity", f"{history_df['clarity_score'].dropna().mean():.2f}")

        if len(cols) == 5:
            with cols[3]:
                st.metric(
                    "Avg Consistency", f"{history_df['consistency_score'].dropna().mean():.2f}"
                )
                st.metric("Avg Creativity", f"{history_df['creativity_score'].dropna().mean():.2f}")

            with cols[4]:
                models_used = history_df["model"].nunique()
                st.metric("Models Used", models_used)
        else:
            with cols[3]:
                models_used = history_df["model"].nunique()
                st.metric("Models Used", models_used)

        st.divider()

        # Display the dataframe
        st.dataframe(history_df, use_container_width=True, hide_index=True)

        # Download button
        csv_data = history_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV", data=csv_data, file_name="evaluations.csv", mime="text/csv"
        )
    else:
        st.info("No evaluation history found. Run some evaluations to see history here.")

# Footer
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 0.9em;'>
    💡 Tip: Configure your GOOGLE_API_KEY in a .env file for automatic loading
    </div>
    """,
    unsafe_allow_html=True,
)
