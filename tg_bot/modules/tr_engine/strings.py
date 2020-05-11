import yaml
from codecs import encode, decode
from haruka.modules.sql.redis import get_lang_chat
from haruka import LOGGER

LANGUAGES = ['en-US', 'en-GB', 'id', 'ru']

strings = {}

for i in LANGUAGES:
    strings[i] = yaml.full_load(open("locales/" + i + ".yml", "r"))


def tld(chat_id, t, show_none=True):
    LOCALE = get_lang_chat(chat_id)
    if LOCALE in ('en-US') and t in strings['en-US']:
        result = decode(
            encode(strings['en-US'][t], 'latin-1', 'backslashreplace'),
            'unicode-escape')
        return result
    elif LOCALE in ('en-GB') and t in strings['en-GB']:
        result = decode(
            encode(strings['en-GB'][t], 'latin-1', 'backslashreplace'),
            'unicode-escape')
        return result
    elif LOCALE in ('id') and t in strings['id']:
        result = decode(
            encode(strings['id'][t], 'latin-1', 'backslashreplace'),
            'unicode-escape')
        return result
    elif LOCALE in ('ru') and t in strings['ru']:
        result = decode(
            encode(strings['ru'][t], 'latin-1', 'backslashreplace'),
            'unicode-escape')
        return result

    if t in strings['en-US']:
        result = decode(
            encode(strings['en-US'][t], 'latin-1', 'backslashreplace'),
            'unicode-escape')
        return result

    err = f"No string found for {t}.\nReport it in @HarukaAyaGroup."
    LOGGER.warning(err)
    return err


def tld_list(chat_id, t):
    LOCALE = get_lang_chat(chat_id)
    if LOCALE in ('en-US') and t in strings['en-US']:
        return strings['en-US'][t]
    elif LOCALE in ('en-GB') and t in strings['en-GB']:
        return strings['en-GB'][t]
    elif LOCALE in ('id') and t in strings['id']:
        return strings['id'][t]
    elif LOCALE in ('ru') and t in strings['ru']:
        return strings['ru'][t]

    if t in strings['en-US']:
        return strings['en-US'][t]

    LOGGER.warning(f"#NOSTR No string found for {t}.")
    return f"No string found for {t}.\nReport it in @HarukaAyaGroup."
