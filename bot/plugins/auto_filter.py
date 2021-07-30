import re
import logging
import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import ButtonDataInvalid, FloodWait

from bot.database import Database # pylint: disable=import-error
from bot.bot import Bot # pylint: disable=import-error
from bot import MT_CHANNEL_USERNAME, MASSAGE_PHOTO

FIND = {}
INVITE_LINK = {}
ACTIVE_CHATS = {}
db = Database()

@Bot.on_message(filters.text & filters.group & ~filters.bot, group=0)
async def auto_filter(bot, update):
    """
    A Funtion To Handle Incoming Text And Reply With Appropriate Results
    """
    group_id = update.chat.id

    if re.findall(r"((^\/|^,|^\.|^[\U0001F600-\U000E007F]).*)", update.text):
        return
    
    if ("https://" or "http://") in update.text:
        return
    
    query = re.sub(r"[1-2]\d{3}", "", update.text) # Targetting Only 1000 - 2999 😁
    
    if len(query) < 2:
        return
    
    results = []
    
    global ACTIVE_CHATS
    global FIND
    
    configs = await db.find_chat(group_id)
    achats = ACTIVE_CHATS[str(group_id)] if ACTIVE_CHATS.get(str(group_id)) else await db.find_active(group_id)
    ACTIVE_CHATS[str(group_id)] = achats
    
    if not configs:
        return
    
    allow_video = configs["types"]["video"]
    allow_audio = configs["types"]["audio"] 
    allow_document = configs["types"]["document"]
    
    max_pages = configs["configs"]["max_pages"] # maximum page result of a query
    pm_file_chat = configs["configs"]["pm_fchat"] # should file to be send from bot pm to user
    max_results = configs["configs"]["max_results"] # maximum total result of a query
    max_per_page = configs["configs"]["max_per_page"] # maximum buttom per page 
    show_invite = configs["configs"]["show_invite_link"] # should or not show active chat invite link
    
    show_invite = (False if pm_file_chat == True else show_invite) # turn show_invite to False if pm_file_chat is True
    
    filters = await db.get_filters(group_id, query)
    
    if filters:
        results.append(
                [
                    InlineKeyboardButton("🔆 𝘼𝙈𝙄𝙂𝙊 𝘾𝙄𝙉𝙀𝙈𝘼𝙎 🔆", url=f"https://t.me/{MT_CHANNEL_USERNAME}")
                ]
            )
        for filter in filters: # iterating through each files
            file_name = filter.get("file_name")
            file_type = filter.get("file_type")
            file_link = filter.get("file_link")
            file_size = int(filter.get("file_size", "0"))
            
            # from B to MiB
            
            if file_size < 1024:
                file_size = f"[{file_size} B]"
            elif file_size < (1024**2):
                file_size = f"[{str(round(file_size/1024, 2))} KB] "
            elif file_size < (1024**3):
                file_size = f"[{str(round(file_size/(1024**2), 2))} MB] "
            elif file_size < (1024**4):
                file_size = f"[{str(round(file_size/(1024**3), 2))} GB] "
            
            
            file_size = "" if file_size == ("[0 B]") else file_size
            
            # add emoji down below inside " " if you want..
            button_text = f"🎬{file_size} {file_name}"
            

            if file_type == "video":
                if allow_video: 
                    pass
                else:
                    continue
                
            elif file_type == "audio":
                if allow_audio:
                    pass
                else:
                    continue
                
            elif file_type == "document":
                if allow_document:
                    pass
                else:
                    continue
            
            if len(results) >= max_results:
                break
            
            if pm_file_chat: 
                unique_id = filter.get("unique_id")
                if not FIND.get("bot_details"):
                    try:
                        bot_= await bot.get_me()
                        FIND["bot_details"] = bot_
                    except FloodWait as e:
                        asyncio.sleep(e.x)
                        bot_= await bot.get_me()
                        FIND["bot_details"] = bot_
                
                bot_ = FIND.get("bot_details")
                file_link = f"https://t.me/{bot_.username}?start={unique_id}"
            
            results.append(
                [
                    InlineKeyboardButton(button_text, url=file_link)
                ]
            )
        
    else:
        return # return if no files found for that query
    

    if len(results) == 0: # double check
        return
    
    else:
    
        result = []
        # seperating total files into chunks to make as seperate pages
        result += [results[i * max_per_page :(i + 1) * max_per_page ] for i in range((len(results) + max_per_page - 1) // max_per_page )]
        len_result = len(result)
        len_results = len(results)
        results = None # Free Up Memory
        
        FIND[query] = {"results": result, "total_len": len_results, "max_pages": max_pages} # TrojanzHex's Idea Of Dicts😅

        # Add next buttin if page count is not equal to 1
        if len_result != 1:
            result[0].append(
                [
                    InlineKeyboardButton("𝙽𝚎𝚡𝚝»»»", callback_data=f"navigate(0|next|{query})")
                ]
            )
        
        # Just A Decaration
        result[0].append([
            InlineKeyboardButton(f"⭕ 𝙿𝚊𝚐𝚎 1/{len_result if len_result < max_pages else max_pages} ⭕", callback_data="ignore")
        ])
        
        
        # if show_invite is True Append invite link buttons
        if show_invite:
            
            ibuttons = []
            achatId = []
            await gen_invite_links(configs, group_id, bot, update)
            
            for x in achats["chats"] if isinstance(achats, dict) else achats:
                achatId.append(int(x["chat_id"])) if isinstance(x, dict) else achatId.append(x)

            ACTIVE_CHATS[str(group_id)] = achatId
            
            for y in INVITE_LINK.get(str(group_id)):
                
                chat_id = int(y["chat_id"])
                
                if chat_id not in achatId:
                    continue
                
                chat_name = y["chat_name"]
                invite_link = y["invite_link"]
                
                if ((len(ibuttons)%2) == 0):
                    ibuttons.append(
                        [
                            InlineKeyboardButton(f"⚜ {chat_name} ⚜", url=invite_link)
                        ]
                    )

                else:
                    ibuttons[-1].append(
                        InlineKeyboardButton(f"⚜ {chat_name} ⚜", url=invite_link)
                    )
                
            for x in ibuttons:
                result[0].insert(0, x) #Insert invite link buttons at first of page
                
            ibuttons = None # Free Up Memory...
            achatId = None
            
            
        reply_markup = InlineKeyboardMarkup(result[0])

        try:
            movie_name = message.input_str
        await message.edit(f"__searching IMDB for__ : `{movie_name}`")
        search_results = await _get(API_ONE_URL.format(theuserge=movie_name))
        srch_results = json.loads(search_results.text)
        first_movie = srch_results.get("d")[0]
        mov_title = first_movie.get("l")
        mov_imdb_id = first_movie.get("id")
        mov_link = f"https://www.imdb.com/title/{mov_imdb_id}"
        page2 = await _get(API_TWO_URL.format(imdbttid=mov_imdb_id))
        second_page_response = json.loads(page2.text)
        image_link = first_movie.get("i").get("imageUrl")
        mov_details = get_movie_details(second_page_response)
        director, writer, stars = get_credits_text(second_page_response)
        story_line = second_page_response.get("summary").get("plot", 'Not available')
        mov_country, mov_language = get_countries_and_languages(second_page_response)
        mov_rating = second_page_response.get("UserRating").get("description")
        des_ = f"""<b>Title🎬: </b><code>{mov_title}</code>

<b>More Info: </b><code>{mov_details}</code>
<b>Rating⭐: </b><code>{mov_rating}</code>
<b>Country🗺: </b><code>{mov_country}</code>
<b>Language: </b><code>{mov_language}</code>
<b>Cast Info🎗: </b>
  <b>Director📽: </b><code>{director}</code>
  <b>Writer📄: </b><code>{writer}</code>
  <b>Stars🎭: </b><code>{stars}</code>

<b>IMDB URL Link🔗: </b>{mov_link}

<b>Story Line : </b><em>{story_line}</em>"""
    except IndexError:
        await message.edit("Bruh, Plox enter **Valid movie name** kthx")
        return
    if len(des_) > 1024:
        des_ = des_[:1021] + "..."
    if os.path.exists(THUMB_PATH):
        optimize_image(THUMB_PATH)
        await message.client.send_photo(
            chat_id=message.chat.id,
            photo=THUMB_PATH,
            caption=des_,
            parse_mode="html"
        )
        await message.delete()
    elif image_link is not None:
        await message.edit("__downloading thumb ...__")
        image = image_link
        img_path = await pool.run_in_thread(
            wget.download
        )(image, os.path.join(Config.DOWN_PATH, 'imdb_thumb.jpg'))
        optimize_image(img_path)
        await message.client.send_photo(
            chat_id=message.chat.id,
            photo=img_path,
            caption=des_,
            parse_mode="html"
        )
        await message.delete()
        os.remove(img_path)
    else:
        await message.edit(des_, parse_mode="HTML")


def optimize_image(path):
    _image = Image.open(path)
    if _image.size[0] > 720:
        _image.resize((720, round(truediv(*_image.size[::-1]) * 720))).save(path, quality=95)


def get_movie_details(soup):
    mov_details = []
    inline = soup.get("Genres")
    if inline and len(inline) > 0:
        for io in inline:
            mov_details.append(io)
    tags = soup.get("duration")
    if tags:
        mov_details.append(tags)
    if mov_details and len(mov_details) > 1:
        mov_details_text = ' | '.join(mov_details)
    else:
        mov_details_text = mov_details[0] if mov_details else ''
    return mov_details_text


def get_countries_and_languages(soup):
    languages = soup.get("Language")
    countries = soup.get("CountryOfOrigin")
    lg_text = ""
    if languages:
        if len(languages) > 1:
            lg_text = ', '.join([lng["NAME"] for lng in languages])
        else:
            lg_text = languages[0]["NAME"]
    else:
        lg_text = "No Languages Found!"
    if countries:
        if len(countries) > 1:
            ct_text = ', '.join([ctn["NAME"] for ctn in countries])
        else:
            ct_text = countries[0]["NAME"]
    else:
        ct_text = "No Country Found!"
    return ct_text, lg_text


def get_credits_text(soup):
    pg = soup.get("sum_mary")
    direc = pg.get("Directors")
    writer = pg.get("Writers")
    actor = pg.get("Stars")
    if direc:
        if len(direc) > 1:
            director = ', '.join([x["NAME"] for x in direc])
        else:
            director = direc[0]["NAME"]
    else:
        director = "No Director Found!"
    if writer:
        if len(writer) > 1:
            writers = ', '.join([x["NAME"] for x in writer])
        else:
            writers = writer[0]["NAME"]
    else:
        writers = "No Writer Found!"
    if actor:
        if len(actor) > 1:
            actors = ', '.join([x["NAME"] for x in actor])
        else:
            actors = actor[0]["NAME"]
    else:
        actors = "No Actor Found!"
    return director, writers, actors


@pool.run_in_thread
def _get(url: str, attempts: int = 0) -> requests.Response:
    while True:
        abc = requests.get(url)
        if attempts > 5:
            raise IndexError
        if abc.status_code == 200:
            break
        attempts += 1
    return abc


        except ButtonDataInvalid:
            print(result[0])
        
        except Exception as e:
            print(e)


async def gen_invite_links(db, group_id, bot, update):
    """
    A Funtion To Generate Invite Links For All Active 
    Connected Chats In A Group
    """
    chats = db.get("chat_ids")
    global INVITE_LINK
    
    if INVITE_LINK.get(str(group_id)):
        return
    
    Links = []
    if chats:
        for x in chats:
            Name = x["chat_name"]
            
            if Name == None:
                continue
            
            chatId=int(x["chat_id"])
            
            Link = await bot.export_chat_invite_link(chatId)
            Links.append({"chat_id": chatId, "chat_name": Name, "invite_link": Link})

        INVITE_LINK[str(group_id)] = Links
    return 


async def recacher(group_id, ReCacheInvite=True, ReCacheActive=False, bot=Bot, update=Message):
    """
    A Funtion To rechase invite links and active chats of a specific chat
    """
    global INVITE_LINK, ACTIVE_CHATS

    if ReCacheInvite:
        if INVITE_LINK.get(str(group_id)):
            INVITE_LINK.pop(str(group_id))
        
        Links = []
        chats = await db.find_chat(group_id)
        chats = chats["chat_ids"]
        
        if chats:
            for x in chats:
                Name = x["chat_name"]
                chat_id = x["chat_id"]
                if (Name == None or chat_id == None):
                    continue
                
                chat_id = int(chat_id)
                
                Link = await bot.export_chat_invite_link(chat_id)
                Links.append({"chat_id": chat_id, "chat_name": Name, "invite_link": Link})

            INVITE_LINK[str(group_id)] = Links
    
    if ReCacheActive:
        
        if ACTIVE_CHATS.get(str(group_id)):
            ACTIVE_CHATS.pop(str(group_id))
        
        achats = await db.find_active(group_id)
        achatId = []
        if achats:
            for x in achats["chats"]:
                achatId.append(int(x["chat_id"]))
            
            ACTIVE_CHATS[str(group_id)] = achatId
    return 
