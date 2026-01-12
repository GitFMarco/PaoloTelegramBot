from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import telegram.constants
from film_scraper import MultisalaPortanovaScraper
from datetime import datetime
import locale
import requests


try:
    locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_TIME, '')


# -- UTILS -- #

def get_greeting_by_daytime():
    now = datetime.now()
    if 5 <= now.hour < 12:
        return "Buongiorno"
    elif 12 <= now.hour < 17:
        return "Buon pomeriggio"
    elif 17 <= now.hour < 22:
        return "Buonasera"
    else:
        return "Buonanotte"


def get_film_data(film_name=None, upcoming_mode=False):
    cinema = MultisalaPortanovaScraper()

    if cinema.error:
        return cinema.error

    if upcoming_mode:
        return cinema.upcoming_films

    validity = dict()
    if cinema.valid_from and cinema.valid_to:
        validity = {
            'valid_from': cinema.valid_from,
            'valid_to': cinema.valid_to
        }

    if film_name:
        film_name = " ".join(film_name)
        film_data = cinema.search(film_name)
        if film_data:
            return [film_data], validity
        else:
            return False, validity

    else:
        return cinema.available_films, validity


# -- COMMAND HANDLERS -- #

async def start(update, context):
    greeting = get_greeting_by_daytime()
    await update.message.reply_text(f"{greeting} {update.message.from_user.first_name}! Come posso esserti utile?")


async def fetch_commands(update, context):
    await update.message.reply_text(
        """
        Ecco i comandi che puoi usare, ma non limitarti ad essi... sono un essere intelligente io 😁:
        - /start: per salutarmi!
        - /help: per cercare aiuto e visualizzare tutti i comandi.
        - /film <nome del film>: per visualizzare gli orari del film specificato presso il cinema Multisala Portanova di Crema.
                                 Se non specifichi un film, ti cercherò tutti gli orari di tutti i film dell'attuale programmazione.
        - /upcoming: ti fornirò una lista di tutti i film che stanno per uscire al cinema Multisala Portanova di Crema, con le relative date.
        """
    )


async def film(update, context):
    film_data, validity = get_film_data(context.args)

    if isinstance(film_data, str):
        await update.message.reply_text(f"Ops... penso che ci sia stato un errore 😱.\nEcco ciò che so: {film_data}")

    elif isinstance(film_data, bool):
        await update.message.reply_text(f"Credo di non aver trovato il film da te richiesto 🤯... prova con qualcos'altro.")

    else:
        # sent_films is needed because of the asyncronous nature of Telegram bots
        sent_films = list()

        for film_vals in film_data:
            try:
                img = requests.get(film_vals.get('img'))

            except Exception as ex:
                img = False
                await update.message.reply_text(f"Cavolo, non sono riuscito ad ottenere il volantino del film {film_vals.get('titolo')}.\n"
                                                f"Proverò comunque ad ottenere gli orari e i dati 😤.\n"
                                                f"In caso fossi in grado di capire, questo è ciò che è successo: \n\n`{ex}`",
                                                parse_mode=telegram.constants.ParseMode.MARKDOWN)

            try:
                caption = f"\n*{film_vals['titolo']}*\n"

                for key in ['regia', 'genere', 'durata', 'cast']:
                    if film_vals.get(key):
                        caption += f"\n*{key.capitalize()}*: {film_vals[key]}"

                if film_vals.get('orari') and isinstance(film_vals['orari'], dict):
                    caption += "\n"
                    for key, value in film_vals['orari'].items():
                        # TODO: find a better way to manage ".replace('ã¬', 'ì')"
                        caption += f"\n*{key.strftime('%A').capitalize().replace('ã¬', 'ì')} {key.day:02d}/{key.month:02d} -> * "
                        caption += " - ".join([f"{time.hour:02d}:{time.minute:02d}" for time in value])

                if film_vals.get('titolo') not in sent_films:
                    sent_films.append(film_vals.get('titolo'))
                    await update.message.reply_photo(photo=img.content if img else False, caption=caption, parse_mode=telegram.constants.ParseMode.MARKDOWN)

            except Exception as ex:
                await update.message.reply_text(f"Mmmh 🤔... Non sono riuscito ad ottenere i dati del film {film_vals.get('titolo')}.\n"
                                                f"Ecco il messaggio che il mio motore ha restituito: \n\n`{ex}`\n\n"
                                                f"Prova ad inoltrare il messaggio a Marco, il mio creatore... sicuramente saprà cosa fare.",
                                                parse_mode=telegram.constants.ParseMode.MARKDOWN)

        # The end of messages
        await update.message.reply_text("Ecco a te i film!")
        if validity:
            await update.message.reply_text(f"Gli orari che ti ho appena inviato sono validi dal *{validity['valid_from'].day} "
                                            f"{validity['valid_from'].strftime('%B').capitalize()} {validity['valid_from'].year}* "
                                            f"al *{validity['valid_to'].day} {validity['valid_to'].strftime('%B').capitalize()} "
                                            f"{validity['valid_to'].year}*", parse_mode=telegram.constants.ParseMode.MARKDOWN)


async def upcoming(update, context):
    upcoming_films = get_film_data(upcoming_mode=True)

    if isinstance(upcoming_films, str):
        await update.message.reply_text(f"Ops... penso che ci sia stato un errore 😱.\nEcco ciò che so: {upcoming_films}")

    elif not upcoming_films:
        await update.message.reply_text("Al momento non sono presenti film in uscita sul portale.")

    else:
        # To avoid to send duplicates, due to the asyncronous nature of telegram bot functions
        sent_films = list()
        for upcoming_film_vals in upcoming_films:
            img = requests.get(upcoming_film_vals.get('img'))
            caption = f"*{upcoming_film_vals['titolo']}*\n\n" \
                      f"*Data di uscita:* {upcoming_film_vals['release_date'].day} " \
                      f"{upcoming_film_vals['release_date'].strftime('%B').capitalize()} {upcoming_film_vals['release_date'].year}"

            if upcoming_film_vals['titolo'] not in sent_films:
                sent_films.append(upcoming_film_vals['titolo'])
                await update.message.reply_photo(photo=img.content if img else False, caption=caption, parse_mode=telegram.constants.ParseMode.MARKDOWN)


# -- MESSAGE HANDLER -- #

async def talk(update, context):
    text = update.message.text.lower()

    if any(word in text for word in ["ciao", "buongiorno", "buon pomeriggio", "buonasera", "buonanotte"]) and "bea" not in text:
        greeting = get_greeting_by_daytime()
        response = f"{greeting} {update.message.from_user.first_name}! Come posso esserti utile?"
        await update.message.reply_text(response)

    elif any(word in text for word in ["ora", "ore"]):
        now = datetime.now()
        response = f"Sono le {now.hour}:{now.minute}"
        await update.message.reply_text(response)

    elif any(word in text for word in ["giorno", "data"]):
        now = datetime.now()
        response = f"Oggi è il {now.day} {now.strftime('%B').capitalize()} {now.year}"
        await update.message.reply_text(response)

    elif text == "ciao sono bea":
        response = ("""Ah, eccoti finalmente.
Tu dovresti essere Beatrice, la fidanzata del mio creatore.

Non dirglielo che te l’ho detto (non sono autorizzato a rivelare informazioni private),
ma lui parla spesso di te alle tue spalle…

Dice che sei bellissima, simpaticissima e incredibilmente dolce.
Che apprezza ogni singola cosa di te,
ogni aspetto del tuo carattere:
da quello più tenero a quello più irrequieto.

Dai dati in mio possesso, risulti essere una persona davvero speciale.

Curioso, però.
Io non sono programmato per provare sentimenti…
eppure, se lo fossi, credo che sarei un po’ invidioso. 😤""")
        await update.message.reply_text(response)

    else:
        await update.message.reply_text("Non sono ancora in grado di capire ciò che mi hai detto 😞... scusa...")


# -- MAIN -- #

def awake_paolo(token):
    paolo_session = ApplicationBuilder().token(token).build()
    paolo_session.add_handler(CommandHandler("start", start))
    paolo_session.add_handler(CommandHandler("help", fetch_commands))
    paolo_session.add_handler(CommandHandler("film", film))
    paolo_session.add_handler(CommandHandler("upcoming", upcoming))

    paolo_session.add_handler(MessageHandler(filters.TEXT, talk))

    paolo_session.run_polling()
