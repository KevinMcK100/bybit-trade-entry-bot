from models import TradesDao


class RestService:
    def __init__(self):
        self.model = TradesDao()

    def create(self, params):
        return self.model.create(params)

    def update(self, item_id, params):
        return self.model.update(item_id, params)

    def delete(self, item_id):
        return self.model.deactivate_trade(item_id)

    def list(self):
        response = self.model.list_items()
        return response
    
    def get_by_id(self, item_id):
        response = self.model.get_by_id(item_id)
        return response
