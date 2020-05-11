import html
import re
from typing import List

from telegram import Update, Bot, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters, run_async

import tg_bot.modules.sql.blacklist_sql as sql
from tg_bot import dispatcher, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin, user_not_admin
from tg_bot.modules.helper_funcs.extraction import extract_text
from tg_bot.modules.helper_funcs.misc import split_message

from tg_bot.modules.connection import connected


BLACKLIST_GROUP = 11


@run_async
@user_admin
def blacklist(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message
    chat = update.effective_chat

    update_chat_title = chat.title
    message_chat_title = update.effective_message.chat.title

    if update_chat_title == message_chat_title:
        base_blacklist_string = "Current <b>blacklisted</b> words:\n"
    else:
        base_blacklist_string = f"Current <b>blacklisted</b> words in <b>{update_chat_title}</b>:\n"

    all_blacklisted = sql.get_chat_blacklist(chat.id)

    filter_list = base_blacklist_string

    if len(args) > 0 and args[0].lower() == 'copy':
        for trigger in all_blacklisted:
            filter_list += f"<code>{html.escape(trigger)}</code>\n"
    else:
        for trigger in all_blacklisted:
            filter_list += f" - <code>{html.escape(trigger)}</code>\n"

    split_text = split_message(filter_list)
    for text in split_text:
        if text == base_blacklist_string:
            if update_chat_title == message_chat_title:
                msg.reply_text("There are no blacklisted messages here!")
            else:
                msg.reply_text(f"There are no blacklisted messages in <b>{update_chat_title}</b>!",
                               parse_mode=ParseMode.HTML)
            return
        msg.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
@user_admin
def add_blacklist(bot: Bot, update: Update):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    words = msg.text.split(None, 1)

    conn = connected(bot, update, chat, user.id)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            return
        else:
            chat_name = chat.title

    if len(words) > 1:
        text = words[1]
        to_blacklist = list(
            set(trigger.strip() for trigger in text.split("\n")
                if trigger.strip()))
        for trigger in to_blacklist:
            sql.add_to_blacklist(chat_id, trigger.lower())

        if len(to_blacklist) == 1:
            msg.reply_text(tld(chat.id, "blacklist_add").format(
                html.escape(to_blacklist[0]), chat_name),
                           parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(tld(chat.id,
                               "blacklist_add").format(len(to_blacklist)),
                           chat_name,
                           parse_mode=ParseMode.HTML)

    else:
        msg.reply_text(tld(chat.id, "blacklist_err_add_no_args"))


@run_async
@user_admin
def unblacklist(bot: Bot, update: Update):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    words = msg.text.split(None, 1)

    conn = connected(bot, update, chat, user.id)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            return
        else:
            chat_name = chat.title

    if len(words) > 1:
        text = words[1]
        to_unblacklist = list(
            set(trigger.strip() for trigger in text.split("\n")
                if trigger.strip()))
        successful = 0
        for trigger in to_unblacklist:
            success = sql.rm_from_blacklist(chat_id, trigger.lower())
            if success:
                successful += 1

        if len(to_unblacklist) == 1:
            if successful:
                msg.reply_text(tld(chat.id, "blacklist_del").format(
                    html.escape(to_unblacklist[0]), chat_name),
                               parse_mode=ParseMode.HTML)
            else:
                msg.reply_text(tld(chat.id, "blacklist_err_not_trigger"))

        elif successful == len(to_unblacklist):
            msg.reply_text(tld(chat.id, "blacklist_multi_del").format(
                successful, chat_name),
                           parse_mode=ParseMode.HTML)

        elif not successful:
            msg.reply_text(tld(chat.id,
                               "blacklist_err_multidel_no_trigger").format(
                                   successful,
                                   len(to_unblacklist) - successful),
                           parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(tld(
                chat.id, "blacklist_err_multidel_some_no_trigger").format(
                    successful, chat_name,
                    len(to_unblacklist) - successful),
                           parse_mode=ParseMode.HTML)
    else:
        msg.reply_text(tld(chat.id, "blacklist_err_del_no_args"))


@run_async
@user_not_admin
def del_blacklist(bot: Bot, update: Update):
    chat = update.effective_chat
    message = update.effective_message
    to_match = extract_text(message)
    if not to_match:
        return

    chat_filters = sql.get_chat_blacklist(chat.id)
    for trigger in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(trigger) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("Error while deleting blacklist message.")
            break


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __stats__():
    return "• `{}` blacklist triggers, across `{}` chats.".format(
        sql.num_blacklist_filters(), sql.num_blacklist_filter_chats())


__mod_name__ = "Blacklist"

__help__ = """
Blacklists are used to stop certain triggers from being said in a group. Any time the trigger is mentioned, the message will immediately be deleted. A good combo is sometimes to pair this up with warn filters!

*NOTE* blacklists do not affect group admins.

 - /blacklist: View the current blacklisted words.
- /geturl: View the current blacklisted urls

*Admin only*
- /addblacklist <blacklist trigger> blacklists the trigger. You can set sentences by putting quotes around the reason.
- /unblacklist <blacklist trigger>: stop blacklisting a certain blacklist trigger.
- /rmblacklist <blacklist trigger>: same as /unblacklist
- /addurl <urls>: Add a domain to the blacklist. The bot will automatically parse the url.
- /delurl <urls>: Remove urls from the blacklist.

*Top tip*
Blacklists allow you to use some modifiers to match "unknown" characters. For example, you can use the ? character to match a single occurence of any non-whitespace character.
You could also use the  modifier, which matches any number of any character. If you want to blacklist urls, this will allow you to match the full thing. It matches every character except spaces. This is cool if you want to stop, for example, url shorteners.
For example, the following will Delete any bit.ly link:
/addblacklist bit.ly/
If you wanted to only match bit.ly/ links followed by three characters, you could use:
/addblacklist bit.ly/??? 
This would match bit.ly/abc, but not bit.ly/abcd.

*Example*
- /addblacklist the admins suck
This would delete any message containing 'the admins suck'.

- /addurl bit.ly
This would delete any message containing url "bit.ly".
"""


BLACKLIST_HANDLER = DisableAbleCommandHandler("blacklist",
                                              blacklist,
                                              pass_args=True,
                                              admin_ok=True)
ADD_BLACKLIST_HANDLER = CommandHandler("addblacklist", add_blacklist)
UNBLACKLIST_HANDLER = CommandHandler(["unblacklist", "rmblacklist"],
                                     unblacklist)
BLACKLIST_DEL_HANDLER = MessageHandler(
    (Filters.text | Filters.command | Filters.sticker | Filters.photo)
    & Filters.group,
    del_blacklist,
    edited_updates=True)

dispatcher.add_handler(BLACKLIST_HANDLER)
dispatcher.add_handler(ADD_BLACKLIST_HANDLER)
dispatcher.add_handler(UNBLACKLIST_HANDLER)
dispatcher.add_handler(BLACKLIST_DEL_HANDLER, group=BLACKLIST_GROUP)
