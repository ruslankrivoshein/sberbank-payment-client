import json
import logging
from typing import Dict
from urllib.parse import urlencode

import aiohttp

from exceptions import ActionException, BadRequestException, \
    BadResponseException, NetworkException


class SberbankClient:
    ACTION_SUCCESS = 0

    API_PREFIX_DEFAULT = '/payment/rest/'
    API_PREFIX_APPLE = '/payment/applepay/'
    API_PREFIX_GOOGLE = '/payment/google/'
    API_PREFIX_SAMSUNG = '/payment/samsung/'

    def __init__(
        self,
        api_uri: str,
        session: aiohttp.ClientSession,
        **kwargs,
    ):
        if kwargs.get('username') and kwargs.get('password'):
            if kwargs.get('token'):
                raise Exception  # TODO: add a normal exception

            self.username = kwargs.get('username')
            self.password = kwargs.get('password')
        elif kwargs.get('token'):
            self.token = kwargs.get('token')
        else:
            raise Exception  # TODO: add a normal exception

        self.api_uri = api_uri
        self.language = kwargs.get('language')
        self.currency = kwargs.get('currency')
        self.prefix_default = kwargs.get(
            'prefix_default', self.API_PREFIX_DEFAULT,
        )
        self.prefix_apple = kwargs.get(
            'prefix_apple', self.API_PREFIX_APPLE,
        )
        self.prefix_google = kwargs.get(
            'prefix_google', self.API_PREFIX_GOOGLE,
        )
        self.prefix_samsung = kwargs.get(
            'prefix_samsung', self.API_PREFIX_SAMSUNG,
        )
        self.session = session
        self.logger = logging.getLogger('sber')

        if kwargs.get('http_method'):
            if kwargs.get('http_method') not in ['GET', 'POST']:
                raise BadRequestException('Только GET и POST '
                                          'доступны для использования')

            self.http_method = kwargs.get('http_method')

    async def register_order(
        self,
        *,
        order_number: str,
        amount: int,
        return_url: str,
        **kwargs,
    ):
        """
        Запрос регистрации заказа

        :param order_number: Номер (идентификатор) заказа в системе магазина
        :type order_number: str
        :param amount: Сумма возврата в минимальных единицах валюты
        :type amount: int
        :param return_url: Адрес, на который требуется перенаправить
                           пользователя в случае успешной оплаты
        :type return_url: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        return await self.do_register_order(
            order_number=order_number,
            amount=amount,
            return_url=return_url,
            method='%s%s' % (self.prefix_default, 'register.do'),
            **kwargs,
        )

    async def register_order_preauth(
        self,
        *,
        order_number: str,
        amount: int,
        return_url: str,
        **kwargs,
    ):
        """
        Запрос регистрации заказа

        :param order_number: Номер (идентификатор) заказа в системе магазина
        :type order_number: str
        :param amount: Сумма возврата в минимальных единицах валюты
        :type amount: int
        :param return_url: Адрес, на который требуется перенаправить
                           пользователя в случае успешной оплаты
        :type return_url: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        return await self.do_register_order(
            order_number=order_number,
            amount=amount,
            return_url=return_url,
            method='%s%s' % (self.prefix_default, 'registerPreAuth.do'),
            **kwargs,
        )

    async def do_register_order(
        self,
        *,
        order_number: str,
        amount: int,
        return_url: str,
        method: str,
        **kwargs,
    ):
        """
        Запрос регистрации заказа

        :param order_number: Номер (идентификатор) заказа в системе магазина
        :type order_number: str
        :param amount: Сумма возврата в минимальных единицах валюты
        :type amount: int
        :param return_url: Адрес, на который требуется перенаправить
                           пользователя в случае успешной оплаты
        :type return_url: str
        :param method: Название метода для вызова
        :type method: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['orderNumber'] = order_number
        kwargs['amount'] = amount
        kwargs['returnUrl'] = return_url

        if not kwargs.get('currency') and self.currency:
            kwargs['currency'] = self.currency

        if kwargs.get('jsonParams'):
            if isinstance(kwargs.get('jsonParams'), dict):
                raise TypeError('"jsonParams" должен быть типа dict')

        return await self.execute(method, **kwargs)

    async def deposit(
        self,
        *,
        order_id: str,
        amount: int,
        **kwargs,
    ):
        """
        Запрос завершения на полную сумму в деньгах

        :param order_id: Номер заказа в платежной системе
        :type order_id: str
        :param amount: Сумма платежа в копейках (или центах).
                       Внимание!!! Если в этом параметре указать ноль,
                       завершение произойдет на всю предавторизованную сумму
        :type amount: int
        :param data: Необязательные данные
        :type data: dict
        """
        kwargs['orderId'] = order_id
        kwargs['amount'] = amount

        return await self.execute(
            '%s%s' % (self.prefix_default, 'deposit.do'),
            **kwargs,
        )

    async def reverse_order(
        self,
        *,
        order_id: str,
        **kwargs,
    ):
        """
        Запрос отмены оплаты заказа

        :param order_id: Номер заказа в платежной системе
        :type order_id: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['orderId'] = order_id

        return await self.execute(
            '%s%s' % (self.prefix_default, 'reverse.do'),
            **kwargs,
        )

    async def refund_order(
        self,
        *,
        order_id: str,
        amount: int,
        **kwargs,
    ):
        """
        Запрос возврата на полную сумму в деньгах

        :param order_id: Номер заказа в платежной системе
        :type order_id: str
        :param amount: Сумма возврата в минимальных единицах валюты
        :type amount: int
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['orderId'] = order_id
        kwargs['amount'] = amount

        return await self.execute(
            '%s%s' % (self.prefix_default, 'refund.do'),
            **kwargs,
        )

    async def get_order_status_by_id(
        self,
        *,
        order_id: str,
        **kwargs,
    ):
        """
        Расширенный запрос состояния заказа

        :param order_id: Номер заказа в платежной системе
        :type order_id: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['orderId'] = order_id

        return await self.execute(
            '%s%s' % (self.prefix_default, 'getOrderStatusExtended.do'),
            **kwargs,
        )

    async def get_order_status_by_number(
        self,
        *,
        order_number: str,
        **kwargs,
    ):
        """
        Расширенный запрос состояния заказа

        :param order_number: Номер заказа в системе магазина
        :type order_number: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['orderNumber'] = order_number

        return await self.execute(
            '%s%s' % (self.prefix_default, 'getOrderStatusExtended.do'),
            **kwargs,
        )

    async def verify_enrollment(
        self,
        *,
        pan: str,
        **kwargs,
    ):
        """
        Запрос проверки вовлечённости карты в 3-D Secure

        :param pan: Маскированный номер карты, которая использовалась для оплаты
        :type pan: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['pan'] = pan

        return await self.execute(
            '%s%s' % (self.prefix_default, 'verifyEnrollment.do'),
            **kwargs,
        )

    async def pay_with_applepay(
        self,
        *,
        order_number: str,
        merchant: str,
        payment_token: str,
        **kwargs,
    ):
        """
        Запрос на оплату с помощью Apple Pay

        :param order_number: Номер (идентификатор) заказа в системе магазина
        :type order_number: str
        :param merchant: Логин продавца в платёжном шлюзе
        :type merchant: str
        :param payment_token: Закодированное в Base64 значение
                              свойства paymentData, полученного
                              из объекта PKPaymentToken Object
                              от системы Apple Pay
        :type payment_token: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['orderNumber'] = order_number
        kwargs['merchant'] = merchant
        kwargs['paymentToken'] = payment_token

        return await self.execute(
            '%s%s' % (self.prefix_apple, 'payment.do'),
            **kwargs,
        )

    async def pay_with_applepay_recurrent(
        self,
        *,
        order_number: str,
        amount: int,
        binding_id: str,
        **kwargs,
    ):
        """
        Запрос на оплату с помощью Apple Pay

        :param order_number: Номер заказа в системе магазина
        :type order_number: str
        :param amount: Сумма возврата в минимальных единицах валюты
        :type amount: int
        :param binding_id: Идентификатор связки, созданной ранее
        :type binding_id: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['orderNumber'] = order_number
        kwargs['amount'] = amount
        kwargs['binding_id'] = binding_id

        return await self.execute('payment/recurrentPayment.do', **kwargs)

    async def pay_with_samsungpay(
        self,
        *,
        order_number: str,
        merchant: str,
        payment_token: str,
        ip: str,
        **kwargs,
    ):
        """
        Запрос на оплату с помощью Samsung Pay

        :param order_number: Номер (идентификатор) заказа в системе магазина
        :type order_number: str
        :param merchant: Логин продавца в платёжном шлюзе
        :type merchant: str
        :param payment_token: Содержимое параметра 3ds.data из ответа,
                              полученного от Samsung Pay
        :type payment_token: str
        :param ip: IP-адрес покупателя
        :type ip: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['orderNumber'] = order_number
        kwargs['merchant'] = merchant
        kwargs['payment_token'] = payment_token
        kwargs['ip'] = ip

        return await self.execute(
            '%s%s' % (self.prefix_samsung, 'payment.do'),
            **kwargs,
        )

    async def pay_with_samsungpay_web(
        self,
        *,
        md_order: str,
        back_url: str,
    ):
        """
        Запрос на оплату через Samsung Pay, при котором используется
        платёжная страница на стороне продавца

        :param md_order: Номер заказа в платёжном шлюзе
        :type md_order: str
        :param back_url: URL-адрес, на который будет перенаправлен покупатель
                         в случае ошибки или превышения срока ожидания
        :type back_url: str
        """
        kwargs = {'mdOrder': md_order, 'onFailedPaymentBackUrl': back_url}

        return await self.execute('payment/samsungWeb/payment.do', **kwargs)

    async def pay_with_googlepay(
        self,
        *,
        order_number: str,
        merchant: str,
        payment_token: str,
        amount,
        **kwargs,
    ):
        """
        Запрос на оплату с помощью Google Pay

        :param order_number: Номер (идентификатор) заказа в системе магазина
        :type order_number: str
        :param merchant: Логин продавца в платёжном шлюзе
        :type merchant: str
        :param payment_token: Токен, полученный от Google Pay и закодированный
                              в Base64
        :type payment_token: str
        :param amount: IP-адрес покупателя
        :type amount: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['orderNumber'] = order_number
        kwargs['merchant'] = merchant
        kwargs['paymentToken'] = payment_token
        kwargs['amount'] = amount

        return await self.execute(
            '%s%s' % (self.prefix_google, 'payment.do'),
            **kwargs,
        )

    async def decline_by_id(
        self,
        *,
        order_id: str,
        merchant_location: str,
        **kwargs,
    ):
        """
        Запрос отмены неоплаченного заказа

        :param order_id: Номер заказа в системе магазина
        :type order_id: str
        :param merchant_location: Имя мерчанта, для которого нужно
                                  отклонить заказ
        :type merchant_location: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['orderId'] = order_id
        kwargs['merchantLocation'] = merchant_location

        return await self.execute(
            '%s%s' % (self.prefix_default, 'decline.do'),
            **kwargs,
        )

    async def decline_by_number(
        self,
        *,
        order_number: str,
        merchant_location: str,
        **kwargs,
    ):
        """
        Запрос отмены неоплаченного заказа

        :param order_number: Номер заказа в системе магазина
        :type order_number: str
        :param merchant_location: Имя мерчанта, для которого нужно отклонить заказ
        :type merchant_location: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['orderNumber'] = order_number
        kwargs['merchantLocation'] = merchant_location

        return await self.execute(
            '%s%s' % (self.prefix_default, 'decline.do'),
            **kwargs,
        )

    async def get_receipt_status(self, **kwargs):
        """
        Запрос сведений о кассовом чеке

        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        return await self.execute(
            '%s%s' % (self.prefix_default, 'getReceiptStatus.do'),
            **kwargs,
        )

    async def unbind_card(
        self,
        *,
        binding_id: str,
        **kwargs,
    ):
        """
        Запрос деактивации связки

        :param binding_id: Идентификатор созданной ранее связки
        :type binding_id: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['bindingId'] = binding_id

        return await self.execute(
            '%s%s' % (self.prefix_default, 'unBindCard.do'),
            **kwargs,
        )

    async def bind_card(
        self,
        *,
        binding_id: str,
        **kwargs,
    ):
        """
        Запрос активации связки

        :param binding_id: Идентификатор созданной ранее связки
        :type binding_id: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['bindingId'] = binding_id

        return await self.execute(
            '%s%s' % (self.prefix_default, 'bindCard.do'),
            **kwargs,
        )

    async def get_bindings(
        self,
        *,
        client_id: str,
    ):
        """
        Запрос списка всех связок клиента

        :param client_id: Номер (идентификатор) клиента в системе магазина
        :type client_id: str
        """
        kwargs = {'clientId': client_id}

        return await self.execute(
            '%s%s' % (self.prefix_default, 'getBindings.do'),
            **kwargs,
        )

    async def get_bindings_by_card(
        self,
        *,
        pan: str,
        **kwargs,
    ):
        """
        Запрос списка связок определённой банковской карты

        :param pan: Маскированный номер карты, которая использовалась для оплаты
        :type pan: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['pan'] = pan

        return await self.execute(
            '%s%s' % (self.prefix_default, 'getBindingsByCardOrId.do'),
            **kwargs,
        )

    async def get_bindings_by_id(
        self,
        *,
        binding_id: str,
        **kwargs,
    ):
        """
        Запрос списка связок определённой банковской карты

        :param binding_id: Идентификатор созданной ранее связки
        :type binding_id: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['bindingId'] = binding_id

        return await self.execute(
            '%s%s' % (self.prefix_default, 'getBindingsByCardOrId.do'),
            **kwargs,
        )

    async def payment_order_binding(
        self,
        *,
        binding_id: str,
        md_order: str,
        ip: str,
        **kwargs,
    ):
        """
        Запрос проведения оплаты по связкам

        :param binding_id: Идентификатор созданной ранее связки
        :type binding_id: str
        :param md_order: Номер заказа в платёжном шлюзе
        :type md_order: str
        :param ip: IP-адрес покупателя
        :type ip: str
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['bindingId'] = binding_id
        kwargs['mdOrder'] = md_order
        kwargs['ip'] = ip

        return await self.execute(
            '%s%s' % (self.prefix_default, 'paymentOrderBinding.do'),
            **kwargs,
        )

    async def extend_binding(
        self,
        *,
        binding_id: str,
        new_expiry: int,
        **kwargs,
    ):
        """
        Запрос изменения срока действия связки

        :param binding_id: Идентификатор созданной ранее связки
        :type binding_id: str
        :param new_expiry: Новая дата (год и месяц) окончания срока действия
                           в формате ГГГГДД
        :type new_expiry: int
        :param kwargs: Необязательные данные
        :type kwargs: dict
        """
        kwargs['bindingId'] = binding_id
        kwargs['newExpiry'] = int(new_expiry)

        return await self.execute(
            '%s%s' % (self.prefix_default, 'extendBinding.do'),
            **kwargs,
        )

    async def execute(self, action: str, **kwargs):
        """
        Выполнение запроса к API Сбербанка

        :param action: Название вызываемого метода API
        :type action: str
        :param kwargs: Передаваемые данные
        :type kwargs: dict
        """
        data = self._snake_to_camel(kwargs)

        if action[0] != '/':
            action = '%s%s' % (self.prefix_default, action)

        rest = action.find(self.prefix_default)
        uri = '%s%s' % (self.api_uri, action)

        if not data.get('language') and self.language:
            data['language'] = self.language

        headers = {'Cache-Control': 'no-cache'}
        method = self.http_method

        log_str = f'{method} {uri}({data}):'

        if rest != -1:
            if hasattr(self, 'token'):
                data['token'] = self.token
            else:
                data['userName'] = self.username
                data['password'] = self.password

            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            data = urlencode(data)
        else:
            headers['Content-Type'] = 'application/json'
            method = 'POST'
            data = json.dumps(data)

        try:
            async with self.session.request(
                method=method,
                url=uri,
                headers=headers,
                data=data,
            ) as response:
                if response.status != 200:
                    msg = 'HTTP-код: %s' % response.status

                    self.logger.error(f'{log_str} {msg}')

                    raise BadResponseException('HTTP-код: %s' % response.status)

                response = await response.read()
                response = json.loads(response)

                try:
                    self._handle_errors(response)
                except ActionException as e:
                    self.logger.error(f'{log_str} "{e.code} ({e.message})"')

                    raise e

                self.logger.info(f'{log_str} {response}')

                return self._camel_to_snake(response)
        except aiohttp.ClientConnectorError as e:
            msg = 'Сбербанк недоступен'

            self.logger.error(f'{log_str} {e}')

            raise NetworkException(msg)

    def _handle_errors(self, response: Dict):
        error_code = self.ACTION_SUCCESS
        error_message = 'Неизвестная ошибка'

        if response.get('errorCode'):
            error_code = response['errorCode']
        elif response.get('ErrorMessage'):
            error_code = response['ErrorMessage']
        elif response.get('error', {}).get('code'):
            error_code = response['error']['code']

        if response.get('errorMessage'):
            error_message = response['errorMessage']
        elif response.get('ErrorMessage'):
            error_message = response['ErrorMessage']
        elif response.get('error', {}).get('message'):
            error_message = response['error']['message']
        elif response.get('error', {}).get('description'):
            error_message = response['error']['description']

        if isinstance(error_code, str) and error_code.isdigit():
            error_code = int(error_code)

        if error_code != self.ACTION_SUCCESS:
            raise ActionException(error_message, error_code)

    def _snake_to_camel(self, data: Dict):
        camel_data = {}

        for key in data:
            _key = key

            if key.find('_') != -1:
                _key = ''.join(x for x in key.title() if x.isalnum())
                _key = _key[0].lower() + _key[1:]

            if isinstance(data[key], dict):
                camel_data[_key] = self._snake_to_camel(data[key])
            else:
                camel_data[_key] = data[key]

        return camel_data

    def _camel_to_snake(self, data: Dict):
        snake_data = {}

        for key in data:
            _key = ''.join(['_' + i.lower() if i.isupper() else i for i in key]).lstrip('_')

            if isinstance(data[key], dict):
                snake_data[_key] = self._camel_to_snake(data[key])
            else:
                snake_data[_key] = data[key]

        return snake_data
