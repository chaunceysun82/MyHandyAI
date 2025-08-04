import streamlit as st
from dotenv import load_dotenv
import os, base64, json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, ConversationChain
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.memory import ConversationBufferMemory

load_dotenv()
API_KEY=os.getenv("GOOGLE_API_KEY")

template_models={
    "Gemini 2.5 Flash":"gemini-2.5-flash",
    "Gemini 2.5 Pro":"gemini-2.5-pro",
    "Gemini 2.5 Flash Lite":"gemini-2.5-flash-lite"
}
def get_llm(key: str):
    return ChatGoogleGenerativeAI(model=template_models[key], api_key=API_KEY)

summary_schema=[ResponseSchema(name="summary", description="Concise summary")]
summary_parser=StructuredOutputParser.from_response_schemas(summary_schema)
summary_prompt=PromptTemplate(
    input_variables=["query","info","img_b64"],
    partial_variables={"format_instructions": summary_parser.get_format_instructions()},
    template=(
        "You are an assistant. {format_instructions}\n"
        "Problem: {query}\n"
        "Description of the Problem: {info}\n"
        "Image (base64): {img_b64}"
    )
)

qa_schema=[ResponseSchema(name="questions", description="JSON list of questions with 'text' and optional 'choices'")]
qa_parser=StructuredOutputParser.from_response_schemas(qa_schema)
qa_prompt=PromptTemplate(
    input_variables=["summary"],
    partial_variables={"format_instructions": qa_parser.get_format_instructions()},
    template=(
        "Based on this summary, generate 3-5 clarifying questions. Return JSON array of questions. {format_instructions}\n"
        "Summary: {summary}"
    )
)

auth_schema=[ResponseSchema(name="valid", description="true if answer fits the question, otherwise false")]
auth_parser=StructuredOutputParser.from_response_schemas(auth_schema)
auth_prompt=PromptTemplate(
    input_variables=["question","answer"],
    partial_variables={"format_instructions": auth_parser.get_format_instructions()},
    template=(
        "Classify: does this answer is nearly not a doubt or answerable to the question? {format_instructions}\n"
        "Question: {question}\nAnswer: {answer}"
    )
)

explain_prompt=PromptTemplate(
    input_variables=["question"],
    template=(
        "The following question may be unclear. Provide a friendly explanation of what is being asked and how to think about it: {question}"
    )
)

tools_prompt=PromptTemplate(
    input_variables=["summary","qa_history"],
    template=(
        "Based on summary and Q&A, recommend only the missing tools and materials needed for the task.\n"
        "Summary: {summary}\nQ&A: {qa_history}"
    )
)

steps_prompt=PromptTemplate(
    input_variables=["summary","qa_history","tools"],
    template=(
        "Based on summary, Q&A, and tools, provide step-by-step approach, risk factors, and safety measures.\n"
        "Summary: {summary}\nQ&A: {qa_history}\nTools: {tools}"
    )
)

chat_system_prompt=PromptTemplate(
    input_variables=["input", "history"],
    template=(
        "You are an assistant for home repair and improvement tasks. You have answer the user queries in brief and in a simple way. Below is the context for the current task:\n"
        "Summary: {summary}\n"
        "Q&A: {qa_history}\n"
        "Tools: {tools}\n"
        "Steps: {steps}\n\n"
        "Current conversation:\n"
        "{history}\n"
        "Human: {input}\n"
        "Assistant:"
    )
)

st.set_page_config(page_title="MyHandyAI Full Flow")
st.title("MyHandyAI Full Flow")

df_img=st.file_uploader("Upload image", type=["jpg","jpeg","png"])
mode= st.radio("Input mode", ["Text","Voice"])
query=st.text_input("Describe the problem:") if mode=="Text" else ""
info=st.text_input("Description of the problem (optional):")

ss=st.session_state
ss.setdefault("stage", "summary")
ss.setdefault("summary", None)
ss.setdefault("questions", [])
ss.setdefault("current_q", 0)
ss.setdefault("answers", [])
ss.setdefault("tools", None)
ss.setdefault("steps", None)
ss.setdefault("chat_chain", None)
ss.setdefault("explanation", None)  
ss.setdefault("chat_history", "")  

if df_img and query:
    img_b64=base64.b64encode(df_img.read()).decode()

    st.subheader("1. Summary")
    if ss.summary:
        st.markdown(ss.summary)
    
    if ss.stage=="summary":
        model_summary=st.selectbox("Select model for Summary", list(template_models.keys()), key="model_summary")
        
        def generate_summary():
            raw=LLMChain(llm=get_llm(model_summary), prompt=summary_prompt).run({
                "query": query, "info": info or "None", "img_b64": img_b64
            })
            ss.summary=summary_parser.parse(raw)["summary"]
            ss.stage="questions"
            
        st.button("Generate Summary", on_click=generate_summary)

    if ss.stage in ["questions", "answering", "tools", "steps", "chat"]:
        st.subheader("2. Clarifying Questions")
      
        if ss.stage!="answering" and ss.answers:
            st.write("Questions and Answers:")
            for i, qa in enumerate(ss.answers):
                st.markdown(f"**Q{i+1}:** {qa['q']}")
                st.markdown(f"**A{i+1}:** {qa['a']}")
      
        if ss.stage=="questions":
            model_qa=st.selectbox("Select model for QA Generation", list(template_models.keys()), key="model_qa")
            
            def generate_questions():
                raw=LLMChain(llm=get_llm(model_qa), prompt=qa_prompt).run({"summary": ss.summary})
                parsed=qa_parser.parse(raw)
                try:
                    ss.questions=json.loads(parsed["questions"])
                except:
                    ss.questions=parsed["questions"]
                ss.current_q=0
                ss.stage="answering"
                
            st.button("Get Questions", on_click=generate_questions)
        
       
        if ss.stage=="answering":
            model_validation=st.selectbox("Select model for Answer Validation", list(template_models.keys()), key="model_validation")
            
            if ss.current_q<len(ss.questions):
                q=ss.questions[ss.current_q]
                st.markdown(f"**Q{ss.current_q+1}:** {q['text']}")
                
                if ss.explanation and ss.explanation.get(ss.current_q):
                    st.info(ss.explanation[ss.current_q])
                
                if q.get("choices"):
                    ans=st.radio("Select:", q["choices"] + ["I don't know","I'm not sure"], key=f"a{ss.current_q}")
                else:
                    ans=st.text_input("Answer:", key=f"a{ss.current_q}")
                    
                def submit_ans():
                    rawv=LLMChain(llm=get_llm(model_validation), prompt=auth_prompt).run({"question": q['text'], "answer": ans})
                    valid=auth_parser.parse(rawv)["valid"]
                    if valid=="true":
                        ss.answers.append({"q": q['text'], "a": ans})
                        ss.current_q+=1
                        
                        if ss.explanation:
                            ss.explanation.pop(ss.current_q, None)
                        if ss.current_q>=len(ss.questions):
                            ss.stage="tools"
                    else:
                        expl=LLMChain(llm=get_llm(model_validation), prompt=explain_prompt).run({"question": q['text']})
                    
                        if not ss.explanation:
                            ss.explanation={}
                        ss.explanation[ss.current_q]=expl
                        
                st.button("Submit Answer", on_click=submit_ans)

    if ss.stage in ["tools", "steps", "chat"]:
        st.subheader("3. Tools & Materials")
        if ss.tools:
            st.markdown(ss.tools)
        
        if ss.stage=="tools":
            model_tools=st.selectbox("Select model for Tools Generation", list(template_models.keys()), key="model_tools")
            
            def gen_tools():
                ss.tools=LLMChain(llm=get_llm(model_tools), prompt=tools_prompt).run({
                    "summary": ss.summary, "qa_history": ss.answers
                })
                ss.stage="steps"
                
            st.button("Generate Tools", on_click=gen_tools)

    if ss.stage in ["steps", "chat"]:
        st.subheader("4. Step-by-Step Approach")
        if ss.steps:
            st.markdown(ss.steps)
        
        if ss.stage=="steps":
            model_steps=st.selectbox("Select model for Steps Generation", list(template_models.keys()), key="model_steps")
            
            def gen_steps():
                ss.steps=LLMChain(llm=get_llm(model_steps), prompt=steps_prompt).run({
                    "summary": ss.summary, "qa_history": ss.answers, "tools": ss.tools
                })
                ss.stage="chat"
                
            st.button("Generate Steps", on_click=gen_steps)

    if ss.stage=="chat":
        st.subheader("5. Chat with Assistant")
        model_chat=st.selectbox("Select model for Chat", list(template_models.keys()), key="model_chat")
        
        context={
            "summary": ss.summary,
            "qa_history": "\n".join([f"Q: {qa['q']}\nA: {qa['a']}" for qa in ss.answers]),
            "tools": ss.tools,
            "steps": ss.steps
        }
        
        if ss.chat_chain is None:
            ss.chat_chain=ConversationChain(
                llm=get_llm(model_chat),
                prompt=chat_system_prompt.partial(**context),
                memory=ConversationBufferMemory(
                    memory_key="history",
                    return_messages=True,
                    human_prefix="Human",
                    ai_prefix="Assistant"
                )
            )
            
        user_q=st.text_input("Your question:", key="chat_input")
        if st.button("Ask Bot", key="chat_btn") and user_q:
            resp=ss.chat_chain.predict(input=user_q)
            st.markdown(f"**Assistant:** {resp}")
      
            ss.chat_history+=f"**You:** {user_q}\n**Assistant:** {resp}\n\n"
        
        if ss.chat_history:
            st.subheader("Chat History")
            st.markdown(ss.chat_history)
## Testing with Gemini Models
