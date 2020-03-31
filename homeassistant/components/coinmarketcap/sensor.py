"""Details about crypto currencies from CoinMarketCap."""
import os
import json
import requests
import tempfile
import requests_cache
from datetime import timedelta
import logging
from urllib.error import HTTPError

#from coinmarketcap import Market
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ATTR_ATTRIBUTION, CONF_DISPLAY_CURRENCY
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

ATTR_VOLUME_24H = "volume_24h"
ATTR_AVAILABLE_SUPPLY = "available_supply"
ATTR_CIRCULATING_SUPPLY = "circulating_supply"
ATTR_MARKET_CAP = "market_cap"
ATTR_PERCENT_CHANGE_24H = "percent_change_24h"
ATTR_PERCENT_CHANGE_7D = "percent_change_7d"
ATTR_PERCENT_CHANGE_1H = "percent_change_1h"
ATTR_PRICE = "price"
ATTR_RANK = "rank"
ATTR_SYMBOL = "symbol"
ATTR_TOTAL_SUPPLY = "total_supply"

ATTRIBUTION = "Data provided by CoinMarketCap"

CONF_CURRENCY_ID = "currency_id"
CONF_DISPLAY_CURRENCY_DECIMALS = "display_currency_decimals"
CONF_API_KEY = "api_key"

DEFAULT_CURRENCY_ID = 1
DEFAULT_DISPLAY_CURRENCY = "USD"
DEFAULT_DISPLAY_CURRENCY_DECIMALS = 2
DEFAULT_API_KEY = None

ICON = "mdi:currency-usd"

SCAN_INTERVAL = timedelta(minutes=15)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_CURRENCY_ID, default=DEFAULT_CURRENCY_ID): cv.positive_int,
        vol.Optional(
            CONF_DISPLAY_CURRENCY, default=DEFAULT_DISPLAY_CURRENCY
        ): cv.string,
        vol.Optional(
            CONF_DISPLAY_CURRENCY_DECIMALS, default=DEFAULT_DISPLAY_CURRENCY_DECIMALS
        ): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the CoinMarketCap sensor."""
    currency_id = config.get(CONF_CURRENCY_ID)
    display_currency = config.get(CONF_DISPLAY_CURRENCY).upper()
    display_currency_decimals = config.get(CONF_DISPLAY_CURRENCY_DECIMALS)
    api_key = config.get(CONF_API_KEY)

    try:
        _LOGGER.warning("i call now coinmarketcapdata")
        CoinMarketCapData(api_key, currency_id, display_currency).update()
    except HTTPError:
        _LOGGER.warning(
            "Currency ID %s or display currency %s "
            "is not available. Using 1 (bitcoin) "
            "and USD.",
            currency_id,
            display_currency,
        )
        currency_id = DEFAULT_CURRENCY_ID
        display_currency = DEFAULT_DISPLAY_CURRENCY

    add_entities(
        [
            CoinMarketCapSensor(
                CoinMarketCapData(api_key, currency_id, display_currency),
                display_currency_decimals,
            )
        ],
        True,
    )


class CoinMarketCapSensor(Entity):
    """Representation of a CoinMarketCap sensor."""

    def __init__(self, data, display_currency_decimals):
        """Initialize the sensor."""
        self.data = data
        _LOGGER.warning("----------------------------")
        _LOGGER.warning(data.__dict__)
        _LOGGER.warning("----------------------------")
        self.display_currency_decimals = display_currency_decimals
        self._ticker = None
        self._unit_of_measurement = self.data.display_currency

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._ticker.get("name")

    @property
    def state(self):
        """Return the state of the sensor."""
        print("indrux "+self.data.display_currency)
        print("dadursch "+str(self._ticker))
        return round(
            float(
                self._ticker.get("quote").get(self.data.display_currency).get("price")
            ),
            self.display_currency_decimals,
        )

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return ICON

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            ATTR_VOLUME_24H: self._ticker.get("quote")
            .get(self.data.display_currency)
            .get("volume_24h"),
            ATTR_ATTRIBUTION: ATTRIBUTION,
            ATTR_CIRCULATING_SUPPLY: self._ticker.get("circulating_supply"),
            ATTR_MARKET_CAP: self._ticker.get("quote")
            .get(self.data.display_currency)
            .get("market_cap"),
            ATTR_PERCENT_CHANGE_24H: self._ticker.get("quote")
            .get(self.data.display_currency)
            .get("percent_change_24h"),
            ATTR_PERCENT_CHANGE_7D: self._ticker.get("quote")
            .get(self.data.display_currency)
            .get("percent_change_7d"),
            ATTR_PERCENT_CHANGE_1H: self._ticker.get("quote")
            .get(self.data.display_currency)
            .get("percent_change_1h"),
            ATTR_RANK: self._ticker.get("rank"),
            ATTR_SYMBOL: self._ticker.get("symbol"),
            ATTR_TOTAL_SUPPLY: self._ticker.get("total_supply"),
        }

    def update(self):
        """Get the latest data and updates the states."""
        print("knarsch update")
        self.data.update()
        print("knarsch updated")
        print("knarsch dadarr tickre sun "+str(self.data.ticker))
        print("knarsch dadarr tickre sol "+str(self.data.ticker.get("data")))
        print("knarsch dadarr tickre six "+str(self.data.currency_id))
        self._ticker = self.data.ticker.get("data").get(str(self.data.currency_id))
        print("knarsch albursh flastre euwasch "+str(self._ticker))


class CoinMarketCapData:
    """Get the latest data and update the states."""

    _session = None
    __DEFAULT_BASE_URL = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency'
    __DEFAULT_TIMEOUT = 30
    __TEMPDIR_CACHE = True

    def __init__(self, api_key, currency_id, display_currency, base_url = __DEFAULT_BASE_URL, request_timeout = __DEFAULT_TIMEOUT, tempdir_cache = __TEMPDIR_CACHE):
        """Initialize the data object."""
        self.currency_id = currency_id
        self.display_currency = display_currency
        self.api_key = api_key
        self.ticker = None
# add a http client

        __DEFAULT_BASE_URL = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency'
        self.base_url = base_url
        self.request_timeout = request_timeout
        self.cache_filename = 'coinmarketcap_cache'
        self.cache_name = os.path.join(tempfile.gettempdir(), self.cache_filename) if tempdir_cache else self.cache_filename

    @property
    def session(self):
        _LOGGER.warning("i am property session")
        if not self._session:
            _LOGGER.warning("i have no property session")
            self._session = requests_cache.core.CachedSession(cache_name=self.cache_name, backend='sqlite', expire_after=120)
            self._session.headers.update({'X-CMC_PRO_API_KEY': self.api_key})
            self._session.headers.update({'Content-Type': 'application/json'})
            self._session.headers.update({'User-agent': 'coinmarketcap - python wrapper around \
                coinmarketcap.com (github.com/barnumbirr/coinmarketcap)'})
            _LOGGER.warning("headers "+str(self._session.headers))
            _LOGGER.warning("i have property session")
        return self._session

    def __request(self, endpoint, params):
        _LOGGER.warning("i am want request "+self.base_url+endpoint)
        _LOGGER.warning("with params "+str(params))
        response_object = self.session.get(self.base_url + endpoint, params = params, timeout = self.request_timeout)

        try:
            _LOGGER.warning("i try request")
            response = json.loads(response_object.text)
            _LOGGER.warning("i try request")

            if isinstance(response, list) and response_object.status_code == 200:
                response = [dict(item, **{u'cached':response_object.from_cache}) for item in response]
            if isinstance(response, dict) and response_object.status_code == 200:
                response[u'cached'] = response_object.from_cache

        except Exception as e:
            return e

        return response


    def update(self):
        """Get the latest data from coinmarketcap.com."""

        #self.ticker = Market().ticker(self.currency_id, convert=self.display_currency)
        params = {}
        params["id"] = self.currency_id
        params["convert"] = self.display_currency
#        params.update(kwargs)

        # see https://github.com/barnumbirr/coinmarketcap/pull/28

        self.ticker = self.__request('/quotes/latest', params)
        _LOGGER.warning("ticker response is "+str(self.ticker))


