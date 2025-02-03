class ClassModifier:
    def __init__(self, cls, new_classmethods=None, return_modifications=None):
        """
        cls: The original class to be modified.
        new_classmethods: A dictionary of method names and functions that
        are to be added to the new class
        return_modifications: A dictionary of method names and functions that
        are used to modify the return values of the corresponding methods.
        """
        self.cls = cls
        self.new_classmethods = new_classmethods or {}
        self.return_modifications = return_modifications or {}

    def __call__(self):
        """
        Create a class with the new classmethods in addition to the existing
        classmethods, which have modified return values for specified methods.
        """
        new_class_dict = {}

        # Add new classmethods
        new_class_dict.update(self.new_classmethods.items())

        # Iterate over all class attributes and methods of the original class
        for attr_name, attr_value in self.cls.__dict__.items():
            # If the attribute is in return_modifications, wrap the method
            if attr_name in self.return_modifications:
                new_class_dict[attr_name] = self._wrap_method(
                    attr_value,
                    self.return_modifications[attr_name],
                )
            else:
                new_class_dict[attr_name] = attr_value

        # Use a fallback name if the class doesn't have a __name__ attribute
        class_name = getattr(self.cls, "__name__", "AnonymousClass")

        return type(f"Modified{class_name}", (object,), new_class_dict)

    def _wrap_method(self, method, return_modifier):
        """
        Wrap a classmethod so that it calls the original method and modifies
        its return value.
        method: The original method to wrap.
        return_modifier: A function that takes the original return value and
        modifies it.
        """
        # Get the underlying function from the classmethod
        original_func = method.__func__

        @classmethod
        def wrapped(cls, *args, **kwargs):
            original_return_value = original_func(cls, *args, **kwargs)
            return return_modifier(cls, original_return_value, *args, **kwargs)

        return wrapped
