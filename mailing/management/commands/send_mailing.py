import logging
from django.core.management.base import BaseCommand
from mailing.models import Mailing
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Отправка рассылки"

    def handle(self, *args, **kwargs):
        mailings = Mailing.objects.filter(my_field=Mailing.STATUS_NEW)

        for mailing in mailings:
            recipients = mailing.recipient.all()
            for recipient in recipients:
                try:
                    send_mail(
                        subject=mailing.mail.subject,  # Предположим, что `Mail` имеет поле `subject`
                        message=mailing.mail.body,  # Предположим, что `Mail` имеет поле `body`
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[
                            recipient.email
                        ],  # Предположим, что `Recipient` имеет поле `email`
                    )
                    logger.info(
                        f"Письмо отправлено {recipient.email} для рассылки {mailing.id}"
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке письма {recipient.email}: {e}")

            # Если рассылка завершена, обновляем статус
            mailing.my_field = Mailing.STATUS_END
            mailing.save()

        logger.info("Все рассылки успешно обработаны.")
