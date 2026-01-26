# Other imports
import io
import os
import json
import asyncio
from asyncio import run_coroutine_threadsafe
from thefuzz import fuzz,  process

# LineOA imports
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage, ImageSendMessage, FollowEvent

# FastAPI imports
from fastapi import FastAPI, Request, Header, HTTPException, WebSocket, WebSocketDisconnect
import uvicorn

# Database module imports
from SqlDB import init_db, update_user_points

# Image processing imports
from ultralytics import YOLO
from PIL import Image

# Load trained model
model = YOLO("trainedModel.pt")

# Create folders for saving images based on confidence
LowConfidenceImg_folder = "Low_Confidence_Images"
if not os.path.exists(LowConfidenceImg_folder):
    os.makedirs(LowConfidenceImg_folder)
    
HightConfidenceImg_folder = "Hight_Confidence_Images"
if not os.path.exists(HightConfidenceImg_folder):
    os.makedirs(HightConfidenceImg_folder)

# Image classification function
def classify_Image(ImageBytes):
    
    try:
        # Image preprocessing on RAM
        Img = Image.open(io.BytesIO(ImageBytes)).convert('RGB')

        # Prediction
        Img = Img.resize((224, 224))
        Results = model(Img, verbose=False)

        # Check results
        if not Results or not hasattr(Results[0], 'probs') or Results[0].probs is None:
            print("Error: No classification results.")
            return None
        
        if Results[0].probs.top1conf.item() < 0.7:
            LowConfImg_Path = os.path.join(LowConfidenceImg_folder, f"{Results[0].names[Results[0].probs.top1]}_{round(Results[0].probs.top1conf.item(), 2)}.png")
            Img.save(LowConfImg_Path)
            print("Low confidence in classification.")
            return None

        # Return confidence class above threshold 0.7 or 70%
        HightConfImg_Path = os.path.join(HightConfidenceImg_folder, f"{Results[0].names[Results[0].probs.top1]}_{round(Results[0].probs.top1conf.item(), 2)}.png")
        Img.save(HightConfImg_Path)
        ClassIndex = Results[0].probs.top1
        ClassName = Results[0].names[ClassIndex]
        return ClassName

    except Exception as e:
        print(f"Error during classification: {e}")
        return None

# Bin Mapping
try:
    with open('BinMapping.json', 'r', encoding='utf-8') as binmapping_file:
        BinMapping = json.load(binmapping_file)
except Exception as e:
    print(f"Error loading BinMapping.json: {e}")

# Reply Message Mapping
try:
    with open('Replymsg.json', 'r', encoding='utf-8') as replymsg_file:
        Replymsg = json.load(replymsg_file)
except Exception as e:
    print(f"Error loading Replymsg.json: {e}")

# Keywords Mapping
try:
    with open('Keywords.json', 'r', encoding='utf-8') as Keywords_file:

        Keywords = json.load(Keywords_file)

except Exception as e:      
    print(f"Error loading Keywords.json: {e}")

# Color to number bin mapping function
def find_bin(Text: str):
    highest_score = 0
    phrases_match = None
    bin_color = None

    for key, phrases in Keywords.items():
        match, score = process.extractOne(Text, phrases, scorer=fuzz.token_sort_ratio)
        if score > highest_score:
            highest_score = score
            phrases_match = match
            bin_color = key
    
    if highest_score >= 80:
        return bin_color, phrases_match, highest_score
    else:
        return None, None, None

# Rich menu response
def RichMenuResponse(Text: str):
    if Text == "วิธีใช้":
        return [
            ImageSendMessage(
            original_content_url="https://raw.githubusercontent.com/seh83555/BinPj/refs/heads/main/PreviewPics/Guide_1.png",
            preview_image_url="https://raw.githubusercontent.com/seh83555/BinPj/refs/heads/main/PreviewPics/Guide_1.png"
        ),
            ImageSendMessage(
            original_content_url="https://raw.githubusercontent.com/seh83555/BinPj/refs/heads/main/PreviewPics/Guide_2.png",
            preview_image_url="https://raw.githubusercontent.com/seh83555/BinPj/refs/heads/main/PreviewPics/Guide_2.png"
        )]
    elif Text == "แลกของรางวัล":
        return ImageSendMessage(
            original_content_url="https://raw.githubusercontent.com/seh83555/BinPj/refs/heads/main/PreviewPics/Bonus.png",
            preview_image_url="https://raw.githubusercontent.com/seh83555/BinPj/refs/heads/main/PreviewPics/Bonus.png"
        )
    else:
        return None

# Initialize database
init_db()

# Initialize Line Bot API and Token
try:
    with open('LINETOKEN.json', 'r') as token_file:
        tokens = json.load(token_file)

        LINE_CHANNEL_ACCESS_TOKEN = tokens.get("LINE_CHANNEL_ACCESS_TOKEN")
        LINE_CHANNEL_SECRET = tokens.get("LINE_CHANNEL_SECRET")

except Exception as e:
    print(f"Error loading LINETOKEN.json: {e}")

LineBotApi = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
Handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Initialize FastAPI app
app = FastAPI()

# Class Connection manager for WebSocket
class ConnectionManager:
    def __init__(self):
        self.Connection: WebSocket = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.Connection = websocket
        print("ESP32 Connected via WebSocket!")

    def disconnect(self):
        self.Connection = None
        print("ESP32 Disconnected")

    async def send_command(self, message: str):
        if self.Connection:
            await self.Connection.send_text(message)
            print(f"Sent to ESP32: {message}")
        else:
            print("ESP32 is not connected, cannot send command")

# Initialize Connection Manager
Device = ConnectionManager()

# WebSocket endpoint for device connection
@app.websocket("/websocket")
async def websocket_endpoint(websocket: WebSocket):

    await Device.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        Device.disconnect()


# Line endpoint
@app.post("/")
async def callback(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()
    try:
        Handler.handle(body.decode("utf-8"), x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "OK"

# Follow event handler (when user adds the bot as a friend)
@Handler.add(FollowEvent)
def FollowHandler(Event):
    LineBotApi.reply_message(Event.reply_token,TextSendMessage(Replymsg.get("WelcomeMsg")))

# Handle text messages
@Handler.add(MessageEvent, message=TextMessage)
def TextHandler(Event):
    
    UserId = Event.source.user_id
    userText = Event.message.text

    # if usertext matches rich menu commands
    RichMenuResponseessage = RichMenuResponse(userText)
    if RichMenuResponseessage:
        LineBotApi.reply_message(Event.reply_token, RichMenuResponseessage)
        return

    bin_color, phrases_match, highest_score = find_bin(userText)
    
    if highest_score is not None and highest_score >= 80:

        BinNumber = BinMapping.get(bin_color, None)
        if BinNumber is not None and BinNumber >= 1 and BinNumber <= 4:

            loop = asyncio.get_event_loop()
            run_coroutine_threadsafe(Device.send_command(str(BinNumber)), loop)
            TotalPoints, TodayPoints = update_user_points(UserId, 10)

        # Reply to user
        LineBotApi.reply_message(Event.reply_token,TextSendMessage(text=Replymsg.get(str(BinNumber)) + f"\n\nคุณได้รับแต้ม {TodayPoints}/50 วันนี้\nแต้มสะสมทั้งหมด : {TotalPoints}"))
    else:
        LineBotApi.reply_message(Event.reply_token,TextSendMessage(text=Replymsg.get("ErrorMsg")))

# Handle image messages
@Handler.add(MessageEvent, message=ImageMessage)
def ImageHandler(Event):

    UserId = Event.source.user_id
    MessageId = Event.message.id

    ImageContent = LineBotApi.get_message_content(MessageId)
    ImageBytes = b"".join([chunk for chunk in ImageContent.iter_content()])

    objectName = classify_Image(ImageBytes)
    if objectName:

        bin_color, phrases_match, highest_score = find_bin(objectName)

        if highest_score is None:
            LineBotApi.reply_message(Event.reply_token,TextSendMessage(text=Replymsg.get("ErrorMsg")))
            return
        
        BinNumber = BinMapping.get(bin_color, None)
        if BinNumber is not None and BinNumber >= 1 and BinNumber <= 4:
            loop = asyncio.get_event_loop()
            run_coroutine_threadsafe(Device.send_command(str(BinNumber)), loop)
            TotalPoints, TodayPoints = update_user_points(UserId, 10)

        # Reply to user
        LineBotApi.reply_message(Event.reply_token,TextSendMessage(text=Replymsg.get(str(BinNumber)) + f"\n\nคุณได้รับแต้ม {TodayPoints}/50 วันนี้\nแต้มสะสมทั้งหมด : {TotalPoints}"))
    else:
        LineBotApi.reply_message(Event.reply_token,TextSendMessage(text=Replymsg.get("ErrorMsg")))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)