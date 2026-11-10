from .operation import Operation

class Cloud(Operation):
    def __init__(self, operations):
        self.operations = operations

    def get_operations(self):
        return self.operations

    def get_type(self):
        return 'Cloud'