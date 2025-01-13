import PIL.Image
import telebot
from PIL import Image
import PIL.ImageOps 
import io
from telebot import types
from telebot.types import Message
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN_BOT = os.getenv('TOKEN_BOT')

TOKEN = TOKEN_BOT
bot = telebot.TeleBot(TOKEN)

user_states = {}  # тут будем хранить информацию о действиях пользователя

# набор символов из которых составляем изображение
ASCII_CHARS = '@%#*+=-:. '


def resize_image(image, new_width=100):
    '''
    Изменяет размер изображения с сохранением пропорций
    '''
    width, height = image.size
    ratio = height / width
    new_height = int(new_width * ratio)
    return image.resize((new_width, new_height))


def grayify(image):
    '''
    Преобразует цветное изображение в оттенки серого.
    '''
    return image.convert("L")


def image_to_ascii(image_stream, ASCII_CHARS, new_width=40):
    '''
    Основная функция для преобразования изображения в ASCII-арт. 
    Изменяет размер, преобразует в градации серого и затем в строку ASCII-символов.
    '''
    # Переводим в оттенки серого
    image = Image.open(image_stream).convert('L')

    # меняем размер сохраняя отношение сторон
    width, height = image.size
    aspect_ratio = height / float(width)
    new_height = int(
        aspect_ratio * new_width * 0.55)  # 0,55 так как буквы выше чем шире
    img_resized = image.resize((new_width, new_height))

    img_str = pixels_to_ascii(img_resized, ASCII_CHARS)
    img_width = img_resized.width

    max_characters = 4000 - (new_width + 1)
    max_rows = max_characters // (new_width + 1)

    ascii_art = ""
    for i in range(0, min(max_rows * img_width, len(img_str)), img_width):
        ascii_art += img_str[i:i + img_width] + "\n"

    return ascii_art


def pixels_to_ascii(image, USE_ASCII_CHARS):
    '''
    Конвертирует пиксели изображения в градациях серого в строку ASCII-символов, используя предопределенную строку ASCII_CHARS
    '''
    pixels = image.getdata()
    characters = ""
    for pixel in pixels:
        characters += USE_ASCII_CHARS[pixel * len(USE_ASCII_CHARS) // 256]
    return characters


# Огрубляем изображение
def pixelate_image(image, pixel_size):
    '''
    Принимает изображение и размер пикселя.
    Уменьшает изображение до размера, где один пиксель представляет большую область, затем увеличивает обратно, создавая пиксельный эффект.
    '''
    image = image.resize(
        (image.size[0] // pixel_size, image.size[1] // pixel_size),
        Image.NEAREST
    )
    image = image.resize(
        (image.size[0] * pixel_size, image.size[1] * pixel_size),
        Image.NEAREST
    )
    return image


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    '''
    Предлагает пользователю ввести свой набор ASCII символов
    '''
    bot.reply_to(message, "Enter the set using the symbol: ")

@bot.message_handler(content_types=['photo'])
def handle_photo(message: Message):
    '''
    Предлагает пользователю выбрать стиль преобразования
    '''
    bot.reply_to(message, "I got your photo! Please choose what you'd like to do with it.",
                 reply_markup=get_options_keyboard())
    user_states[message.chat.id] = {'photo': message.photo[-1].file_id}
    

@bot.message_handler(content_types=["text"])
def get_ascii_simbol(message: Message):
    '''
    Изменяет набор ASCII символов и предлагает отправить фото для преобразования
    '''
    global ASCII_CHARS
    ASCII_CHARS = message.text
    bot.reply_to(message, "Send me an image, and I'll provide options for you!")


def get_options_keyboard():
    '''
    Создаёт клавиатуру и возвращает её объект
    '''
    keyboard = types.InlineKeyboardMarkup()
    pixelate_btn = types.InlineKeyboardButton("Pixelate", callback_data="pixelate")
    ascii_btn = types.InlineKeyboardButton("ASCII Art", callback_data="ascii")
    enver_color = types.InlineKeyboardButton("Invers Colors", callback_data='invert_color') # Кнопка для инверсии цвета изображения
    horisontal_image = types.InlineKeyboardButton('Horizontal reflection', callback_data='horiz_reflect') # Для горизонтального отражения фотографии
    vertical_image = types.InlineKeyboardButton('Vertical reflection', callback_data='vertical_reflect') # Для вертикального отражения фотографии
    keyboard.add(pixelate_btn, ascii_btn).add(enver_color).add(horisontal_image, vertical_image)
    return keyboard


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    '''
    Обрабатывает значения полученные с клавиатуры
    '''
    if call.data == "pixelate":
        bot.answer_callback_query(call.id, "Pixelating your image...")
        pixelate_and_send(call.message)
    elif call.data == "ascii":
        bot.answer_callback_query(call.id, "Converting your image to ASCII art...")
        ascii_and_send(call.message, ASCII_CHARS) # Передать в эту функцию набор аскии символов
    elif call.data == 'invert_color':
        bot.answer_callback_query(call.id, "Inverted image...")
        inversing_colors(call.message)
    elif call.data == 'horiz_reflect':
        mirror_image(message=call.message, transponse='HORIZONTAL')
    elif call.data == 'vertical_reflect':
        mirror_image(message=call.message, transponse='VERTICAL')


def mirror_image(message: Message, transponse: str):
    '''
    transponse - принимает два аргумента для горизонтального и вертикального отображения
    Функция для горизонтального отображения фотографии
    '''
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)
    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    if transponse == 'HORIZONTAL':
        horisontal_reflect = image.transpose(method=Image.FLIP_TOP_BOTTOM)
        output_stream = io.BytesIO()
        horisontal_reflect.save(output_stream, format="JPEG")
        output_stream.seek(0)
        bot.send_photo(message.chat.id, output_stream, caption='Horizontal reflection')
        return 0
    elif transponse == 'VERTICAL':
        horisontal_reflect = image.transpose(method=Image.FLIP_LEFT_RIGHT )
        output_stream = io.BytesIO()
        horisontal_reflect.save(output_stream, format="JPEG")
        output_stream.seek(0)
        bot.send_photo(message.chat.id, output_stream, caption='Vertical reflection')
        return 0

def inversing_colors(message: Message):
    '''
    Функция инвертирует цвет изображения
    '''
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    inversing_image = PIL.ImageOps.invert(image)

    output_stream = io.BytesIO()
    inversing_image.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)

def pixelate_and_send(message):
    '''
    Пикселизирует изображение и отправляет его обратно пользователю.
    '''
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    pixelated = pixelate_image(image, 20)

    output_stream = io.BytesIO()
    pixelated.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


def ascii_and_send(message, ASCII_CHARS_USER):
    '''
    Преобразует изображение в ASCII-арт и отправляет результат в виде текстового сообщения.
    '''
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    ascii_art = image_to_ascii(image_stream, ASCII_CHARS_USER)
    bot.send_message(message.chat.id, f"```\n{ascii_art}\n```", parse_mode="MarkdownV2")


bot.polling(none_stop=True)