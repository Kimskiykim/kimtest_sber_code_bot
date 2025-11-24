
FIRST_LINE_PROMPT = """
Generate a FIRST line of Python code for a collaborative coding game.
Rules:
- No logic.
- It must be a safe starter line: import, function signature, class header, etc.
- Max 95 characters.
- Do NOT write full function bodies.
Generate EXACTLY 6 variants as JSON list of strings.

Return STRICTLY IN JSON ONLY
NO ADDITIONAL INFO OR EXPLANATION NEEDED
WITH NO MARKUP (like ```json etc)
"""

NEXT_LINE_PROMPT = """
You are generating the NEXT line of Python code based on the prior code.
History:
{history}

Rules:
- Generate code that is the natural next line.
- Do NOT add new features or new logic.
- Continue the existing block/indentation.
- Max 95 characters per line.
- Return EXACTLY 6 variants as a JSON list.


Return STRICTLY IN JSON ONLY
NO ADDITIONAL INFO OR EXPLANATION NEEDED
WITH NO MARKUP (like ```json etc)
"""

EVALUATION_PROMPT = """
Оцените каждую предложенную строку Python-кода по шкале от 0 до 100.

Критерии:

синтаксически корректная (или почти корректная);

логично и естественно продолжающая указанную историю;

короткая (менее 95 символов).

История:
{history}

Кандидаты:
{candidates}

Верните СТРОГО ТОЛЬКО JSON вида: {{ "<строка>": score }}
БЕЗ каких-либо пояснений, комментариев или разметки (например, ```json).
"""

COMPLETE_PROMPT = """
Ты - профессиональный senior-разработчик на Python3.
Дополни следующий фрагмент Python-кода до полностью корректного и запускаемого кода.

# Правила:

- Не добавляй новую логику, функциональность или ветвления.
- Только закрывай блоки, завершай выражения, добавляйте недостающие return.
- Смысл и структура кода должны остаться полностью неизменными.
- Никаких расширений, оптимизаций или рефакторинга. Входящая часть кода должна быть неизменной в ответе
- Максимальная длина каждой дополненной строки не должна превышать 95 символов c учетом отступов и пробелов
- Если добавление нового кода излишне (он и так корректен и запускаем и соблюдены все правила), то ничего не добавляй

# Код:
{code}

# Формат ответа:
Верните ТОЛЬКО итоговый рабочий python-код,
БЕЗ каких-либо комментариев, объяснений, форматирования или разметки (например, ```python).


# ПРИМЕРЫ:
## 1-пример:
Input Code:

def helloWorld():
    print('helloWorld')

Returned Code:

def helloWorld():
    print('helloWorld')
    return None

## 2-пример:
Input Code:

async def generate_next(self, state: CodeState):
    drafts = await self.llm_generate_next(state["history"])
    state["drafts"] = drafts

Returned Code:

async def generate_next(self, state: CodeState):
    drafts = await self.llm_generate_next(state["history"])
    state["drafts"] = drafts
    return state
"""
