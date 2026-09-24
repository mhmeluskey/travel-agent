---
name: document-travel-agent-components
description: 'Create and maintain component documentation for this travel-agent project. Use when documenting Python modules, Streamlit pages, LangGraph nodes, provider integrations, APIs, configuration, data flow, or debugging behavior such as missing trip fields.'
argument-hint: 'Which components should be documented?'
user-invocable: true
disable-model-invocation: false
---

# Document Travel-Agent Components

## Purpose

Produce accurate, maintainable documentation for every requested component in the travel-agent workspace. Documentation must explain what a component does, how data moves through it, what it depends on, how it fails, and how to verify it.

## Component Map

Use the repository as the source of truth. The current component groups are:

- `ui.py`: primary Streamlit trip-search page and form workflow.
- `pages/friendly_agent.py`: conversational Streamlit page that gathers trip details question by question.
- `app/graph.py`: LangGraph state, requirement extraction, validation, weather-first destination selection, flight search, ranking, and answer generation.
- `app/models.py`: trip-request schema and destination defaults/limits.
- `app/date_utils.py`: date parsing, typo correction, date-range normalization, and validation.
- `app/prompts.py`: extraction and final-answer prompt contracts.
- `app/providers/locations.py`: city, airport, and metro-code resolution.
- `app/providers/weather.py`: geocoding, forecast retrieval, and weather-quality evaluation.
- `app/providers/serpapi.py`: SerpApi Google Flights requests and round-trip parsing.
- `app/providers/ranking.py`: budget filtering and flight ordering.
- `app/main.py`: interactive command-line entry point.
- `app/api.py`: FastAPI health and search endpoints.

Update this map when the repository changes. Do not invent components that are not present in the workspace.

## Procedure

1. Identify the requested component files and read their neighboring callers, callees, models, prompts, and configuration references.
2. For each component, document:
   - responsibility and user-visible purpose;
   - public functions, classes, graph nodes, routes, or page interactions;
   - inputs, normalized values, outputs, and state keys;
   - dependencies, external services, environment variables, and side effects;
   - success path and important failure paths;
   - assumptions and constraints, including limits and date or currency rules;
   - a focused command or test that verifies the component.
3. Trace the component through one realistic flow. For the travel workflow, follow:
   `user input -> extraction -> validation -> weather -> destination selection -> flight search -> ranking -> answer`.
4. When documenting a bug, reproduce or inspect the exact value crossing the relevant boundary. Distinguish UI state, generated request text, structured extraction, validation, and provider calls. Do not claim that a UI fix works until the generated request and validation result have been checked.
5. For missing fields, inspect these in order:
   - the form value and its type;
   - the value stored in `st.session_state`;
   - the request text sent to the graph;
   - the structured `TripRequest` result;
   - the `validate_request` required-field check.
6. Include operational instructions for the component where useful: required `.env` values, dependency installation, startup command, endpoint or page URL, and external API limitations.
7. Keep documentation close to the code it describes. Prefer concise module docstrings, a component README, or a focused reference document rather than duplicating the same details in multiple places.
8. Preserve existing behavior while documenting. If documentation reveals a real defect, report it separately or make the smallest necessary fix with a focused validation step.

## Documentation Format

For each component, use this structure:

### `<component path>`

- **Role:** one-sentence responsibility.
- **Entry points:** functions, classes, graph nodes, routes, or UI controls.
- **Data contract:** important inputs, outputs, state keys, and normalization.
- **Dependencies:** internal modules, packages, services, and environment variables.
- **Behavior:** normal flow and meaningful branches.
- **Failure modes:** validation errors, provider errors, missing configuration, and fallback behavior.
- **Verification:** the narrowest useful test or run command.

For cross-component behavior, add a short sequence or table showing the handoff between components. Use exact state-key and field names from the code.

## Quality Checks

Before finishing:

- Confirm every documented path and symbol exists in the current workspace.
- Confirm names and field types match the implementation, especially `max_flight_price`, dates, currency, and `alternative_destinations`.
- Confirm environment-variable names and startup commands are current.
- Confirm external API constraints and fallback behavior are stated without implying that anything is booked.
- Run a syntax check, focused test, or endpoint/page smoke check when available.
- Mark any unverified external-service behavior as unverified instead of presenting it as successful.
- Avoid documenting implementation details that are not stable or relevant to a maintainer.

## Expected Output

Return the requested documentation plus a short verification note. If the request covers the whole project, document all components in the component map and finish with one end-to-end data-flow summary and the remaining test gaps.
