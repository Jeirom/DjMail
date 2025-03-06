import logging

from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    TemplateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from mailing.forms import MailForm, RecipientForm, MailingForm
from mailing.models import *
from mailing.services import send_a_message
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

# Настройка логирования
logger = logging.getLogger(__name__)


# Классы представления для Mailing по принципу CRUD
# noinspection PyUnresolvedReferences
@method_decorator(
    cache_page(60 * 15), name="dispatch"
)  # Кешировать представление на 15 минут
class MailingListView(ListView):
    """
    Представление для списка рассылок, с кэшированием данных на 15 минут.

    Модель: Mailing
    Шаблон: "home.html"
    Контекст: 'mailings' - список рассылок текущего пользователя.
    """

    model = Mailing
    template_name = "home.html"
    context_object_name = "mailings"

    def get_context_data(self, **kwargs):
        """
        Получает данные контекста для шаблона.

        Если пользователь аутентифицирован, получает информацию о рассылках из кэша,
        в противном случае инициализирует значения для анонимного пользователя.

        :param kwargs: Дополнительные аргументы для передачи.
        :return: Словарь с данными контекста для шаблона.
        """
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            # Идентификатор кеша можно формировать на основе пользователя
            cache_key = f"user_{self.request.user.id}_mailing_data"
            cached_data = cache.get(cache_key)

            if cached_data is None:
                # Если данные не закешированы, получаем их из базы данных
                cached_data = {
                    "mailing_all": Mailing.objects.filter(
                        owner=self.request.user
                    ).count(),
                    "status_started": Mailing.objects.filter(
                        owner=self.request.user, my_field=Mailing.STATUS_STARTED
                    ).count(),
                    "recipient_all": Recipient.objects.filter(
                        owner=self.request.user
                    ).count(),
                    "status_ok": TryRecipient.objects.filter(
                        owner=self.request.user, status="Успешно"
                    ).count(),
                    "status_error": TryRecipient.objects.filter(
                        owner=self.request.user, status="Не успешно"
                    ).count(),
                    "sum_recipient": TryRecipient.objects.filter(
                        owner=self.request.user
                    ).count(),
                }
                # Сохраняем данные в кеш на 15 минут
                cache.set(cache_key, cached_data, 60 * 15)

            context.update(cached_data)
        else:
            context["mailing_all"] = 0
            context["status_started"] = 0
            context["recipient_all"] = 0
            context["status_ok"] = 0
            context["status_error"] = 0
            context["sum_recipient"] = 0

        return context

    def get_queryset(self):
        """Возвращает все объекты рассылок владельца пользователя."""
        if self.request.user.is_authenticated:
            return Mailing.objects.filter(owner=self.request.user)
        else:
            return Mailing.objects.none()

    def post(self, request, *args, **kwargs):
        """Обрабатывает POST запрос для отправки сообщения."""
        mailing_id = request.POST.get("mailing_id")
        mailing = get_object_or_404(Mailing, id=mailing_id, owner=request.user)
        send_a_message(mailing)

        return redirect("mailing:home")


# noinspection PyUnresolvedReferences
@method_decorator(
    cache_page(60 * 15), name="dispatch"
)  # Кешировать представление на 15 минут
class MailingDetailView(LoginRequiredMixin, DetailView):
    """
    Представление для детальной информации о рассылке.

    Модель: Mailing
    Шаблон: "mailing_detail.html"
    """

    model = Mailing
    template_name = "mailing_detail.html"

    def get_context_data(self, **kwargs):
        """
        Получает данные контекста для детального просмотра рассылки.

        :param kwargs: Дополнительные аргументы для передачи.
        :return: Словарь с данными контекста для шаблона.
        """
        context = super().get_context_data(**kwargs)
        context["recipients"] = self.object.recipient.all()
        context["tryrecipients"] = TryRecipient.objects.filter(
            recipient__in=context["recipients"]
        )

        return context

    def get_queryset(self):
        """Возвращает все объекты рассылок владельца пользователя."""
        if self.request.user.is_authenticated:
            return Mailing.objects.filter(owner=self.request.user)
        else:
            return Mailing.objects.none()


class SendMessageDetailView(DetailView):
    """
    Представление для отправки сообщения о рассылке.

    Модель: Mailing
    Шаблон: "send_handmade.html"
    """

    model = Mailing
    template_name = "send_handmade.html"

    def post(self, request, *args, **kwargs):
        mailing = self.get_object()
        send_a_message(mailing)
        return redirect("mailing:home")


# noinspection PyUnresolvedReferences
@method_decorator(
    cache_page(60 * 15), name="dispatch"
)  # Кешировать представление на 15 минут
class CombinedTemplateView(TemplateView):
    """
    Отображает шаблон с данными о рассылках, письмах и получателях.

    Attributes:
        model (Mailing): Модель для рассылок.
        template_name (str): Имя шаблона для отображения.
    """

    model = Mailing
    template_name = "mailing.html"

    def get_context_data(self, **kwargs) -> dict:
        """
        Получает данные контекста для отображения шаблона.

        Args:
            **kwargs: Дополнительные аргументы.

        Returns:
            dict: Словарь с данными о рассылках, письмах и получателях.
        """
        context = super().get_context_data(**kwargs)
        context["mailings"] = Mailing.objects.all()
        context["mails"] = Mail.objects.all()
        context["recipients"] = Recipient.objects.all()
        return context

    def get_queryset(self):
        """
        Получает набор объектов рассылок для авторизованного пользователя.

        Returns:
            QuerySet: Набор рассылок для текущего пользователя или пустой набор.
        """
        if self.request.user.is_authenticated:
            return Mailing.objects.filter(owner=self.request.user)
        else:
            return Mailing.objects.none()


@method_decorator(
    cache_page(60 * 15), name="dispatch"
)  # Кешировать представление на 15 минут
class MailingCreateView(LoginRequiredMixin, CreateView):
    """
    Представление для создания новой рассылки.

    Attributes:
        model (Mailing): Модель для рассылок.
        form_class (MailingForm): Форма для создания рассылки.
        success_url (str): URL для перенаправления после успешного создания.
        template_name (str): Имя шаблона для отображения.
    """

    model = Mailing
    form_class = MailingForm
    success_url = reverse_lazy("mailing:mailing")
    template_name = "create.html"

    def get_form_kwargs(self) -> dict:
        """
        Получает аргументы для формы.

        Returns:
            dict: Аргументы для инициализации формы, включая текущего пользователя.
        """
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user  # Передаем текущего пользователя в форму
        return kwargs

    def form_valid(self, form) -> HttpResponse:
        """
        Обрабатывает валидные данные формы.

        Args:
            form (MailingForm): Валидированная форма для создания рассылки.

        Returns:
            HttpResponse: Ответ с редиректом на `success_url`.
        """
        # Устанавливаем владельца на текущего авторизованного пользователя
        form.instance.owner = self.request.user

        # Создаем объект Mailing
        mailing = form.save()

        # Отправляем сообщение получателям
        send_a_message(mailing)
        return super().form_valid(form)


@method_decorator(
    cache_page(60 * 15), name="dispatch"
)  # Кешировать представление на 15 минут
class MailingUpdateView(LoginRequiredMixin, UpdateView):
    """
    Представление для редактирования существующей рассылки.

    Attributes:
        model (Mailing): Модель для рассылок.
        template_name (str): Имя шаблона для отображения.
        success_url (str): URL для перенаправления после успешного редактирования.
    """

    def get_form_class(self):
        return MailingForm

    # def form_valid(self, form):
    #     """ При указании статуса "Завершена", устанавливать endDt """


class MailingDeleteView(LoginRequiredMixin, DeleteView):
    """View для удаления рассылки."""

    model = Mailing
    template_name = "delete.html"
    success_url = reverse_lazy("mailing:mailing")


class TryRecipientCreateView(CreateView):
    """View для создания нового получателя рассылки."""

    model = TryRecipient
    success_url = reverse_lazy("mailing:home")
    # template_name = 'create.html'


class TryRecipientDetailView(LoginRequiredMixin, DetailView):
    """View для отображения деталей получателя рассылки."""

    model = TryRecipient

    def get_queryset(self):
        """Получает только те посты, которые создал текущий пользователь."""
        try:
            return TryRecipient.objects.filter(owner=self.request.user)
        except Exception as e:
            logger.info(f"Произошла такая ошибка: \n {e}")
            return (
                TryRecipient.objects.none()
            )  # Возвращаем пустой QuerySet в случае ошибки


class TryRecipientListView(LoginRequiredMixin, ListView):
    """View для списка получателей рассылки."""

    model = TryRecipient
    template_name = "try_recipient.html"

    def get_context_data(self, **kwargs):
        """Добавляет всех получателей, связанных с текущим пользователем, в контекст."""
        context = super().get_context_data(**kwargs)
        context["try_recipients"] = TryRecipient.objects.filter(owner=self.request.user)
        return context

    def get_queryset(self):
        """Получает только те посты, которые создал текущий пользователь."""
        try:
            return TryRecipient.objects.filter(owner=self.request.user)
        except Exception as e:
            logger.info(f"Произошла такая ошибка: \n {e}")
            return (
                TryRecipient.objects.none()
            )  # Возвращаем пустой QuerySet в случае ошибки


class TryRecipientUpdateView(LoginRequiredMixin, UpdateView):
    """View для обновления данных получателя рассылки."""

    model = TryRecipient
    template_name = "editing.html"


class TryRecipientDeleteView(LoginRequiredMixin, DeleteView):
    """View для удаления TryRecipient.

    Атрибуты:
        model: Модель TryRecipient.
        template_name: Шаблон для удаления TryRecipient.
    """

    model = TryRecipient
    template_name = "delete.html"


class RecipientCreateView(LoginRequiredMixin, CreateView):
    """View для создания Recipient.

    Атрибуты:
        model: Модель Recipient.
        form_class: Форма для создания Recipient.
        success_url: URL для перенаправления после успешного создания.
        template_name: Шаблон для создания Recipient.
    """

    model = Recipient
    form_class = RecipientForm
    success_url = reverse_lazy("mailing:mailing")
    template_name = "create.html"

    def form_valid(self, form) -> str:
        """Обрабатывает допустимую форму.

        Аргументы:
            form: Форма, которую необходимо обработать.

        Возвращает:
            str: Результат обработки формы.
        """
        form.instance.owner = (
            self.request.user
        )  # Устанавливаем владельца на текущего авторизованного пользователя
        return super().form_valid(form)

    def get_form_class(self) -> type:
        """Возвращает класс формы.

        Возвращает:
            type: Класс формы для Recipient.
        """
        return RecipientForm


class RecipientDetailView(LoginRequiredMixin, DetailView):
    """View для отображения деталей Recipient.

    Атрибуты:
        model: Модель Recipient.
        template_name: Шаблон для отображения деталей Recipient.
    """

    model = Recipient
    template_name = "mailing.html"

    def get_queryset(self) -> Recipient:
        """Определяет queryset для текущего пользователя.

        Возвращает:
            Recipient: Записи о получателе, принадлежащие текущему пользователю.
        """
        if self.request.user.is_authenticated:
            return Recipient.objects.filter(owner=self.request.user)
        return Recipient.objects.none()


class RecipientListView(LoginRequiredMixin, ListView):
    """View для отображения списка Recipient.

    Атрибуты:
        model: Модель Recipient.
        template_name: Шаблон для отображения списка Recipient.
        context_object_name: Имя контекстного объекта.
    """

    model = Recipient
    template_name = "mailing_detail.html"
    context_object_name = "tryrecipients"

    def get_queryset(self) -> Recipient:
        """Определяет queryset для текущего пользователя.

        Возвращает:
            Recipient: Записи о получателе, принадлежащие текущему пользователю.
        """
        if self.request.user.is_authenticated:
            return Recipient.objects.filter(owner=self.request.user)
        return Recipient.objects.none()


class RecipientUpdateView(LoginRequiredMixin, UpdateView):
    """View для обновления Recipient.

    Атрибуты:
        model: Модель Recipient.
        template_name: Шаблон для обновления Recipient.
        success_url: URL для перенаправления после успешного обновления.
    """

    model = Recipient
    template_name = "editing.html"
    success_url = reverse_lazy("mailing:mailing")

    def get_form_class(self) -> type:
        """Возвращает класс формы.

        Возвращает:
            type: Класс формы для Recipient.
        """
        return RecipientForm


class RecipientDeleteView(LoginRequiredMixin, DeleteView):
    """View для удаления Recipient.

    Атрибуты:
        model: Модель Recipient.
        template_name: Шаблон для удаления Recipient.
        success_url: URL для перенаправления после успешного удаления.
    """

    model = Recipient
    template_name = "delete.html"
    success_url = reverse_lazy("mailing:mailing")


class MailCreateView(LoginRequiredMixin, CreateView):
    """View для создания Mail.

    Атрибуты:
        model: Модель Mail.
        form_class: Форма для создания Mail.
        success_url: URL для перенаправления после успешного создания.
        template_name: Шаблон для создания Mail.
    """

    model = Mail
    form_class = MailForm
    success_url = reverse_lazy("mailing:mailing")
    template_name = "create.html"

    def form_valid(self, form):
        # Устанавливаем владельца на текущего авторизованного пользователя
        form.instance.owner = self.request.user
        # self.permissions_owner()
        return super().form_valid(form)

    def get_form_class(self):
        return MailForm


class MailDetailView(LoginRequiredMixin, DetailView):
    model = Mail
    template_name = "mailing_detail.html"

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Mail.objects.filter(owner=self.request.user)
        else:
            return Mail.objects.none()


class MailListView(LoginRequiredMixin, ListView):
    model = Mail

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Mail.objects.filter(owner=self.request.user)
        else:
            return Mail.objects.none()


class MailUpdateView(LoginRequiredMixin, UpdateView):
    model = Mail
    template_name = "editing.html"
    success_url = reverse_lazy("mailing:mailing")

    def get_form_class(self):
        return MailForm


class MailDeleteView(LoginRequiredMixin, DeleteView):
    model = Mail
    template_name = "delete.html"
    success_url = reverse_lazy("mailing:mailing")
