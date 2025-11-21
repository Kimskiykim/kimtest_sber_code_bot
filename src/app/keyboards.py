from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
# ---
from app.enums import CommandsEnum, RolesEnum

user_commands = (CommandsEnum.CODE, )
admin_commands = tuple(list(user_commands) + [CommandsEnum.START, CommandsEnum.CODE_COMPLETED, CommandsEnum.SEND_NOW, ])
owner_commands = tuple(list(admin_commands) + [CommandsEnum.HEALTH, CommandsEnum.LOGS, CommandsEnum.ALLOGS])


ROLE_KEYBOARDS = {
    RolesEnum.ADMIN: owner_commands,
    RolesEnum.GROUP_ADMIN: admin_commands,
    RolesEnum.USER: user_commands
}

def chunk_list(lst, size):
    return [lst[i:i+size] for i in range(0, len(lst), size)]

def get_keyboard_for_role(role: RolesEnum) -> ReplyKeyboardMarkup:
    buttons = [KeyboardButton(text="/" + btn.value) for btn in ROLE_KEYBOARDS.get(role, [])]
    rows = chunk_list(buttons, 3)
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True
    )
