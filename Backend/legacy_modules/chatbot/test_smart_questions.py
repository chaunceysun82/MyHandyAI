#!/usr/bin/env python3
"""
Test script for the Smart Question Manager
Demonstrates how context-aware questions work for ANY DIY problem without additional API calls
"""

from smart_questions import SmartQuestionManager


def test_any_diy_problem():
    """Test that the system works with ANY DIY problem, not just specific ones"""
    print("🧪 Testing Generic DIY Problem Handling")
    print("=" * 60)

    # Initialize the smart question manager
    sqm = SmartQuestionManager()

    # Example: User wants to fix a broken window in the attic
    print("📋 Example: Broken window in attic")

    # Questions that might be returned by the LLM for ANY problem
    generic_questions = [
        {
            "id": "location",
            "text": "Where is the problem located?",
            "type": "free_text",
            "appliesIf": "",  # Always ask
            "collect": {"field": "location"}
        },
        {
            "id": "thing",
            "text": "What needs to be fixed?",
            "type": "free_text",
            "appliesIf": "",  # Always ask
            "collect": {"field": "thing"}
        },
        {
            "id": "symptoms",
            "text": "What's wrong with it? (describe the problem)",
            "type": "free_text",
            "appliesIf": "",  # Always ask
            "collect": {"field": "symptoms"}
        },
        {
            "id": "materials",
            "text": "What material is it made of?",
            "type": "free_text",
            "appliesIf": "",  # Always ask
            "collect": {"field": "materials.material_type"}
        },
        {
            "id": "access",
            "text": "Can you safely access the area?",
            "type": "yes_no",
            "appliesIf": "area_type == 'indoor'",  # Only ask for indoor problems
            "collect": {"field": "can_access"}
        },
        {
            "id": "weather",
            "text": "Is this exposed to weather?",
            "type": "yes_no",
            "appliesIf": "area_type == 'outdoor'",  # Only ask for outdoor problems
            "collect": {"field": "weather_exposed"}
        },
        {
            "id": "tools",
            "text": "Do you have basic tools (hammer, screwdriver, etc.)?",
            "type": "yes_no",
            "appliesIf": "",  # Always ask
            "collect": {"field": "tools_available.basic_tools"}
        },
        {
            "id": "experience",
            "text": "What's your experience level with this type of repair?",
            "type": "free_text",
            "appliesIf": "",  # Always ask
            "collect": {"field": "experience_level"}
        }
    ]

    # Initial triage state (minimal, from problem recognition)
    triage_state = {
        "domain": None,
        "system": None,
        "thing": None,
        "area_type": None,
        "location": None,
        "room": None,
        "materials": [],
        "symptoms": [],
        "dimensions": {},
        "tools_available": [],
        "hazards": []
    }

    print("📋 Generic Questions (before filtering):")
    for i, q in enumerate(generic_questions):
        print(f"  {i + 1}. {q['text']}")
        if q.get('appliesIf'):
            print(f"     (appliesIf: {q['appliesIf']})")

    print(f"\n🏠 Initial Triage State: {triage_state}")

    # Filter questions based on current context (no location specified yet)
    filtered_questions = sqm.filter_questions(generic_questions, triage_state, "broken_window")

    print(f"\n✅ Questions after filtering (no context yet):")
    for i, q in enumerate(filtered_questions):
        print(f"  {i + 1}. {q['text']}")

    # Simulate user answering: "attic"
    print(f"\n👤 User answers: 'attic'")

    location_question = filtered_questions[0]
    triage_state = sqm.apply_answer_to_state(location_question, "attic", triage_state)

    print(f"🏠 Updated Triage State: {triage_state}")

    # Now filter questions again with updated context
    filtered_questions_after = sqm.filter_questions(generic_questions, triage_state, "broken_window")

    print(f"\n✅ Questions after filtering (location = attic, indoor):")
    for i, q in enumerate(filtered_questions_after):
        print(f"  {i + 1}. {q['text']}")

    # Check that outdoor-specific questions are filtered out
    outdoor_questions = [q for q in filtered_questions_after if "weather" in q['text'].lower()]
    if not outdoor_questions:
        print(f"\n🎯 SUCCESS: Weather question correctly filtered out for indoor attic!")
    else:
        print(f"\n❌ FAILURE: Weather question not filtered out")

    # Simulate user answering: "broken window"
    print(f"\n👤 User answers: 'broken window'")

    thing_question = filtered_questions_after[1]
    triage_state = sqm.apply_answer_to_state(thing_question, "broken window", triage_state)

    print(f"🏠 Updated Triage State: {triage_state}")

    # Simulate user answering: "cracked glass, frame is loose"
    print(f"\n👤 User answers: 'cracked glass, frame is loose'")

    symptoms_question = filtered_questions_after[2]
    triage_state = sqm.apply_answer_to_state(symptoms_question, "cracked glass, frame is loose", triage_state)

    print(f"🏠 Updated Triage State: {triage_state}")

    return triage_state


def test_completely_different_problem():
    """Test with a completely different problem type"""
    print(f"\n\n🧪 Testing Completely Different Problem: Electrical Outlet")
    print("=" * 60)

    sqm = SmartQuestionManager()

    # Different set of questions for electrical work
    electrical_questions = [
        {
            "id": "location",
            "text": "Where is the outlet located?",
            "type": "free_text",
            "appliesIf": "",
            "collect": {"field": "location"}
        },
        {
            "id": "problem",
            "text": "What's happening with the outlet?",
            "type": "free_text",
            "appliesIf": "",
            "collect": {"field": "symptoms"}
        },
        {
            "id": "circuit",
            "text": "Is this affecting other outlets on the same circuit?",
            "type": "yes_no",
            "appliesIf": "domain == 'electrical'",
            "collect": {"field": "affects_circuit"}
        },
        {
            "id": "breaker",
            "text": "Have you checked the circuit breaker?",
            "type": "yes_no",
            "appliesIf": "domain == 'electrical'",
            "collect": {"field": "checked_breaker"}
        },
        {
            "id": "gfci",
            "text": "Is this a GFCI outlet (has reset/test buttons)?",
            "type": "yes_no",
            "appliesIf": "domain == 'electrical'",
            "collect": {"field": "is_gfci"}
        },
        {
            "id": "tools",
            "text": "Do you have a voltage tester or multimeter?",
            "type": "yes_no",
            "appliesIf": "",
            "collect": {"field": "tools_available.voltage_tester"}
        }
    ]

    # Initial triage state for electrical problem
    triage_state = {
        "domain": "electrical",
        "system": "wiring",
        "thing": "outlet",
        "area_type": "indoor",
        "location": None,
        "room": None,
        "materials": [],
        "symptoms": [],
        "dimensions": {},
        "tools_available": [],
        "hazards": []
    }

    print("📋 Electrical Questions:")
    for i, q in enumerate(electrical_questions):
        print(f"  {i + 1}. {q['text']}")

    # Filter questions
    filtered_questions = sqm.filter_questions(electrical_questions, triage_state, "electrical_outlet")

    print(f"\n✅ Questions after filtering:")
    for i, q in enumerate(filtered_questions):
        print(f"  {i + 1}. {q['text']}")

    # Simulate user answering: "kitchen"
    print(f"\n👤 User answers: 'kitchen'")

    location_question = filtered_questions[0]
    triage_state = sqm.apply_answer_to_state(location_question, "kitchen", triage_state)

    print(f"🏠 Updated Triage State: {triage_state}")

    # Simulate user answering: "no power, other outlets work"
    print(f"\n👤 User answers: 'no power, other outlets work'")

    problem_question = filtered_questions[1]
    triage_state = sqm.apply_answer_to_state(problem_question, "no power, other outlets work", triage_state)

    print(f"🏠 Updated Triage State: {triage_state}")

    return triage_state


def test_unknown_problem_type():
    """Test with a completely unknown problem type"""
    print(f"\n\n🧪 Testing Unknown Problem Type: 'weird noise in walls'")
    print("=" * 60)

    sqm = SmartQuestionManager()

    # Generic questions that work for ANY problem
    generic_questions = [
        {
            "id": "location",
            "text": "Where is this happening?",
            "type": "free_text",
            "appliesIf": "",
            "collect": {"field": "location"}
        },
        {
            "id": "description",
            "text": "Describe what you're experiencing",
            "type": "free_text",
            "appliesIf": "",
            "collect": {"field": "symptoms"}
        },
        {
            "id": "frequency",
            "text": "How often does this happen?",
            "type": "free_text",
            "appliesIf": "",
            "collect": {"field": "frequency"}
        },
        {
            "id": "access",
            "text": "Can you access the area where this is happening?",
            "type": "yes_no",
            "appliesIf": "",
            "collect": {"field": "can_access"}
        }
    ]

    # Minimal triage state for unknown problem
    triage_state = {
        "domain": None,
        "system": None,
        "thing": None,
        "area_type": None,
        "location": None,
        "room": None,
        "materials": [],
        "symptoms": [],
        "dimensions": {},
        "tools_available": [],
        "hazards": []
    }

    print("📋 Generic Questions for Unknown Problem:")
    for i, q in enumerate(generic_questions):
        print(f"  {i + 1}. {q['text']}")

    # Filter questions
    filtered_questions = sqm.filter_questions(generic_questions, triage_state, "unknown_problem")

    print(f"\n✅ Questions after filtering:")
    for i, q in enumerate(filtered_questions):
        print(f"  {i + 1}. {q['text']}")

    # Simulate user answering: "bedroom wall"
    print(f"\n👤 User answers: 'bedroom wall'")

    location_question = filtered_questions[0]
    triage_state = sqm.apply_answer_to_state(location_question, "bedroom wall", triage_state)

    print(f"🏠 Updated Triage State: {triage_state}")

    # Simulate user answering: "scratching sounds at night"
    print(f"\n👤 User answers: 'scratching sounds at night'")

    description_question = filtered_questions[1]
    triage_state = sqm.apply_answer_to_state(description_question, "scratching sounds at night", triage_state)

    print(f"🏠 Updated Triage State: {triage_state}")

    return triage_state


if __name__ == "__main__":
    print("🚀 Smart Question Manager - Generic DIY Problem Test Suite")
    print("=" * 80)
    print("This demonstrates how the system works with ANY DIY problem, not just specific ones!")

    # Test generic DIY problem handling
    window_state = test_any_diy_problem()

    # Test completely different problem type
    electrical_state = test_completely_different_problem()

    # Test unknown problem type
    unknown_state = test_unknown_problem_type()

    print(f"\n\n🎉 All tests completed!")
    print(f"Broken window triage state: {window_state}")
    print(f"Electrical outlet triage state: {electrical_state}")
    print(f"Unknown problem triage state: {unknown_state}")

    print(f"\n✨ Key Benefits:")
    print(f"✅ Works with ANY DIY problem type")
    print(f"✅ Automatically adapts questions based on context")
    print(f"✅ No hardcoded problem-specific logic")
    print(f"✅ Scales to new problem types without code changes")
    print(f"✅ Maintains context awareness across different domains")
