from typing import List, Dict, Any, Optional

from langchain_core.messages import HumanMessage, AIMessage


def extract_qa_pairs_from_messages(messages: List[Any]) -> tuple[List[str], Dict[str, str], Optional[str]]:
    """
    Extract questions and answers from conversation messages.

    Returns:
        tuple: (questions_list, answers_dict, image_analysis)
    """
    questions: List[str] = []
    answers: Dict[str, str] = {}
    image_analysis = None

    # Track conversation flow: skip initial greeting and first user message
    skip_initial = True
    last_question_index = -1

    for i, msg in enumerate(messages):
        # Skip system messages and tool calls
        msg_type = getattr(msg, 'type', None) or (type(msg).__name__ if hasattr(msg, '__class__') else '')
        if msg_type in ['system', 'tool']:
            continue

        # Get message content
        content = getattr(msg, 'content', '')
        if isinstance(content, list):
            # Extract text from multimodal content
            text_content = ''
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        text_content = item.get('text', '')
                    elif item.get('type') == 'image':
                        # Note: image analysis would be in AI responses, not extracted here
                        pass
            content = text_content
        else:
            content = str(content) if content else ""

        # Human message - could be an answer
        is_human = isinstance(msg, HumanMessage) or msg_type == 'human'
        # AI message - could contain a question
        is_ai = isinstance(msg, AIMessage) or msg_type == 'ai'

        if is_human:
            # Skip the very first user message (initial description, handled by store_home_issue)
            if skip_initial:
                skip_initial = False
                continue

            # If we have questions and this follows an AI message, it's likely an answer
            if last_question_index >= 0 and last_question_index < len(questions):
                answers[str(last_question_index)] = content
                last_question_index = -1  # Reset after storing answer

        elif is_ai:
            # Check if this is a question (not a tool call response)
            has_tool_calls = hasattr(msg, 'tool_calls') and msg.tool_calls
            if not has_tool_calls and content:
                # Heuristic: question if ends with '?' or contains question words
                is_question = (
                        '?' in content or
                        any(word in content.lower() for word in [
                            'what', 'where', 'when', 'how', 'which', 'who',
                            'do you', 'can you', 'have you', 'did you',
                            'are you', 'is it', 'does it'
                        ])
                )

                if is_question:
                    questions.append(content)
                    last_question_index = len(questions) - 1
                else:
                    # Not a question, might be a summary or confirmation request
                    # Reset question tracking
                    last_question_index = -1

    return questions, answers, image_analysis
