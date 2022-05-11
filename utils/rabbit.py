import aio_pika
import json


async def queue_push(
        channel: aio_pika.Channel,
        message: str,
        telegram_user_id: int,
):
    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(
                dict(
                    message=message,
                    telegram_user_id=telegram_user_id,
                ),
            ).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key='push',
    )
