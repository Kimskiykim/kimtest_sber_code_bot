import json
from typing import List
from app.llm.prompts import (FIRST_LINE_PROMPT, NEXT_LINE_PROMPT,
                      EVALUATION_PROMPT, COMPLETE_PROMPT)
from typing import List, TypedDict, Optional
from langchain_gigachat import GigaChat
from langgraph.graph.state import StateGraph, START, END
# from langgraph.checkpoint.memory import InMemorySaver

from enum import Enum, auto
import ast
from functools import wraps
import json
from app.settings import AppCTXSettings


class LLMModelEnum(Enum):
    judge = auto()
    generator = auto()


class CodeState(TypedDict):
    history: List[str]               # готовые строки кода
    mode: str                        # zero | next | complete
    drafts: List[str]                # черновые варианты
    final: List[str]                 # финальные 4 варианта
    completed_code: Optional[str]    # финальный код для complete


def is_syntax_ok(line: str) -> bool:
    try:
        ast.parse(line)
        return True
    except Exception:
        return False

def string_converter(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        func_res = await func(*args, **kwargs)
        return json.loads(func_res)
        # return ast.literal_eval(func_res)
    return wrapper


class LLMGenerator:
    def __init__(self, app_config: AppCTXSettings, memory = None):
        self.model = app_config.LLM_MODEL or "GigaChat-Max"
        self.llm = {
            LLMModelEnum.generator: GigaChat(
                model=self.model, credentials=app_config.LLM_AUTHORIZATION_KEY, verify_ssl_certs=False,
                temperature=0.6, top_p=0.9),
            LLMModelEnum.judge: GigaChat(
                model=self.model, credentials=app_config.LLM_AUTHORIZATION_KEY, verify_ssl_certs=False,
                temperature=0.1),
        }
        self.memory_saver = memory
    
    def pick_best_4(self, drafts, llm_scores):
        # 1. длина
        drafts = [d for d in drafts if len(d) <= 95]

        # 2. remove duplicates
        seen = set()
        uniq = []
        for d in drafts:
            if d not in seen:
                uniq.append(d)
                seen.add(d)
        drafts = uniq

        # 3. syntax boost
        scored = []
        for d in drafts:
            score = llm_scores.get(d, 0)
            if is_syntax_ok(d):
                score += 20
            scored.append((score, d))

        # 4. sort desc
        scored.sort(reverse=True, key=lambda x: x[0])

        # 5. top4
        return [d for (_, d) in scored[:4]]
    
    async def call_llm(self, prompt: str, type: LLMModelEnum = LLMModelEnum.generator) -> str:
        return await self.llm[type].ainvoke(prompt)

    @string_converter
    async def llm_generate_first_line(self) -> List[str]:
        raw = await self.call_llm(FIRST_LINE_PROMPT)
        return raw.content

    @string_converter
    async def llm_generate_next(self, history: List[str]) -> List[str]:
        prompt = NEXT_LINE_PROMPT.format(history="\n".join(history))
        raw = await self.call_llm(prompt)
        print("----")
        print("llm_generate_next", raw.content)
        print("----")
        return raw.content

    @string_converter
    async def llm_evaluate(self, history: List[str], drafts: List[str]) -> dict:
        prompt = EVALUATION_PROMPT.format(
            history="\n".join(history),
            candidates=drafts
        )
        raw = await self.call_llm(prompt,LLMModelEnum.judge)
        return raw.content

    async def llm_auto_complete(self, history: List[str]) -> str:
        prompt = COMPLETE_PROMPT.format(code="\n".join(history))
        raw = await self.call_llm(prompt, LLMModelEnum.judge)
        return raw.content

    
    async def generate_first(self, state: CodeState):
        drafts = await self.llm_generate_first_line()
        state["drafts"] = drafts
        return state


    async def generate_next(self, state: CodeState):
        drafts = await self.llm_generate_next(state["history"])
        state["drafts"] = drafts
        return state


    async def evaluate(self, state: CodeState):
        drafts = state["drafts"]
        history = state["history"]

        llm_scores = await self.llm_evaluate(history, drafts)
        final = self.pick_best_4(drafts, llm_scores)

        state["final"] = final
        return state


    async def auto_complete(self, state: CodeState):
        completed = await self.llm_auto_complete(state["history"])
        state["completed_code"] = completed
        return state


    def return_4(self, state: CodeState):
        return state
    
    def route_by_mode(self, state: CodeState):
        if state["mode"] == "zero":
            return "zero_history"
        if state["mode"] == "next":
            return "next_line"
        if state["mode"] == "complete":
            return "auto_complete"
    
    
    def build_graph(self):
        graph = StateGraph(CodeState)

        graph.add_node("zero_history", self.generate_first)
        graph.add_node("next_line", self.generate_next)
        graph.add_node("evaluate", self.evaluate)
        graph.add_node("return4", self.return_4)
        graph.add_node("auto_complete", self.auto_complete)
        
        graph.add_conditional_edges(START, self.route_by_mode, {
        "zero_history": "zero_history",
        "next_line": "next_line",
        "auto_complete": "auto_complete"
    })

        graph.add_edge("zero_history", "evaluate")
        graph.add_edge("next_line", "evaluate")
        graph.add_edge("evaluate", "return4")
        graph.add_edge("auto_complete", END)

        return graph.compile(debug=True, checkpointer=self.memory_saver)
    

# import asyncio


# async def main():
    # llgen = LLMGenerator()
    # graph = llgen.build_graph()
    # config = {"configurable": {"thread_id": 1}}


#     # тест первого режима
#     # result = await graph.ainvoke({
#     #     "mode": "zero",
#     #     "history": []
#     # }, config=config)
#     # print("\n=== ZERO RESULT ===")
#     # print(result)

#     # # тест второго режима
#     # result = await graph.ainvoke({
#     #     "mode": "next",
#     #     "history": ["def hello():", "    pass"]
#     # }, config=config)
#     # print("\n=== NEXT RESULT ===")
#     # print(result)

#     # тест complete
#     result = await graph.ainvoke({
#         "mode": "complete",
#         "history": ["def hello():", "    print('x')"]
#     }, config=config)
#     print("\n=== COMPLETE RESULT ===")
#     print(result["completed_code"])

# if __name__ == "__main__":
#     asyncio.run(main())