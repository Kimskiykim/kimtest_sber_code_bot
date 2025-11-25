from app.enums import RolesEnum
from aiogram.types import BufferedInputFile


async def get_user_role(user_id: int, event, admin_ids = None) -> RolesEnum:
    # print("User ID:", user_id)
    if not admin_ids or not isinstance(admin_ids, list) and all([isinstance(adm, int) for adm in admin_ids]):
        admin_ids = []
    if user_id in admin_ids:
        return RolesEnum.ADMIN
    if event.chat and event.chat.type != "private":
        chat_admins = await event.chat.get_administrators()
        admin_ids = [admin.user.id for admin in chat_admins]
        # print("Chat admins:", admin_ids)
        if user_id in admin_ids:
            return RolesEnum.GROUP_ADMIN
    return RolesEnum.USER


async def send_py_from_memory(message, code_text: str):
    data = code_text.encode("utf-8")

    file = BufferedInputFile(
        file=data,
        filename="result.py"
    )
    await message.answer_document(file)


def to_markdown(code_text: str):
    return f"```\n{code_text}\n```"