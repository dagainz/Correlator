class Event:
    def __init__(self, **kwargs):
        self.data = None

        # Allow setting any property from kwargs used in constructor

        allowed_keys = list(self.__dict__.keys())
        self.__dict__.update((key, value) for key, value in kwargs.items()
                             if key in allowed_keys)
        rejected_keys = set(kwargs.keys()) - set(allowed_keys)
        if rejected_keys:
            raise ValueError(
                "Event called with invalid arguments".format(rejected_keys))


if __name__ == 'main':
    a = Event()
    b = Event(data='this works')

    pass
