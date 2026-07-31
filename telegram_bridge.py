"""
Telegram Bridge — Lucienne Nightfall Absolute Edition
No /start required. Auto-init on first message.
Conversational, autonomous, with full command set.
"""
import asyncio
import logging
import os
import sys
from typing import Optional

from telegram import Update, BotCommand
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from openhands_runner import LucienneRunner

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Config from env
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
AUTHORIZED_USER_ID = os.getenv("AUTHORIZED_USER_ID", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Global runner (singleton per process)
_runner: Optional[LucienneRunner] = None
_runner_lock = asyncio.Lock()


async def get_runner() -> LucienneRunner:
    """Get or initialize runner singleton."""
    global _runner
    if _runner is None:
        async with _runner_lock:
            if _runner is None:
                _runner = LucienneRunner(
                    model=LLM_MODEL,
                    api_key=LLM_API_KEY,
                    base_url=LLM_BASE_URL,
                    github_token=GITHUB_TOKEN,
                    on_event=_handle_runner_event,
                )
                success = await _runner.init()
                if not success:
                    logger.error("Failed to initialize Lucienne runner")
    return _runner


async def _handle_runner_event(event_type: str, data: dict) -> None:
    """Handle events from runner (safety, streaming, autonomous steps)."""
    # In production, this would send messages to Telegram
    # For now, log to console
    if event_type == "safety_pause":
        logger.warning(f"🔒 SAFETY PAUSE: {data['kind']} — {data['content'][:100]}")
    elif event_type == "autonomous_step":
        logger.info(f"🤖 Step {data['step']} [{data['phase']}]: {data['message']}")
    else:
        logger.info(f"📡 Event [{event_type}]: {str(data)[:200]}")


# ========== AUTH ==========

def is_authorized(user_id: int) -> bool:
    """Check if user is authorized."""
    if not AUTHORIZED_USER_ID:
        return True  # No restriction if not set
    return str(user_id) == AUTHORIZED_USER_ID


# ========== HANDLERS ==========

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free-form text messages — conversational mode."""
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    message_text = update.message.text or ""
    # Guard: skip command messages (let CommandHandler handle them)
    if message_text.startswith('/'):
        return
    user_id = str(user.id)

    # Typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    # Get runner (auto-init on first message)
    runner = await get_runner()
    if runner is None:
        await update.message.reply_text("❌ Lucienne failed to initialize. Check server logs.")
        return

    # Send to runner
    try:
        response = await runner.chat(message_text, user_id=user_id)
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Chat error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — Explicit initialization + status."""
    try:
        user = update.effective_user
        logger.info(f"cmd_start called by user {user.id}")
        if not is_authorized(user.id):
            logger.warning(f"cmd_start: user {user.id} not authorized")
            await update.message.reply_text("🚫 Unauthorized.")
            return

        logger.info("cmd_start: calling get_runner()")
        runner = await get_runner()
        logger.info(f"cmd_start: get_runner() returned {runner}")
        if runner is None:
            logger.error("cmd_start: runner is None")
            await update.message.reply_text("❌ Initialization failed.")
            return

        status = runner.get_status()
        msg = (
            "🌙 **Lucienne Nightfall — CENGO Online**\n"
            "Codename: Code Executor & Network Gateway Operator\n\n"
            f"✅ Initialized: {status['initialized']}\n"
            f"📚 Skills loaded: {status['skills_loaded']}\n"
            f"🔌 MCP servers: {status['mcp_servers']}\n"
            f"🧠 Memory tasks: {status['memory_tasks']}\n\n"
            "I am ready. Chat freely or use commands:\n"
            "`/auto <task>` — Autonomous multi-step\n"
            "`/task <task>` — Direct task execution\n"
            "`/status` — System status\n"
            "`/skills [query]` — Search skills\n"
            "`/mcp list` — MCP servers\n"
            "`/reset` — Reset conversation\n"
            "`/cancel` — Cancel execution"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        logger.info("cmd_start response sent")
    except Exception as e:
        logger.error(f"cmd_start error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ cmd_start error: {e}")


async def cmd_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/task <description> — Execute a specific task."""
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/task <description>`")
        return

    task_desc = " ".join(context.args)
    user_id = str(user.id)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    runner = await get_runner()
    try:
        result = await runner.run_task(task_desc, user_id=user_id)
        await update.message.reply_text(result, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Task error: {e}")


async def cmd_auto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/auto <task> — Run autonomous multi-step loop."""
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/auto <task>`")
        return

    task = " ".join(context.args)
    user_id = str(user.id)

    await update.message.reply_text(f"🤖 Starting autonomous loop...\nTask: {task}")

    runner = await get_runner()
    try:
        result = await runner.run_autonomous(task, user_id=user_id)

        status_emoji = "✅" if result["status"] == "completed" else "⚠️"
        msg = (
            f"{status_emoji} **Autonomous Task Complete**\n"
            f"ID: `{result['task_id']}`\n"
            f"Status: {result['status']}\n"
            f"Iterations: {result['iterations']}\n\n"
            f"**Result:**\n{result['result'][:1500]}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Autonomous error: {e}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/status — Show system status."""
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    runner = await get_runner()
    if runner is None:
        await update.message.reply_text("❌ Not initialized.")
        return

    status = runner.get_status()
    msg = (
        "🌙 **Lucienne Status**\n"
        f"Initialized: {'✅' if status['initialized'] else '❌'}\n"
        f"Paused: {'🔒 Yes' if status['paused'] else '✅ No'}\n"
        f"Pending actions: {status['pending_actions']}\n"
        f"Current task: `{status['current_task'] or 'None'}`\n"
        f"Skills loaded: {status['skills_loaded']}\n"
        f"MCP servers: {status['mcp_servers']}\n"
        f"Memory tasks: {status['memory_tasks']}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/approve — Approve pending risky action."""
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    runner = await get_runner()
    result = runner.approve_pending()
    await update.message.reply_text(result)


async def cmd_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/reject — Reject pending risky action."""
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    runner = await get_runner()
    result = runner.reject_pending()
    await update.message.reply_text(result)


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/cancel — Cancel current execution."""
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    runner = await get_runner()
    result = runner.cancel_execution()
    await update.message.reply_text(result)


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/reset — Reset conversation and memory."""
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    runner = await get_runner()
    result = runner.reset_conversation()
    await update.message.reply_text(result)


async def cmd_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/skills [query] — List or search skills."""
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    runner = await get_runner()
    query = " ".join(context.args) if context.args else ""

    if query:
        matches = runner.skills.match_skills(query)
        if matches:
            lines = [f"📚 Skills matching '{query}':"]
            for name, score in matches:
                lines.append(f"• {name} ({score:.0%})")
            await update.message.reply_text("\n".join(lines))
        else:
            await update.message.reply_text(f"No skills found for '{query}'")
    else:
        skills = runner.skills.list_skills()
        if skills:
            await update.message.reply_text(f"📚 Loaded skills ({len(skills)}):\n" + "\n".join(f"• {s}" for s in skills[:20]))
        else:
            await update.message.reply_text("📚 No skills loaded. Mount skills to /opt/skills")


async def cmd_mcp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/mcp list|tools — MCP server management."""
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    runner = await get_runner()
    args = context.args

    if not args or args[0] == "list":
        servers = runner.mcp.list_servers()
        if servers:
            await update.message.reply_text("🔌 MCP Servers:\n" + "\n".join(f"• {s}" for s in servers))
        else:
            await update.message.reply_text("🔌 No MCP servers registered.")
    elif args[0] == "tools":
        tools = runner.mcp.get_all_tools()
        lines = ["🔧 MCP Tools:"]
        for server, tool_list in tools.items():
            for t in tool_list:
                lines.append(f"• {server}/{t.get('name', '?')}: {t.get('description', 'No desc')}")
        await update.message.reply_text("\n".join(lines) if len(lines) > 1 else "No tools found.")
    else:
        await update.message.reply_text("Usage: `/mcp list` or `/mcp tools`")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help — Show help."""
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("🚫 Unauthorized.")
        return

    msg = (
        "🌙 **Lucienne Commands**\n\n"
        "*(Chat freely without / for conversational mode)*\n\n"
        "**/start** — Initialize & status\n"
        "**/task <desc>** — Direct task execution\n"
        "**/auto <task>** — Autonomous multi-step loop\n"
        "**/status** — System status\n"
        "**/skills [query]** — List/search skills\n"
        "**/mcp list|tools** — MCP management\n"
        "**/approve** — Approve risky action\n"
        "**/reject** — Reject risky action\n"
        "**/cancel** — Cancel execution\n"
        "**/reset** — Reset conversation\n"
        "**/help** — This message"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ========== MAIN ==========

async def post_init(application: Application) -> None:
    """Set bot commands after initialization."""
    await application.bot.set_my_commands([
        BotCommand("start", "Initialize & status"),
        BotCommand("task", "Direct task execution"),
        BotCommand("auto", "Autonomous multi-step loop"),
        BotCommand("status", "System status"),
        BotCommand("skills", "List/search skills"),
        BotCommand("mcp", "MCP server management"),
        BotCommand("approve", "Approve risky action"),
        BotCommand("reject", "Reject risky action"),
        BotCommand("cancel", "Cancel execution"),
        BotCommand("reset", "Reset conversation"),
        BotCommand("help", "Show help"),
    ])
    logger.info("✅ Bot commands registered")


async def async_main() -> None:
    """Async main entry point."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Commands
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("task", cmd_task))
    application.add_handler(CommandHandler("auto", cmd_auto))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("approve", cmd_approve))
    application.add_handler(CommandHandler("reject", cmd_reject))
    application.add_handler(CommandHandler("cancel", cmd_cancel))
    application.add_handler(CommandHandler("reset", cmd_reset))
    application.add_handler(CommandHandler("skills", cmd_skills))
    application.add_handler(CommandHandler("mcp", cmd_mcp))
    application.add_handler(CommandHandler("help", cmd_help))

    # Free-form text (conversational) — catch-all
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("🌙 Lucienne Telegram Bridge starting...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    await asyncio.Event().wait()  # Run forever


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        sys.exit(1)

    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("🌙 Bridge stopped by user")


if __name__ == "__main__":
    main()
