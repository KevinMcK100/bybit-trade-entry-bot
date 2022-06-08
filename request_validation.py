from json import loads
from urllib.request import Request

from flask_inputs import Inputs
from flask_inputs.validators import JsonSchema

SYMBOL = "symbol"
SIDE = "side"
QUANTITY = "quantity"
OPEN_CONDITIONAL_PRICE = "open_conditional_price"
TRIGGER_PRICE = "trigger_price"
SL_PRICE = "sl_price"
TP_PRICE = "tp_price"
MAX_SL_COUNT = "max_sl_count"

create_conditional_order_schema = {
    'type': 'object',
    'properties': {
        SYMBOL: {
            'type': 'string'
        },
        SIDE: {
            'type': 'string'
        },
        QUANTITY: {
            'type': 'number'
        },
        OPEN_CONDITIONAL_PRICE: {
            'type': 'number'
        },
        TRIGGER_PRICE: {
            'type': 'number'
        },
        SL_PRICE: {
            'type': 'number'
        },
        TP_PRICE: {
            'type': 'number'
        },
        MAX_SL_COUNT: {
            'type': 'number'
        },
    },
    'required': [SYMBOL, SIDE, QUANTITY, OPEN_CONDITIONAL_PRICE, TRIGGER_PRICE, SL_PRICE]
}

class CreateConditionalInputs(Inputs):
    create_conditional_schema = JsonSchema(schema=create_conditional_order_schema)
    json = [create_conditional_schema]

    def validate(self):
        is_valid = super().validate()
        if is_valid:
            request: Request = self._request
            json_body = loads(request.data)
            side = json_body[SIDE]
                
            if side == "BUY":
                if float(json_body[OPEN_CONDITIONAL_PRICE]) > float(json_body[TRIGGER_PRICE]):
                    is_valid = False
                    self.errors.append(f"When '{SIDE}' is BUY, '{OPEN_CONDITIONAL_PRICE}' must be less than '{TRIGGER_PRICE}'")
            elif side == "SELL":
                if float(json_body[OPEN_CONDITIONAL_PRICE]) < float(json_body[TRIGGER_PRICE]):
                    is_valid = False
                    self.errors.append(f"When '{SIDE}' is SELL, '{OPEN_CONDITIONAL_PRICE}' must be greater than '{TRIGGER_PRICE}'")
            else:
                is_valid = False
                self.errors.append(f"'{SIDE}' must be one of BUY or SELL'")
        return is_valid

def validate_conditional_order_request(request):
   inputs = CreateConditionalInputs(request)
   if inputs.validate():
       return None
   else:
       print(len(inputs.errors))
       return inputs.errors
