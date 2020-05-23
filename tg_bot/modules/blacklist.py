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

from tg_bot.modules.tr_engine.strings import tld

BLACKLIST_GROUP = 11


@run_async
def blacklist(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    conn = connected(bot, update, chat, user.id, need_admin=False)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if chat.type == "private":
            return
        else:
            chat_id = update.effective_chat.id
            chat_name = chat.title

    filter_list = tld(chat.id, "blacklist_active_list").format(chat_name)

    all_blacklisted = sql.get_chat_blacklist(chat_id)

    if len(args) > 0 and args[0].lower() == 'copy':
        for trigger in all_blacklisted:
            filter_list += "<code>{}</code>\n".format(html.escape(trigger))
    else:
        for trigger in all_blacklisted:
            filter_list += " • <code>{}</code>\n".format(html.escape(trigger))

    split_text = split_message(filter_list)
    for text in split_text:
        if filter_list == tld(chat.id, "blacklist_active_list").format(
                chat_name):  #We need to translate
            msg.reply_text(tld(chat.id, "blacklist_no_list").format(chat_name),
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


__mod_name__ = "BlackList[s]"

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

*Example*
- /addblacklist the admins suck
This would delete any message containing 'the admins suck'.

- /addurl bit.ly
This would delete any message containing url "bit.ly".
"""


BLACKLIST_HANDLER = DisableAbleCommandHandler("blacklist",
                                              blacklist,
                                              pass_args=True)
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
