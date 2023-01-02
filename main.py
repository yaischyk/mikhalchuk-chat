import re
from datetime import date
import asyncio
from pymongo import MongoClient
from typing import Optional
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ChatPermissions
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.utils.keyboard import CallbackData
from aiogram.methods.send_message import SendMessage
from aiogram.fsm.context import FSMContext 
from aiogram.filters.state import StatesGroup, State

client = MongoClient('mongodb+srv://admin:DyfbnQ8j0KSRMKFe@cluster0.hrd7w1m.mongodb.net/manager')
db = client['manager']

bot = Bot(token="5771365422:AAGssIOkoEJqAEsHZif8Cj97JteMkcHzFks")
BOT_ID = 5771365422
dp = Dispatcher()


# DELETE MESSAGES BY KEYS
async def checkMessage(message):
    try:
        data = db.messages.find({
            "is_sent": False
        })

        for x in data:
            try:
                id = x['_id']
                chat_id = str(int(x['chat_id']))
                message = x['message']
                print(chat_id)
                await bot.send_message(chat_id=chat_id, text=message)
                db.messages.update_one({'_id': id}, {'$set': {'is_sent': True}})
            except Exception as e:
                print(e)
    except Exception as e:
        print(e)

    try:
        try:
            msg = message.__dict__
            msg = message.__dict__
            chat_id = msg["chat"].__dict__["id"]
            user_id = msg["from_user"].__dict__["id"]
        except Exception as e:
            print(e)
        
        if msg['reply_to_message']:
            who_replied = msg['from_user'].__dict__['id']
            whose_reply = msg['reply_to_message'].__dict__['from_user'].__dict__['id']
            
            if whose_reply == BOT_ID:
                return False

            # Get governs
            is_governs = db.who_governs.find_one({"chat_id": chat_id, "user_id": who_replied})

            if is_governs:
                get_conditions = db.rating_conditions.find({"chat_id": chat_id})
                print(get_conditions)
                for x in get_conditions:
                    if x['condition'] in msg['text']:
                        print('134')
                        rating = x['rating']
                        # Check user in table
                        user_rating = db.user_rating.find_one({"chat_id": chat_id, "user_id": whose_reply})
                        if not user_rating:
                            db.user_rating.insert_one({"chat_id": chat_id, "user_id": whose_reply, "rating": 0})
                        # Get & update rating
                        get_rating = db.user_rating.find_one({"chat_id": chat_id, "user_id": whose_reply})
                        new_rating = get_rating['rating'] + rating
                        db.user_rating.update_one({"chat_id": chat_id, "user_id": whose_reply}, {'$set': {"rating": new_rating}})

                        # Send message
                        reply_to = msg['reply_to_message'].__dict__['message_id']

                        new_message_text = None
                        if rating > 0:
                            new_message_text = '☺️ Вам начислено '
                        else:
                            new_message_text = '🫡 У вас сняли '
                        new_message_text = new_message_text + str(rating) + ' рейтинга. Текущий баланс: ' + str(new_rating) + ' баллов.'
                        await bot.send_message(chat_id=chat_id, reply_to_message_id=reply_to, text=new_message_text)
        
        if msg['new_chat_members']:
            # GET REQUEST
            try:
                # Restrict member
                await bot.restrict_chat_member(
                    chat_id, 
                    user_id,  
                    ChatPermissions(can_send_messages=False)
                )

                welcome_message = db.welcome_messages.find_one({"chat_id": chat_id})

                builder = InlineKeyboardBuilder()
                # Send message
                builder.add(
                    types.InlineKeyboardButton(
                        text = welcome_message["inline_button_text"], 
                        callback_data = user_id
                    )
                )

                s = welcome_message['text']
                msgsent = 'Привет 👋\n\nДобро пожаловать в <a href="https://t.me/mykhalchuk_chat">«Павел Михальчук Чат»</a>!\nПравила чата - <a href="https://telegra.ph/Pravila-Pavel-Mihalchuk--CHat-11-11">клик</a>'

                try:
                    name = re.search(r'\{(.+?)\}', s)[1]

                    first_name = ' новый'
                    first_name = msg["from_user"].__dict__["first_name"]
                    print(first_name)
                    parsed1 = s.split('{')
                    print(parsed1)
                    parsed2 = s.split('}')
                    
                    msgsent = parsed1[0] + first_name + parsed2[1]
                except Exception as e:
                    msgsent = s

                print(msgsent)

                sent_message = await message.answer(msgsent, disable_web_page_preview=True, parse_mode='html', reply_markup=builder.as_markup())
                sent_message = sent_message.__dict__

                # Add members to database
                db.new_chat_members.insert_one(

                    {"chat_id": chat_id, "user_id": user_id, "username": "@" + msg["from_user"].__dict__["username"], "sent_message": {"message_id": sent_message['message_id']}}
                )
                builder = InlineKeyboardBuilder()

                await asyncio.sleep(60)
                await bot.restrict_chat_member(
                    chat_id, 
                    user_id,  
                    ChatPermissions(can_send_messages=True)
                )
                sent_msg_id = db.new_chat_members.find(
                    {"chat_id": chat_id, "user_id": user_id}
                ).sort("_id", -1)
                msg_id = sent_msg_id[0]['sent_message']['message_id']
                await bot.delete_message(chat_id, msg_id)
            except Exception as e:
                print(e)
        else:
            chat_id = msg["chat"].__dict__["id"]
            message_id = msg["message_id"]
            user_id = msg["from_user"].__dict__["id"]

            white_list = db.white_list.find_one({"chat_id": int(chat_id), "user_id": int(user_id)})
            print(white_list)
            print(user_id)
            print(chat_id)
            if not white_list:
                print('not in white list')
                filter_keys = db.filter_keys.find({"chat_id": int(chat_id)})
                for x in filter_keys:
                    x = x["key"]
                    if x in message.text:
                        await bot.delete_message(chat_id, message_id)
                        try:
                            db.deleted_messages.insert_one({'message': message.text, 'date': str(date.today())})
                        except Exception as e:
                            print(e)
    except Exception as e:
        print(e)

@dp.message()
async def message_handler(message: types.Message):
    msg = message.__dict__
    if msg["chat"].__dict__["type"] == 'supergroup':
        await checkMessage(message)

@dp.edited_message()
async def edited_message_handler(edited_message: types.Message):
    msg = edited_message.__dict__
    if msg["chat"].__dict__["type"] == 'supergroup':
        await checkMessage(edited_message)

# CALLBACK
@dp.callback_query()
async def agree(callback: types.CallbackQuery):
    try: 
        # Callback data
        callback_data = callback.__dict__['data']
        # Chat ID
        chat_id = callback.message.__dict__['chat'].__dict__['id']

        user_id = callback.__dict__['from_user'].__dict__['id']

        # Get params
        welcome_message = db.welcome_messages.find_one({"chat_id": chat_id})

        if int(callback_data) == user_id:
            await callback.answer(welcome_message['callback_answer']['ok'])
            # Restrict member
            await bot.restrict_chat_member(
                chat_id, 
                user_id,  
                ChatPermissions(can_send_messages=True)
            )

            # Delete sent message
            sent_msg_id = db.new_chat_members.find(
                {"chat_id": chat_id, "user_id": user_id}
            ).sort("_id", -1)

            msg_id = sent_msg_id[0]['sent_message']['message_id']
            await bot.delete_message(chat_id, msg_id)
        else:
            await callback.answer(welcome_message['callback_answer']['error'])
    except Exception as e:
        print(e)


async def main():
    await dp.start_polling(bot)
    

if __name__ == "__main__":
    asyncio.run(main())
