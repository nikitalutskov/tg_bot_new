import random
import sqlite3
import requests
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

print('Start telegram bot...')

# Создаем подключение к базе данных
conn = sqlite3.connect('english_bot.db')
cursor = conn.cursor()

# Создаем таблицы в базе данных
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        word_count INTEGER DEFAULT 0
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS words (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        word TEXT,
        translation TEXT,
        example TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS word_history (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        word_id INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (word_id) REFERENCES words (id)
    )
''')

# Инициализируем бота
state_storage = StateMemoryStorage()
token_bot = 'YOUR_BOT_TOKEN'
bot = TeleBot(token_bot, state_storage=state_storage)

known_users = []
userStep = {}
buttons = []


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()


def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        known_users.append(uid)
        userStep[uid] = 0
        print("New user detected, who hasn't used '/start' yet")
        return 0


@bot.message_handler(commands=['start'])
def start(message):
    cid = message.chat.id
    if cid not in known_users:
        known_users.append(cid)
        userStep[cid] = 0
        bot.send_message(cid, "Привет 👋 Давай попрактикуемся в английском языке. Тренировки можешь проходить в удобном для себя темпе. Причём у тебя есть возможность использовать тренажёр как конструктор и собирать свою собственную базу для обучения. Для этого воспользуйся инструментами 'Добавить слово ➕' или 'Удалить слово🔙'. Ну что, начнём ⬇️")


@bot.message_handler(commands=['cards'])
def create_cards(message):
    cid = message.chat.id
    if cid not in known_users:
        known_users.append(cid)
        userStep[cid] = 0
        bot.send_message(cid, "Привет 👋 Давай попрактикуемся в английском языке. Тренировки можешь проходить в удобном для себя темпе. Причём у тебя есть возможность использовать тренажёр как конструктор и собирать свою собственную базу для обучения. Для этого воспользуйся инструментами 'Добавить слово ➕' или 'Удалить слово🔙'. Ну что, начнём ⬇️")

    markup = types.ReplyKeyboardMarkup(row_width=2)
    target_word = 'Peace'
    translate = 'Мир'
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    others = ['Green', 'White', 'Hello', 'Car']
    other_words_btns = [types.KeyboardButton(word) for word in others]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])
    markup.add(*buttons)
    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.chat.id, MyStates.target_word)

    with bot.retrieve_data(message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = others


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    with bot.retrieve_data(message.chat.id) as data:
        target_word = data['target_word']
        cursor.execute('DELETE FROM words WHERE user_id=? AND word=?', (message.chat.id, target_word))
        conn.commit()
        bot.send_message(message.chat.id, f"Слово '{target_word}' успешно удалено из базы данных.")


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    userStep[cid] = 1
    bot.send_message(cid, "Введите новое слово и его перевод в формате 'слово - перевод'.")


@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 1)
def save_new_word(message):
    cid = message.chat.id
    userStep[cid] = 0
    word_data = message.text.split(' - ')
    if len(word_data) != 2:
        bot.send_message(cid, "Неправильный формат ввода. Пожалуйста, повторите попытку.")
        return
    word, translation = word_data
    example = get_word_example(word)
    cursor.execute('INSERT INTO words (user_id, word, translation, example) VALUES (?, ?, ?, ?)',
                   (cid, word, translation, example))
    conn.commit()
    cursor.execute('SELECT COUNT(*) FROM words WHERE user_id=?', (cid,))
    word_count = cursor.fetchone()[0]
    cursor.execute('UPDATE users SET word_count=? WHERE id=?', (word_count, cid))
    conn.commit()
    bot.send_message(cid, f"Слово '{word}' успешно добавлено в базу данных. Теперь у тебя {word_count} слов в словаре.")


def get_word_example(word):
    response = requests.get(f'https://api.dictionaryapi.dev/api/v2/entries/en/{word}')
    data = response.json()
    example = data[0]['meanings'][0]['definitions'][0]['example']
    return example


bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling(skip_pending=True)
