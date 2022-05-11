import lgpio
import functools
import asyncio
import aio_pika
from time import sleep
from pydantic import BaseModel

from utils.config import get_config


class CONSTANTS:
    GERCONE_PIN = 17  # 0 is closed, 1 is opened
    LOCK_PIN = 23
    LGPIO_HANDLER = None


class PushMessage(BaseModel):
    cell_id: int
    is_sending: bool
    is_cell_message: bool = True
    telegram_user_id: int = 1
    message: str = ''


class GetMessage(BaseModel):
    cell_id: int
    is_sending: bool


async def handler(message: aio_pika.IncomingMessage, channel) -> None:
    async with message.process(ignore_processed=True):
        print('='*15)
        print('[*] Signal received')
        info = GetMessage.parse_raw(message.body)

        lgpio.gpio_write(CONSTANTS.LGPIO_HANDLER, CONSTANTS.LOCK_PIN, 1)
        print(f'[*] Lock is opened')
        
        print('[*] Waiting for cell openning')
        while not lgpio.gpio_read(CONSTANTS.LGPIO_HANDLER, CONSTANTS.GERCONE_PIN): pass
        print('[*] Cell is opened')

        lgpio.gpio_write(CONSTANTS.LGPIO_HANDLER, CONSTANTS.LOCK_PIN, 0)
        print('[*] Lock is closed')

        print('[*] Waiting for cell closing')
        while lgpio.gpio_read(CONSTANTS.LGPIO_HANDLER, CONSTANTS.GERCONE_PIN): pass
        print('[*] Cell is closed')


        push_message = PushMessage(cell_id=info.cell_id, is_sending=info.is_sending)
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=push_message.json().encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key='push',
        )

        print('[*] Push is sent')


async def setup():
    config = get_config()
    connection = await aio_pika.connect_robust(
        host=config.rmq.host,
        virtualhost=config.rmq.vhost,
        login=config.rmq.username,
        password=config.rmq.password.get_secret_value(),
        loop=loop,
    )
    channel = await connection.channel()

    queue  = await channel.declare_queue(
        'cell_reqeust',
    )
    patched_handler = functools.partial(handler, channel=channel)
    await queue.consume(patched_handler, no_ack=False)
    return connection, channel


if __name__ == '__main__':
    CONSTANTS.LGPIO_HANDLER = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_input(CONSTANTS.LGPIO_HANDLER, CONSTANTS.GERCONE_PIN)
    lgpio.gpio_claim_output(CONSTANTS.LGPIO_HANDLER, CONSTANTS.LOCK_PIN)

    loop = asyncio.new_event_loop()
    cn, _ = loop.run_until_complete(setup())
    try:    
        loop.run_forever()
    finally:
        print('CLOSING CONNECTION')
        lgpio.gpio_write(CONSTANTS.LGPIO_HANDLER, CONSTANTS.LOCK_PIN, 0)
        lgpio.gpiochip_close(CONSTANTS.LGPIO_HANDLER)
        loop.run_until_complete(cn.close())

