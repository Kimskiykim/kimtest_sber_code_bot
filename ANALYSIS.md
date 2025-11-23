# Project Overview

This repository implements a Telegram bot using `aiogram`. The entry point is `src/main.py`, which initializes the bot with settings from environment variables and starts polling using a router defined in `app.handlers`.

## Architecture
- **Settings**: `app.settings.AppCTXSettings` loads environment variables (e.g., bot token, admin IDs) with validation for admin lists.
- **Routing & Middleware**: `app.handlers` registers command handlers and applies `RoleMiddleware` to inject user roles from `app.utils.get_user_role` for access control.
- **Roles & Commands**: `app.enums` defines `RolesEnum` and `CommandsEnum` to enumerate role types and bot commands.
- **Keyboards**: `app.keyboards.get_keyboard_for_role` builds reply keyboards based on the user's role, using `CommandsEnum` values.
- **Utilities**: `app.utils.get_user_role` contains placeholder logic to classify users as admin, group admin, or standard user by comparing IDs and chat administrators.

## Notable Observations
- `RoleMiddleware` currently trusts the placeholder `get_user_role` logic. It should be replaced with real authorization checks and persisted role assignments.
- Command handlers in `app.handlers` are minimal and mostly send static responses. They can be extended to implement the described behaviors (e.g., sending logs, performing health checks).
- Keyboard generation relies on static role-to-command mapping; consider external configuration if roles or commands grow.
- The `TG_BOT_ADMINS` setting supports multiple formats but returns an empty list when provided with invalid data without explicit error signaling. Validation could be tightened if stricter configuration is required.
