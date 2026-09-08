from aiogram import F
from aiogram.enums import ChatType

PRIVATE = F.chat.type == ChatType.PRIVATE
GROUP = F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP})
CHANNEL = F.chat.type == ChatType.CHANNEL

# For callback queries the chat lives on the message.
CB_PRIVATE = F.message.chat.type == ChatType.PRIVATE
CB_GROUP = F.message.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP})
