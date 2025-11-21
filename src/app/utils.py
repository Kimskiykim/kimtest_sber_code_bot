from app.enums import RolesEnum

async def get_user_role(user_id: int, event) -> RolesEnum:
    # Dummy implementation for example purposes
    print("User ID:", user_id)
    admin_ids = [94408817, 123456789]  # Example admin IDs
    if user_id in admin_ids:
        return RolesEnum.ADMIN
    if event.chat and event.chat.type != "private":
        chat_admins = await event.chat.get_administrators()
        admin_ids = [admin.user.id for admin in chat_admins]
        print("Chat admins:", admin_ids)
        if user_id in admin_ids:
            return RolesEnum.GROUP_ADMIN
    return RolesEnum.USER
