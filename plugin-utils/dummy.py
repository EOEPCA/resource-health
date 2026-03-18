def foo(exceptions: type[BaseException] | tuple[type[BaseException], ...]) -> None:
    try:
        raise TypeError("Bad type :(")
    except exceptions:
        print("Exception occurred")
    

foo(TypeError)
foo((ValueError,))