import streamlit as st
import importlib
import sys
import os
import builtins
from types import SimpleNamespace
from typing import Any, Dict, List
import traceback
import inspect

MODULE_NAME = "diy_flow"
INITIAL_NODE = "Greetings"

st.set_page_config(page_title="DIY Multi-Agent Chat", layout="wide")

def try_import_module(name: str):
    try:
        if name in sys.modules:
            return importlib.reload(sys.modules[name])
        return importlib.import_module(name)
    except Exception as e:
        return None


def safe_call_node(node_fn, state):
    """Call the node function while monkey-patching input() to use the UI provided input.
    The UI stores the latest_user_input in session state (if any). If a node function calls input()
    it will receive that value once (consumed) and then the stored input is cleared so subsequent
    nodes don't reuse the same input unintentionally.
    """
    # save original
    orig_input = builtins.input

    def ui_input(prompt: str = ""):
        # return what UI stored for the next user input, then clear it so it's used only once
        val = st.session_state.get("_next_user_input", None)
        # consume the value so future calls won't reuse it
        st.session_state._next_user_input = None
        if val is None:
            return ""
        return val

    try:
        builtins.input = ui_input
        result = node_fn(state)
    except Exception as e:
        st.error("Error while executing node: " + str(e))
        st.exception(traceback.format_exc())
        result = {}
    finally:
        builtins.input = orig_input
    return result


def append_messages_from_result(result):
    """The node functions commonly return {'messages_history': [AIMessage(content) or HumanMessage(...) ]}
    We'll convert those message objects into simple (role, text) dicts and append to session history.
    """
    msgs = result.get("messages_history")
    if not msgs:
        return
    hist = st.session_state.messages_history
    for m in msgs:
        # if it's a LangChain message object, try to access .content and .type or .__class__.__name__
        try:
            content = getattr(m, "content", None) or getattr(m, "message", None) or str(m)
            cls_name = m.__class__.__name__
            role = "ai" if "AI" in cls_name or "ai" in cls_name.lower() else ("human" if "Human" in cls_name or "human" in cls_name.lower() else "ai")
        except Exception:
            content = str(m)
            role = "ai"
        hist.append({"role": role, "text": content})
    st.session_state.messages_history = hist


# ---- Initialize session state ----
if "loaded_module" not in st.session_state:
    st.session_state.loaded_module = None
if "messages_history" not in st.session_state:
    st.session_state.messages_history = []
if "current_node" not in st.session_state:
    st.session_state.current_node = INITIAL_NODE
if "state" not in st.session_state:
    # build initial state similar to DIYState typed dict in user's code
    st.session_state.state = {
        'message': "",
        'messages_history': [],
        'problem_classified': "",
        'diy_classified': "",
        'initial_problem': "",
        'fields_to_gather': [],
        'text_classified': "",
        'cant_understand': False,
        'answer_relevant': "",
        'information_retrieved': "",
        'fields_asked': "",
        'question_generated': "",
        'summary': ""
    }
if "_next_user_input" not in st.session_state:
    st.session_state._next_user_input = None
if "auto_run" not in st.session_state:
    st.session_state.auto_run = False

# ---- Load user's module ----

def compute_next_node(current_node: str, state: Dict[str, Any]):
    """Determine the next node given the current node and (optionally) the user's module.
    This function tries to call the user's check_* functions if the user's module is available in
    session state; otherwise it falls back to the static graph mapping used in the original UI.
    """
    # Try to get the loaded module object (if available)
    mod = None
    loaded_name = st.session_state.get('loaded_module')
    if loaded_name:
        try:
            # prefer a reload so the module reflects latest code
            if loaded_name in sys.modules:
                mod = importlib.reload(sys.modules[loaded_name])
            else:
                mod = importlib.import_module(loaded_name)
        except Exception:
            # leave mod as None if import/reload fails
            mod = None

    # If we have the user's module, prefer calling its check_* functions (they expect state)
    try:
        if mod is not None:
            if current_node == 'Problem Classifier' and hasattr(mod, 'check_problem'):
                return mod.check_problem(state)
            if current_node == 'Text Classifier' and hasattr(mod, 'check_text'):
                return mod.check_text(state)
            if current_node == 'Answer Relevancy Checker Agent' and hasattr(mod, 'check_text_answer_relevancy'):
                return mod.check_text_answer_relevancy(state)
            if current_node == 'Information Retrieval Agent' and hasattr(mod, 'check_information_retrieval'):
                return mod.check_information_retrieval(state)
    except Exception:
        # If the user's check function raises, ignore and fall back to mapping below
        pass

    # Fallback static mapping (mirrors your original StateGraph)
    mapping = {
        'START': 'Greetings',
        'Greetings': 'Problem Information',
        'Problem Information': 'Problem Classifier',
        'Data Fields Generator': 'AI Field Gathering',
        'AI Field Gathering': 'Text Answer',
        'Text Answer': 'Text Classifier',
        'Skip Question': 'AI Field Gathering',
        'Cant Answer': 'AI Field Gathering',
        'Summary Generation': 'END'
    }
    return mapping.get(current_node, None)


col1, col2 = st.columns([3,1])
with col2:
    st.markdown("**Module loader & controls**")
    module_name = st.text_input("Module name (python file without .py)", value=MODULE_NAME)
    if st.button("Load / Reload module"):
        mod = try_import_module(module_name)
        if mod is None:
            st.error(f"Could not import module '{module_name}'. Make sure the file {module_name}.py is in the same folder and has no import errors.")
            st.session_state.loaded_module = None
        else:
            st.success(f"Loaded module: {module_name}")
            st.session_state.loaded_module = module_name
            st.experimental_rerun()

    st.markdown("---")
    st.write("**Quick actions**")
    if st.button("Reset conversation"):
        st.session_state.messages_history = []
        st.session_state.state = {
            'message': "",
            'messages_history': [],
            'problem_classified': "",
            'diy_classified': "",
            'initial_problem': "",
            'fields_to_gather': [],
            'text_classified': "",
            'cant_understand': False,
            'answer_relevant': "",
            'information_retrieved': "",
            'fields_asked': "",
            'question_generated': "",
            'summary': ""
        }
        st.session_state.current_node = INITIAL_NODE
        st.experimental_rerun()

    st.checkbox("Auto-run when stepping", key="auto_run")
    st.markdown("\n---\nMake sure your environment (API keys) is set before using LLM nodes.")

# Show left area UI
with col1:
    st.title("DIY Multi-Agent Chat — Streamlit UI")
    st.markdown("This UI allows stepping through the nodes of your workflow and provides the user inputs when a node expects them.")

    # show state summary at top
    with st.expander("Conversation / Messages (expand to view)", expanded=True):
        for msg in st.session_state.messages_history:
            if msg['role'] == 'ai':
                st.markdown(f"**AI**: {msg['text']}")
            else:
                st.markdown(f"**User**: {msg['text']}")

    st.markdown("---")
    st.subheader("Current Node: "+st.session_state.current_node)

    # Display important pieces of state
    st.markdown("**Gathered Fields**")
    st.write(st.session_state.state.get('fields_to_gather', []))

    st.markdown("**Key State**")
    keycols = st.columns(3)
    keycols[0].write(f"problem_classified: {st.session_state.state.get('problem_classified')}")
    keycols[1].write(f"diy_classified: {st.session_state.state.get('diy_classified')}")
    keycols[2].write(f"text_classified: {st.session_state.state.get('text_classified')}")

    st.markdown("---")

    with st.expander("Details: classifications & collected info", expanded=False):
        st.subheader("Classification & Collected Information")
        st.write("**Problem classified:**", st.session_state.state.get('problem_classified'))
        st.write("**DIY classified:**", st.session_state.state.get('diy_classified'))
        st.write("**Fields to gather:**")
        st.json(st.session_state.state.get('fields_to_gather'))
        st.write("**Fields asked:**", st.session_state.state.get('fields_asked'))
        st.write("**Question generated:**", st.session_state.state.get('question_generated'))
        st.write("**Information retrieved status:**", st.session_state.state.get('information_retrieved'))
        st.write("**Summary:**")
        st.write(st.session_state.state.get('summary'))

    st.markdown("---")
    # Input area for the *next* user input that will be used by nodes that call input()
    user_text = st.text_input("Enter user text for the next question/input (this will be used when a node calls input())", key="user_text_input")
    if st.button("Set next user input"):
        st.session_state._next_user_input = user_text
        st.success("Next user input set")

    st.markdown("---")

    # Load module object
    mod = None
    if st.session_state.loaded_module is not None:
        mod = try_import_module(st.session_state.loaded_module)
    else:
        # try to import with default provided name (do not auto-reload here)
        mod = try_import_module(module_name)
        if mod is not None:
            st.session_state.loaded_module = module_name

    if mod is None:
        st.warning("User module not loaded. Please load your module file containing the workflow and node functions.")
        st.stop()

    # map node names to functions from user's module
    node_map = {
        'Greetings': getattr(mod, 'greetings', None),
        'Problem Information': getattr(mod, 'problem_information', None),
        'Problem Classifier': getattr(mod, 'problem_classifier', None),
        'Data Fields Generator': getattr(mod, 'data_fields_generator', None),
        'AI Field Gathering': getattr(mod, 'ai_field_gathering', None),
        'Text Answer': getattr(mod, 'text_answer', None),
        'Text Classifier': getattr(mod, 'text_classifier', None),
        'Skip Question': getattr(mod, 'skip_question', None),
        'Cant Answer': getattr(mod, 'cant_answer', None),
        'Answer Relevancy Checker Agent': getattr(mod, 'answer_relevancy_checker_agent', None),
        'Information Retrieval Agent': getattr(mod, 'information_retrieval_agent', None),
        'Summary Generation': getattr(mod, 'summary_generation', None),
    }

    # If the UI is at START (no node function) auto-advance to the first real node defined by the graph
    # and attempt to run the Greetings node once to sync UI with any greeting printed to the terminal
    if st.session_state.current_node == 'START':
        nxt = compute_next_node('START', st.session_state.state)
        if nxt and nxt != 'START':
            st.session_state.current_node = nxt
            # Only call the greetings node automatically if there is no message history yet
            if st.session_state.messages_history == [] and node_map.get(nxt):
                try:
                    res = safe_call_node(node_map.get(nxt), st.session_state.state)
                    if isinstance(res, dict):
                        for k, v in res.items():
                            if k == 'messages_history':
                                append_messages_from_result({'messages_history': v})
                            elif k == 'message':
                                st.session_state.messages_history.append({'role': 'human', 'text': v})
                                st.session_state.state['message'] = v
                            else:
                                st.session_state.state[k] = v
                    # advance one step after greeting
                    after = compute_next_node(nxt, st.session_state.state)
                    if after:
                        st.session_state.current_node = after
                except Exception:
                    # On any failure, leave the current_node set to nxt so user can Step
                    st.warning('Auto-run of greetings failed; you can press Step to continue.')

    # confirm all nodes are present
    # Auto-progress: if enabled, the app will run nodes automatically until a node requires user input.
    def node_requires_input(node_fn):
        try:
            src = inspect.getsource(node_fn)
            return ("input(" in src or "input (" in src)
        except Exception:
            return False

    # Auto-run trigger: run automatically when the module is loaded or when user provides input
    if st.session_state.get('auto_progress', True):
        loop_limit = 200
        count = 0
        progressed = False
        while st.session_state.current_node != 'END' and count < loop_limit:
            cur = st.session_state.current_node
            node_fn = node_map.get(cur)
            # If no node function, just advance via mapping
            if node_fn is None:
                nxt = compute_next_node(cur, st.session_state.state)
                if nxt is None or nxt == cur:
                    break
                st.session_state.current_node = nxt
                count += 1
                progressed = True
                continue

            # If node expects input and no input is set, pause here
            if node_requires_input(node_fn) and not st.session_state._next_user_input:
                break

            # Otherwise call the node
            res = safe_call_node(node_fn, st.session_state.state)
            if isinstance(res, dict):
                for k, v in res.items():
                    if k == 'messages_history':
                        append_messages_from_result({'messages_history': v})
                    elif k == 'message':
                        # append the human message that came from input()
                        st.session_state.messages_history.append({'role': 'human', 'text': v})
                        st.session_state.state['message'] = v
                    else:
                        st.session_state.state[k] = v

            nxt = compute_next_node(cur, st.session_state.state)
            if nxt is None:
                break
            st.session_state.current_node = nxt
            count += 1
            progressed = True

        if progressed:
            # re-render to show updates
            st.experimental_rerun()

    # small control to enable/disable auto progression
    st.checkbox("Auto-progress through nodes (pause for input)", value=True, key='auto_progress')
    missing = [k for k,v in node_map.items() if v is None]
    if missing:
        st.error("The following node functions are missing in your module: " + ", ".join(missing))
        st.stop()

    # Step execution logic
    def compute_next_node(current_node: str, state: Dict[str, Any]):
        # conditional nodes use the check_* functions defined in user's module
        if current_node == 'Problem Classifier':
            return mod.check_problem(state)
        if current_node == 'Text Classifier':
            return mod.check_text(state)
        if current_node == 'Answer Relevancy Checker Agent':
            return mod.check_text_answer_relevancy(state)
        if current_node == 'Information Retrieval Agent':
            return mod.check_information_retrieval(state)

        # fixed transitions based on original graph
        mapping = {
            'START': 'Greetings',
            'Greetings': 'Problem Information',
            'Problem Information': 'Problem Classifier',
            'Data Fields Generator': 'AI Field Gathering',
            'AI Field Gathering': 'Text Answer',
            'Text Answer': 'Text Classifier',
            'Skip Question': 'AI Field Gathering',
            'Cant Answer': 'AI Field Gathering',
            'Summary Generation': 'END'
        }
        return mapping.get(current_node, None)

    # Step button
    step_col1, step_col2, step_col3 = st.columns([1,1,1])
    with step_col1:
        if st.button("Step"):
            cur = st.session_state.current_node
            st.session_state._last_step_node = cur
            st.session_state.status = "Running node: " + cur
            node_fn = node_map.get(cur)
            if node_fn is None:
                # try to advance using the graph mapping (handles START -> Greetings and similar)
                nxt = compute_next_node(cur, st.session_state.state)
                if nxt and nxt != cur:
                    st.session_state.current_node = nxt
                    st.success(f"Advanced from {cur} to {nxt}")
                    st.experimental_rerun()
                else:
                    st.error("No function available for node: " + cur)
            else:
                # If the node's source contains input() and the UI has no next user input, pause and ask user to provide input
                try:
                    source = inspect.getsource(node_fn)
                except Exception:
                    source = ""
                if ("input(" in source or "input (" in source) and not st.session_state._next_user_input:
                    st.warning("This node expects user input. Please set the 'next user input' field and press Step.")
                else:
                    res = safe_call_node(node_fn, st.session_state.state)
                    # update state with returned keys
                    if isinstance(res, dict):
                        for k,v in res.items():
                            # special handling for messages_history
                            if k == 'messages_history':
                                append_messages_from_result({'messages_history': v})
                            elif k == 'message':
                                # this is a direct user message — append to history
                                st.session_state.messages_history.append({'role':'human','text': v})
                                st.session_state.state['message'] = v
                            else:
                                st.session_state.state[k] = v

                    # compute next
                    nxt = compute_next_node(cur, st.session_state.state)
                    if isinstance(nxt, dict):
                        # Some check functions in the original graph returned mapping keys; but in our module they return a string
                        # Fallback: choose first mapping value
                        try:
                            nxt = list(nxt.values())[0]
                        except Exception:
                            nxt = None
                    st.session_state.current_node = nxt or st.session_state.current_node
                    st.success(f"Node {cur} executed. Next: {st.session_state.current_node}")
                    # clear the stored next user input only if it was used
                    st.session_state._next_user_input = None
                    st.experimental_rerun()

    with step_col2:
        if st.button("Auto-step until input"):
            # Run nodes automatically until a node requires user input or END is reached
            loop_limit = st.number_input("Auto-step loop limit", min_value=1, max_value=500, value=50)
            count = 0
            paused_for_input = False
            while st.session_state.current_node != 'END' and count < loop_limit:
                cur = st.session_state.current_node
                node_fn = node_map.get(cur)
                if node_fn is None:
                    nxt = compute_next_node(cur, st.session_state.state)
                    if nxt is None or nxt == cur:
                        break
                    st.session_state.current_node = nxt
                    count += 1
                    continue

                # inspect node to see if it asks for input()
                try:
                    source = inspect.getsource(node_fn)
                except Exception:
                    source = ""
                if ("input(" in source or "input (" in source) and not st.session_state._next_user_input:
                    # pause here and ask user to enter the required input
                    st.warning(f"Node '{cur}' requires user input. Please set the 'next user input' box and press Auto-step again.")
                    paused_for_input = True
                    break

                res = safe_call_node(node_fn, st.session_state.state)
                if isinstance(res, dict):
                    for k,v in res.items():
                        if k == 'messages_history':
                            append_messages_from_result({'messages_history': v})
                        elif k == 'message':
                            st.session_state.messages_history.append({'role':'human','text': v})
                            st.session_state.state['message'] = v
                        else:
                            st.session_state.state[k] = v

                nxt = compute_next_node(cur, st.session_state.state)
                if nxt is None:
                    st.warning(f"Stopped: no mapping from node {cur}")
                    break
                st.session_state.current_node = nxt
                count += 1

            if not paused_for_input:
                st.success("Auto-step run completed or reached loop limit.")
            st.experimental_rerun()

    with step_col3:
        if st.button("Run to End (caution)"):
            # simple loop that runs steps until node becomes END or loop limit reached
            loop_limit = st.number_input("Loop limit", min_value=1, max_value=200, value=20)
            count = 0
            while st.session_state.current_node != 'END' and count < loop_limit:
                cur = st.session_state.current_node
                node_fn = node_map.get(cur)
                if node_fn is None:
                    # try computing next only
                    nxt = compute_next_node(cur, st.session_state.state)
                    if nxt is None:
                        st.warning("No next node found from " + str(cur))
                        break
                    st.session_state.current_node = nxt
                    count += 1
                    continue
                # inspect node for input requirement
                try:
                    source = inspect.getsource(node_fn)
                except Exception:
                    source = ""
                if ("input(" in source or "input (" in source) and not st.session_state._next_user_input:
                    st.warning(f"Node '{cur}' requires user input. Please set the 'next user input' box and press Run to End again.")
                    break
                res = safe_call_node(node_fn, st.session_state.state)
                if isinstance(res, dict):
                    for k,v in res.items():
                        if k == 'messages_history':
                            append_messages_from_result({'messages_history': v})
                        elif k == 'message':
                            st.session_state.messages_history.append({'role':'human','text': v})
                            st.session_state.state['message'] = v
                        else:
                            st.session_state.state[k] = v
                nxt = compute_next_node(cur, st.session_state.state)
                if nxt is None:
                    st.warning(f"Stopped: no mapping from node {cur}")
                    break
                st.session_state.current_node = nxt
                count += 1
            st.experimental_rerun()

    if st.button("Show state as JSON"):
        st.json(st.session_state.state)

    st.markdown("---")

    # summary area
    with st.expander("Summary / Final output", expanded=False):
        st.write("Summary:")
        st.write(st.session_state.state.get('summary'))

    st.markdown("---")
    st.write("If you need the app to integrate differently (for example, calling the compiled workflow object directly), tell me how you named your module or whether you want me to embed the whole flow inside this app. I can adapt the UI.")

# End of Streamlit app
